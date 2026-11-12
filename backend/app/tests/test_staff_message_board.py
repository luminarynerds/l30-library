# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the Staff Message Board feature.

Covers:
- Model creation and relationships
- Category enum values
- API schema validation (skipped if full app deps not available)
"""

import pytest


class TestMessageBoardCategory:
    """Test MessageBoardCategory enum values."""

    def test_all_categories_exist(self):
        from app.models.staff_message_board import MessageBoardCategory

        expected = {'memo', 'library_happenings', 'state_news', 'general', 'tips_tricks', 'professional_dev'}
        actual = {c.value for c in MessageBoardCategory}
        assert actual == expected

    def test_category_string_values(self):
        from app.models.staff_message_board import MessageBoardCategory

        assert MessageBoardCategory.MEMO.value == 'memo'
        assert MessageBoardCategory.LIBRARY_HAPPENINGS.value == 'library_happenings'
        assert MessageBoardCategory.STATE_NEWS.value == 'state_news'
        assert MessageBoardCategory.GENERAL.value == 'general'
        assert MessageBoardCategory.TIPS_TRICKS.value == 'tips_tricks'
        assert MessageBoardCategory.PROFESSIONAL_DEV.value == 'professional_dev'


class TestBoardPostModel:
    """Test BoardPost model table and column configuration."""

    def test_tablename(self):
        from app.models.staff_message_board import BoardPost
        assert BoardPost.__tablename__ == 'staff_board_posts'

    def test_has_expected_columns(self):
        from app.models.staff_message_board import BoardPost

        columns = {c.name for c in BoardPost.__table__.columns}
        expected = {'id', 'title', 'content', 'category', 'pinned', 'archived', 'author_id', 'created_at', 'updated_at'}
        assert expected.issubset(columns)

    def test_repr(self):
        from app.models.staff_message_board import BoardPost

        post = BoardPost(id=1, title='Test Post', category='general')
        r = repr(post)
        assert 'BoardPost' in r
        assert 'Test Post' in r

    def test_default_values(self):
        from app.models.staff_message_board import BoardPost

        post = BoardPost(title='Test', content='Body')
        assert post.pinned is False or post.pinned is None  # Default applied at DB level
        assert post.archived is False or post.archived is None


class TestBoardReplyModel:
    """Test BoardReply model table and column configuration."""

    def test_tablename(self):
        from app.models.staff_message_board import BoardReply
        assert BoardReply.__tablename__ == 'staff_board_replies'

    def test_has_expected_columns(self):
        from app.models.staff_message_board import BoardReply

        columns = {c.name for c in BoardReply.__table__.columns}
        expected = {'id', 'content', 'post_id', 'author_id', 'created_at', 'updated_at'}
        assert expected.issubset(columns)

    def test_repr(self):
        from app.models.staff_message_board import BoardReply

        reply = BoardReply(id=5, post_id=1)
        r = repr(reply)
        assert 'BoardReply' in r
        assert '5' in r


class TestBoardPostRelationships:
    """Test model relationships are properly defined."""

    def test_post_has_replies_relationship(self):
        from app.models.staff_message_board import BoardPost
        assert hasattr(BoardPost, 'replies')

    def test_post_has_author_relationship(self):
        from app.models.staff_message_board import BoardPost
        assert hasattr(BoardPost, 'author')

    def test_reply_has_post_relationship(self):
        from app.models.staff_message_board import BoardReply
        assert hasattr(BoardReply, 'post')

    def test_reply_has_author_relationship(self):
        from app.models.staff_message_board import BoardReply
        assert hasattr(BoardReply, 'author')


class TestAPISchemas:
    """Test API Pydantic schemas for validation.

    These tests require the full app dependency chain (Redis, etc.).
    They are skipped if deps are not available.
    """

    @pytest.fixture(autouse=True)
    def _import_schemas(self):
        try:
            from app.api.v1.staff_message_board import PostCreate, PostUpdate, ReplyCreate, ReplyUpdate
            self.PostCreate = PostCreate
            self.PostUpdate = PostUpdate
            self.ReplyCreate = ReplyCreate
            self.ReplyUpdate = ReplyUpdate
        except ImportError:
            pytest.skip("Full app dependencies not available")

    def test_post_create_schema_valid(self):
        post = self.PostCreate(title='Hello', content='World', category='memo')
        assert post.title == 'Hello'
        assert post.content == 'World'
        assert post.category == 'memo'
        assert post.pinned is False

    def test_post_create_defaults(self):
        post = self.PostCreate(title='Hi', content='There')
        assert post.category == 'general'
        assert post.pinned is False

    def test_post_create_rejects_empty_title(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.PostCreate(title='', content='Content')

    def test_post_create_rejects_empty_content(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.PostCreate(title='Title', content='')

    def test_post_update_all_optional(self):
        update = self.PostUpdate()
        assert update.title is None
        assert update.content is None
        assert update.category is None
        assert update.pinned is None
        assert update.archived is None

    def test_post_update_partial(self):
        update = self.PostUpdate(title='New Title')
        assert update.title == 'New Title'
        assert update.content is None

    def test_reply_create_valid(self):
        reply = self.ReplyCreate(content='A reply')
        assert reply.content == 'A reply'

    def test_reply_create_rejects_empty(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.ReplyCreate(content='')

    def test_reply_update_valid(self):
        reply = self.ReplyUpdate(content='Updated')
        assert reply.content == 'Updated'
