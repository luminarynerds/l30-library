# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff Knowledge Base API Endpoints
Comprehensive knowledge base for staff policies, procedures, how-tos, and Q&A
"""
import hashlib
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, and_, delete, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import AsyncSessionLocal, get_db
from ....core.datetime_utils import utc_now
from ....core.shortcuts import get_or_404
from ....models.embeddings import TextEmbedding
from ....services.semantic_search_service import SemanticSearchService
from ....models.user import User
from ....models.knowledge_base import (
    StaffKnowledgeArticle,
    ArticleVersion,
    DecisionTree,
    VideoTutorial,
    OnboardingChecklist,
    StaffQA,
    ArticleBookmark,
    KnowledgeContentFlag,
)
from ..auth import get_current_user_optional
from ..dependencies import require_staff
from ....models.user import UserRole
from ....schemas.staff_knowledge import (
    StaffKnowledgeArticleCreate,
    StaffKnowledgeArticleUpdate,
    StaffKnowledgeArticleResponse,
    StaffKnowledgeArticleWithVersions,
    ArticleVersionResponse,
    DecisionTreeCreate,
    DecisionTreeUpdate,
    DecisionTreeResponse,
    VideoTutorialCreate,
    VideoTutorialUpdate,
    VideoTutorialResponse,
    OnboardingChecklistCreate,
    OnboardingChecklistUpdate,
    OnboardingChecklistResponse,
    StaffQACreate,
    StaffQAAnswerCreate,
    StaffQAResponse,
    ArticleBookmarkCreate,
    ArticleBookmarkResponse,
    ContentFlagCreate,
    ContentFlagResolve,
    ContentFlagResponse,
    ArticleSearchResult,
    SearchResponse,
)

from ....core.logging import get_logger

logger = get_logger(__name__)


router = APIRouter(prefix="/staff-knowledge", tags=["Staff Knowledge Base"])

STAFF_ARTICLE_ENTITY_TYPE = "staff_knowledge_article"

# Cosine-similarity floor for staff-article semantic search, matching the shared
# SemanticSearchService default (min_similarity = 0.3, i.e. cosine_distance <= 0.7)
# so a query with nothing close returns no semantic matches instead of the
# nearest-N. 1 - cosine_distance >= 0.3  <=>  cosine_distance <= 0.7.
STAFF_SEMANTIC_MIN_SIMILARITY = 0.3


async def _refresh_article_embedding(article_id: int) -> None:
    """Best-effort generate/refresh the pgvector embedding for a staff article.

    Runs OFF the request path as a FastAPI BackgroundTask: by the time it runs
    the request's session is closed, so it opens its OWN AsyncSessionLocal and
    re-loads the article by primitive id (never reuse the request's session or a
    detached ORM instance). Skips the embedding API entirely when the embeddable
    text is unchanged (text_hash match). Upserts a single TextEmbedding row keyed
    by (entity_type, entity_id). Failures are swallowed so the worker never
    crashes on an embedding API timeout.
    """
    try:
        async with AsyncSessionLocal() as db:
            article = await db.get(StaffKnowledgeArticle, article_id)
            if article is None:
                # Deleted between the response and this background task.
                return

            parts = [article.title]
            if article.summary:
                parts.append(article.summary)
            if article.description:
                parts.append(article.description)
            if article.content:
                parts.append(article.content)
            text_content = " ".join(part for part in parts if part).strip()
            if not text_content:
                return

            text_hash = hashlib.sha256(text_content.encode()).hexdigest()

            existing = (
                await db.execute(
                    select(TextEmbedding).where(
                        and_(
                            TextEmbedding.entity_type == STAFF_ARTICLE_ENTITY_TYPE,
                            TextEmbedding.entity_id == article_id,
                        )
                    )
                )
            ).scalar_one_or_none()

            # Unchanged text -> embedding is current; skip the external call entirely.
            if existing is not None and existing.text_hash == text_hash:
                return

            svc = SemanticSearchService(db)
            vector = await svc.generate_embedding(text_content)
            if vector is None:
                return

            if existing is not None:
                existing.text_content = text_content
                existing.text_hash = text_hash
                existing.embedding = vector
                existing.embedding_model = svc.embedding_model
                existing.embedding_dimension = len(vector)
                existing.is_generated = True
                existing.generated_at = utc_now()
            else:
                db.add(
                    TextEmbedding(
                        entity_type=STAFF_ARTICLE_ENTITY_TYPE,
                        entity_id=article_id,
                        text_content=text_content,
                        text_hash=text_hash,
                        embedding=vector,
                        embedding_model=svc.embedding_model,
                        embedding_dimension=len(vector),
                        is_generated=True,
                        generated_at=utc_now(),
                    )
                )
            await db.commit()
    except Exception:  # noqa: BLE001 - embedding best-effort; never crash the worker
        logger.exception(
            "Failed to refresh staff-article embedding for article %s",
            article_id,
        )


async def _semantic_search_articles(
    db: AsyncSession, query: str, limit: int, offset: int
):
    """Semantic search over staff-article embeddings (pgvector cosine distance).

    Mirrors faq_chatbot_service._semantic_search: reuse the shared embedding
    generator, then a direct join TextEmbedding -> StaffKnowledgeArticle ordered
    by cosine distance. Applies the same cosine-similarity floor as the shared
    SemanticSearchService so an off-topic query returns no semantic matches
    (total 0) and the caller falls back to the ILIKE path. Returns
    (articles, total) on success, or None on empty/failure.
    """
    try:
        svc = SemanticSearchService(db)
        vector = await svc.generate_embedding(query, input_type="query")
        if vector is None:
            return None

        distance = TextEmbedding.embedding.cosine_distance(vector)
        join_cond = and_(
            TextEmbedding.entity_id == StaffKnowledgeArticle.id,
            TextEmbedding.entity_type == STAFF_ARTICLE_ENTITY_TYPE,
        )
        # Similarity floor: 1 - cosine_distance >= 0.3  <=>  cosine_distance <= 0.7.
        # Appended to the shared where_cond so the count and ranked queries below
        # carry IDENTICAL predicates and stay consistent.
        where_cond = (
            StaffKnowledgeArticle.is_published == True,
            TextEmbedding.is_generated == True,
            TextEmbedding.embedding.isnot(None),
            distance <= (1 - STAFF_SEMANTIC_MIN_SIMILARITY),
        )

        count_result = await db.execute(
            select(func.count())
            .select_from(StaffKnowledgeArticle)
            .join(TextEmbedding, join_cond)
            .where(*where_cond)
        )
        total = count_result.scalar() or 0
        if total == 0:
            return None

        rows = (
            await db.execute(
                select(StaffKnowledgeArticle, distance.label("distance"))
                .join(TextEmbedding, join_cond)
                .where(*where_cond)
                .order_by("distance")
                .offset(offset)
                .limit(limit)
            )
        ).unique().all()
        articles = [row[0] for row in rows]
        return articles, total
    except Exception:  # noqa: BLE001 - semantic optional; caller falls back to ILIKE
        logger.warning(
            "Staff-article semantic search unavailable; falling back to ILIKE",
            exc_info=True,
        )
        return None



# ==================== Staff Knowledge Articles ====================

@router.post("/articles", response_model=StaffKnowledgeArticleResponse)
async def create_knowledge_article(
    article: StaffKnowledgeArticleCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new knowledge base article (staff only)"""
    new_article = StaffKnowledgeArticle(
        title=article.title,
        description=article.description,
        content=article.content,
        content_type=article.content_type,
        category=article.category,
        subcategory=article.subcategory,
        tags=article.tags,
        summary=article.summary,
        transcript=article.transcript,
        audio_url=article.audio_url,
        is_published=article.is_published,
        created_by_id=current_user.id,
    )
    db.add(new_article)
    await db.commit()
    await db.refresh(new_article)

    # Create initial version
    initial_version = ArticleVersion(
        article_id=new_article.id,
        version_number=1,
        title=article.title,
        content=article.content,
        change_notes="Initial version",
        changed_by_id=current_user.id,
    )
    db.add(initial_version)
    await db.commit()

    # Best-effort: generate semantic embedding off the request path. The task
    # opens its own session, so pass the primitive id (the ORM instance would be
    # detached/closed by the time the task runs).
    background_tasks.add_task(_refresh_article_embedding, new_article.id)

    return new_article


@router.get("/articles", response_model=List[StaffKnowledgeArticleResponse])
async def get_knowledge_articles(
    category: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    published_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge articles with optional filtering"""
    query = select(StaffKnowledgeArticle)

    if published_only:
        query = query.where(StaffKnowledgeArticle.is_published == True)
    if category:
        query = query.where(StaffKnowledgeArticle.category == category)
    if content_type:
        query = query.where(StaffKnowledgeArticle.content_type == content_type)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.unique().scalars().all()


@router.get("/articles/search", response_model=SearchResponse)
async def search_articles(
    q: str = Query(..., min_length=2),
    semantic: bool = Query(False, description="Use pgvector semantic search (falls back to keyword on empty/failure)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across articles (title, summary, description, tags, body).

    With ``semantic=true`` runs pgvector semantic search over staff-article
    embeddings, falling back to the case-insensitive keyword path on empty or
    failed results. Results are ordered by relevance (title > summary/description
    > body) in the keyword path.
    """
    if semantic:
        semantic_hit = await _semantic_search_articles(db, q, limit=limit, offset=skip)
        if semantic_hit is not None:
            articles, total = semantic_hit
            return SearchResponse(
                total=total,
                results=[ArticleSearchResult.model_validate(a) for a in articles],
            )
        # fall through to keyword search on empty/failure

    # Case-insensitive keyword search across title, summary, description, tags, body
    search_pattern = f"%{q}%"
    match_clause = or_(
        StaffKnowledgeArticle.title.ilike(search_pattern),
        StaffKnowledgeArticle.summary.ilike(search_pattern),
        StaffKnowledgeArticle.description.ilike(search_pattern),
        StaffKnowledgeArticle.tags.ilike(search_pattern),
        StaffKnowledgeArticle.content.ilike(search_pattern),
    )

    # Relevance: title match (3) > summary/description (2) > body/tags (1)
    relevance = case(
        (StaffKnowledgeArticle.title.ilike(search_pattern), 3),
        (
            or_(
                StaffKnowledgeArticle.summary.ilike(search_pattern),
                StaffKnowledgeArticle.description.ilike(search_pattern),
            ),
            2,
        ),
        else_=1,
    )

    query = (
        select(StaffKnowledgeArticle)
        .where(match_clause)
        .where(StaffKnowledgeArticle.is_published == True)
        .order_by(relevance.desc(), StaffKnowledgeArticle.view_count.desc())
    )

    count_result = await db.execute(
        select(func.count())
        .select_from(StaffKnowledgeArticle)
        .where(match_clause)
        .where(StaffKnowledgeArticle.is_published == True)
    )
    total = count_result.scalar() or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    articles = result.unique().scalars().all()

    return SearchResponse(
        total=total,
        results=[ArticleSearchResult.model_validate(a) for a in articles],
    )


@router.get("/articles/{article_id}", response_model=StaffKnowledgeArticleWithVersions)
async def get_article(article_id: int, current_user: User = Depends(require_staff), db: AsyncSession = Depends(get_db)):
    """Get a specific article with version history"""
    result = await db.execute(
        select(StaffKnowledgeArticle)
        .where(StaffKnowledgeArticle.id == article_id)
        .options(selectinload(StaffKnowledgeArticle.versions))
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Increment view count
    article.view_count += 1
    await db.commit()

    return article


@router.put("/articles/{article_id}", response_model=StaffKnowledgeArticleResponse)
async def update_article(
    article_id: int,
    article_update: StaffKnowledgeArticleUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update an article and create a new version (staff only)"""
    article = await get_or_404(db, StaffKnowledgeArticle, article_id, "Article not found")

    # Update fields
    if article_update.title is not None:
        article.title = article_update.title
    if article_update.description is not None:
        article.description = article_update.description
    if article_update.content is not None:
        article.content = article_update.content
    if article_update.category is not None:
        article.category = article_update.category
    if article_update.subcategory is not None:
        article.subcategory = article_update.subcategory
    if article_update.tags is not None:
        article.tags = article_update.tags
    if article_update.summary is not None:
        article.summary = article_update.summary
    if article_update.transcript is not None:
        article.transcript = article_update.transcript
    if article_update.audio_url is not None:
        article.audio_url = article_update.audio_url
    if article_update.is_published is not None:
        article.is_published = article_update.is_published

    # If content changed, create a new version
    if article_update.content is not None:
        article.current_version += 1
        new_version = ArticleVersion(
            article_id=article.id,
            version_number=article.current_version,
            title=article.title,
            content=article.content,
            change_notes=article_update.change_notes,
            changed_by_id=current_user.id,
        )
        db.add(new_version)

    article.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(article)

    # Best-effort: refresh semantic embedding off the request path (own session;
    # pass the primitive id, not the soon-detached ORM instance).
    background_tasks.add_task(_refresh_article_embedding, article.id)

    return article


@router.delete("/articles/{article_id}", status_code=204)
async def delete_article(
    article_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete an article (staff only)"""
    article = await get_or_404(db, StaffKnowledgeArticle, article_id, "Article not found")

    await db.delete(article)
    await db.commit()


# ==================== Article Feedback ====================

@router.post("/articles/{article_id}/helpful")
async def mark_helpful(
    article_id: int,
    helpful: bool = Query(...),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark article as helpful or unhelpful"""
    article = await get_or_404(db, StaffKnowledgeArticle, article_id, "Article not found")

    if helpful:
        article.helpful_count += 1
    else:
        article.unhelpful_count += 1

    await db.commit()
    return {"status": "success"}


# ==================== Decision Trees ====================

@router.post("/decision-trees", response_model=DecisionTreeResponse)
async def create_decision_tree(
    tree: DecisionTreeCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a decision tree (staff only)"""
    new_tree = DecisionTree(
        title=tree.title,
        description=tree.description,
        category=tree.category,
        tree_data=tree.tree_data,
        is_published=tree.is_published,
        created_by_id=current_user.id,
    )
    db.add(new_tree)
    await db.commit()
    await db.refresh(new_tree)
    return new_tree


@router.get("/decision-trees", response_model=List[DecisionTreeResponse])
async def get_decision_trees(
    category: Optional[str] = Query(None),
    published_only: bool = Query(True),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get decision trees"""
    query = select(DecisionTree)

    if published_only:
        query = query.where(DecisionTree.is_published == True)
    if category:
        query = query.where(DecisionTree.category == category)

    result = await db.execute(query)
    return result.unique().scalars().all()


@router.get("/decision-trees/{tree_id}", response_model=DecisionTreeResponse)
async def get_decision_tree(tree_id: int, current_user: User = Depends(require_staff), db: AsyncSession = Depends(get_db)):
    """Get a specific decision tree"""
    tree = await get_or_404(db, DecisionTree, tree_id, "Decision tree not found")

    # Increment view count
    tree.view_count += 1
    await db.commit()
    # updated_at has onupdate=func.now(); the commit expires it server-side, so
    # refresh before serializing or the response_model read raises MissingGreenlet.
    await db.refresh(tree)

    return tree


@router.put("/decision-trees/{tree_id}", response_model=DecisionTreeResponse)
async def update_decision_tree(
    tree_id: int,
    tree_update: DecisionTreeUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a decision tree (staff only)"""
    tree = await get_or_404(db, DecisionTree, tree_id, "Decision tree not found")

    if tree_update.title is not None:
        tree.title = tree_update.title
    if tree_update.description is not None:
        tree.description = tree_update.description
    if tree_update.tree_data is not None:
        tree.tree_data = tree_update.tree_data
    if tree_update.is_published is not None:
        tree.is_published = tree_update.is_published

    tree.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(tree)

    return tree


# ==================== Video Tutorials ====================

@router.post("/video-tutorials", response_model=VideoTutorialResponse)
async def create_video_tutorial(
    tutorial: VideoTutorialCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a video tutorial (staff only)"""
    new_tutorial = VideoTutorial(
        title=tutorial.title,
        description=tutorial.description,
        category=tutorial.category,
        video_url=tutorial.video_url,
        thumbnail_url=tutorial.thumbnail_url,
        duration_seconds=tutorial.duration_seconds,
        transcript=tutorial.transcript,
        related_article_ids=tutorial.related_article_ids or [],
        is_published=tutorial.is_published,
        created_by_id=current_user.id,
    )
    db.add(new_tutorial)
    await db.commit()
    await db.refresh(new_tutorial)
    return new_tutorial


@router.get("/video-tutorials", response_model=List[VideoTutorialResponse])
async def get_video_tutorials(
    category: Optional[str] = Query(None),
    published_only: bool = Query(True),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get video tutorials"""
    query = select(VideoTutorial)

    if published_only:
        query = query.where(VideoTutorial.is_published == True)
    if category:
        query = query.where(VideoTutorial.category == category)

    result = await db.execute(query)
    return result.unique().scalars().all()


@router.get("/video-tutorials/{video_id}", response_model=VideoTutorialResponse)
async def get_video_tutorial(video_id: int, current_user: User = Depends(require_staff), db: AsyncSession = Depends(get_db)):
    """Get a specific video tutorial"""
    video = await get_or_404(db, VideoTutorial, video_id, "Video tutorial not found")

    # Increment view count
    video.view_count += 1
    await db.commit()
    # updated_at has onupdate=func.now(); the commit expires it server-side, so
    # refresh before serializing or the response_model read raises MissingGreenlet.
    await db.refresh(video)

    return video


@router.put("/video-tutorials/{video_id}", response_model=VideoTutorialResponse)
async def update_video_tutorial(
    video_id: int,
    tutorial_update: VideoTutorialUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a video tutorial (staff only)"""
    video = await get_or_404(db, VideoTutorial, video_id, "Video tutorial not found")

    if tutorial_update.title is not None:
        video.title = tutorial_update.title
    if tutorial_update.description is not None:
        video.description = tutorial_update.description
    if tutorial_update.video_url is not None:
        video.video_url = tutorial_update.video_url
    if tutorial_update.thumbnail_url is not None:
        video.thumbnail_url = tutorial_update.thumbnail_url
    if tutorial_update.duration_seconds is not None:
        video.duration_seconds = tutorial_update.duration_seconds
    if tutorial_update.transcript is not None:
        video.transcript = tutorial_update.transcript
    if tutorial_update.related_article_ids is not None:
        video.related_article_ids = tutorial_update.related_article_ids
    if tutorial_update.is_published is not None:
        video.is_published = tutorial_update.is_published

    await db.commit()
    await db.refresh(video)

    return video


# ==================== Onboarding Checklists ====================

@router.post("/onboarding-checklists", response_model=OnboardingChecklistResponse)
async def create_onboarding_checklist(
    checklist: OnboardingChecklistCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create an onboarding checklist for a new staff member (staff only)"""
    new_checklist = OnboardingChecklist(
        user_id=checklist.user_id,
        title=checklist.title,
        description=checklist.description,
        checklist_items=checklist.checklist_items,
        assigned_by_id=checklist.assigned_by_id or current_user.id,
    )
    db.add(new_checklist)
    await db.commit()
    await db.refresh(new_checklist)
    return new_checklist


@router.get("/onboarding-checklists/user/{user_id}", response_model=List[OnboardingChecklistResponse])
async def get_user_onboarding_checklists(
    user_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get onboarding checklists for a user (staff or self)"""
    if current_user.id != user_id and current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(OnboardingChecklist)
        .where(OnboardingChecklist.user_id == user_id)
        .order_by(OnboardingChecklist.start_date.desc())
    )
    return result.unique().scalars().all()


@router.put("/onboarding-checklists/{checklist_id}", response_model=OnboardingChecklistResponse)
async def update_onboarding_checklist(
    checklist_id: int,
    checklist_update: OnboardingChecklistUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update an onboarding checklist"""
    checklist = await get_or_404(db, OnboardingChecklist, checklist_id, "Checklist not found")

    # Check authorization
    if current_user.id != checklist.user_id and current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Not authorized")

    if checklist_update.title is not None:
        checklist.title = checklist_update.title
    if checklist_update.description is not None:
        checklist.description = checklist_update.description
    if checklist_update.checklist_items is not None:
        checklist.checklist_items = checklist_update.checklist_items
        # Check if all items are completed
        all_completed = all(item.get("completed", False) for item in checklist.checklist_items)
        if all_completed and not checklist.is_completed:
            checklist.is_completed = True
            checklist.completed_date = datetime.now()

    await db.commit()
    await db.refresh(checklist)

    return checklist


# ==================== Staff Q&A ====================

@router.post("/qa", response_model=StaffQAResponse)
async def create_qa_question(
    qa: StaffQACreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Ask a question in the staff Q&A"""
    new_qa = StaffQA(
        question=qa.question,
        category=qa.category,
        tags=qa.tags,
        asked_by_id=current_user.id,
        related_article_id=qa.related_article_id,
    )
    db.add(new_qa)
    await db.commit()
    await db.refresh(new_qa)
    return new_qa


@router.get("/qa", response_model=List[StaffQAResponse])
async def get_qa_questions(
    category: Optional[str] = Query(None),
    answered_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get Q&A questions"""
    query = select(StaffQA).where(StaffQA.is_closed == False)

    if answered_only:
        query = query.where(StaffQA.is_answered == True)
    if category:
        query = query.where(StaffQA.category == category)

    query = query.order_by(StaffQA.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.unique().scalars().all()


@router.post("/qa/{qa_id}/answer", response_model=StaffQAResponse)
async def answer_qa_question(
    qa_id: int,
    answer_data: StaffQAAnswerCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Answer a Q&A question (staff only)"""
    qa = await get_or_404(db, StaffQA, qa_id, "Question not found")

    if qa.is_answered:
        raise HTTPException(status_code=400, detail="Question already answered")

    qa.answer = answer_data.answer
    qa.answered_by_id = current_user.id
    qa.is_answered = True
    qa.answered_at = datetime.now()

    await db.commit()
    await db.refresh(qa)

    return qa


@router.post("/qa/{qa_id}/upvote")
async def upvote_qa_answer(
    qa_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Upvote a Q&A answer"""
    qa = await get_or_404(db, StaffQA, qa_id, "Question not found")

    if not qa.is_answered:
        raise HTTPException(status_code=400, detail="Question not yet answered")

    qa.answer_upvotes += 1
    await db.commit()

    return {"upvotes": qa.answer_upvotes}


# ==================== Bookmarks ====================

@router.post("/bookmarks", response_model=ArticleBookmarkResponse)
async def bookmark_article(
    bookmark: ArticleBookmarkCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Bookmark an article"""
    # Check if already bookmarked
    existing = await db.execute(
        select(ArticleBookmark).where(
            and_(
                ArticleBookmark.user_id == current_user.id,
                ArticleBookmark.article_id == bookmark.article_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Article already bookmarked")

    new_bookmark = ArticleBookmark(
        user_id=current_user.id,
        article_id=bookmark.article_id,
    )
    db.add(new_bookmark)

    # Update bookmark count on article
    article = await db.execute(
        select(StaffKnowledgeArticle).where(StaffKnowledgeArticle.id == bookmark.article_id)
    )
    article_obj = article.scalar_one_or_none()
    if article_obj:
        article_obj.bookmark_count += 1

    await db.commit()
    await db.refresh(new_bookmark)
    return new_bookmark


@router.get("/bookmarks", response_model=List[StaffKnowledgeArticleResponse])
async def get_user_bookmarks(
    current_user: User = Depends(require_staff),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get user's bookmarked articles"""
    result = await db.execute(
        select(StaffKnowledgeArticle)
        .join(ArticleBookmark, ArticleBookmark.article_id == StaffKnowledgeArticle.id)
        .where(ArticleBookmark.user_id == current_user.id)
        .order_by(ArticleBookmark.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.unique().scalars().all()


@router.delete("/bookmarks/{article_id}", status_code=204)
async def remove_bookmark(
    article_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Remove a bookmark"""
    bookmark = await db.execute(
        select(ArticleBookmark).where(
            and_(
                ArticleBookmark.user_id == current_user.id,
                ArticleBookmark.article_id == article_id,
            )
        )
    )
    bookmark_obj = bookmark.scalar_one_or_none()

    if not bookmark_obj:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    # Update bookmark count on article
    article = await db.execute(
        select(StaffKnowledgeArticle).where(StaffKnowledgeArticle.id == article_id)
    )
    article_obj = article.scalar_one_or_none()
    if article_obj and article_obj.bookmark_count > 0:
        article_obj.bookmark_count -= 1

    await db.delete(bookmark_obj)
    await db.commit()


# ==================== Content Flags ====================

@router.post("/flags", response_model=ContentFlagResponse)
async def flag_content(
    flag: ContentFlagCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Flag content for review"""
    new_flag = KnowledgeContentFlag(
        article_id=flag.article_id,
        reason=flag.reason,
        description=flag.description,
        flagged_by_id=current_user.id,
    )
    db.add(new_flag)
    await db.commit()
    await db.refresh(new_flag)
    return new_flag


@router.get("/flags", response_model=List[ContentFlagResponse])
async def get_content_flags(
    status: Optional[str] = Query(None),
    article_id: Optional[int] = Query(None),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get content flags (staff only)"""
    query = select(KnowledgeContentFlag)

    if status:
        query = query.where(KnowledgeContentFlag.status == status)
    if article_id:
        query = query.where(KnowledgeContentFlag.article_id == article_id)

    query = query.order_by(KnowledgeContentFlag.created_at.desc())
    result = await db.execute(query)
    return result.unique().scalars().all()


@router.put("/flags/{flag_id}", response_model=ContentFlagResponse)
async def resolve_content_flag(
    flag_id: int,
    resolution: ContentFlagResolve,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a content flag (staff only)"""
    flag = await get_or_404(db, KnowledgeContentFlag, flag_id, "Flag not found")

    flag.status = resolution.status
    flag.reviewed_by_id = current_user.id
    flag.reviewed_at = datetime.now()
    flag.reviewer_notes = resolution.reviewer_notes

    await db.commit()
    await db.refresh(flag)

    return flag
