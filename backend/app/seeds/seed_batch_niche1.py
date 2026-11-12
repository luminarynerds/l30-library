# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
from datetime import datetime, timedelta, timezone, date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _future(days_ahead: int) -> datetime:
    return datetime.now(utc) + timedelta(days=days_ahead)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


async def seed_batch_niche1(session: AsyncSession) -> bool:

    # Grab reusable IDs
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    items_r = await session.execute(text("SELECT id FROM catalog_items"))
    catalog_ids = [r[0] for r in items_r.fetchall()]

    now = datetime.now(utc)

    # ================================================================
    # GENEALOGY / LOCAL HISTORY
    # ================================================================

    # ────────────────────────────────────────────────────────────────
    # 17-20. RESEARCH PROJECTS (needed first for FK), then PERSONS,
    #         RELATIONSHIPS, DOCUMENTS, COLLABORATORS
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_research_projects"))
    if r.scalar() == 0:
        print("  Seeding genealogy_research_projects...")
        projects = [
            ("Johnson Family Tree", "Tracing the Johnson family from colonial Virginia to present-day Illinois.", True, True, 5, 12, 8),
            ("Springfield Founders Project", "Collaborative research into the founding families of Springfield, IL.", True, True, 15, 25, 6),
            ("O'Brien Immigration Study", "Tracking the O'Brien family immigration from County Cork, Ireland to America in the 1840s.", False, False, 8, 6, 4),
            ("Williams Heritage Project", "Researching African-American heritage in the central Illinois region from 1850-present.", True, True, 12, 18, 7),
            ("Schmidt German Ancestry", "Documenting the Schmidt family's journey from Bavaria to the American Midwest.", False, False, 6, 4, 3),
        ]
        project_ids = []
        for name, desc, is_public, allow_joins, persons, docs, gens in projects:
            owner = random.choice(all_ids)
            r2 = await session.execute(text("""
                INSERT INTO genealogy_research_projects
                    (name, description, owner_id, is_public,
                     allow_join_requests, default_license,
                     person_count, document_count, generation_count,
                     created_at, updated_at)
                VALUES
                    (:name, :desc, :owner, :public,
                     :joins, 'CC-BY-4.0',
                     :persons, :docs, :gens,
                     :created, :created)
                RETURNING id
            """), {
                "name": name, "desc": desc, "owner": owner,
                "public": is_public, "joins": allow_joins,
                "persons": persons, "docs": docs, "gens": gens,
                "created": _past(random.randint(60, 365)),
            })
            project_ids.append(r2.scalar())
        print(f"    Created {len(projects)} research projects")
        await session.commit()
    else:
        pr = await session.execute(text("SELECT id FROM genealogy_research_projects"))
        project_ids = [r[0] for r in pr.fetchall()]

    # ────────────────────────────────────────────────────────────────
    # 17. GENEALOGY PERSONS
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_persons"))
    if r.scalar() == 0 and project_ids:
        print("  Seeding genealogy_persons...")
        persons = [
            # Project 0: Johnson Family
            (0, "Elijah", "Johnson", None, None, "1785", date(1785, 3, 15), "Virginia",
             "1862", date(1862, 11, 2), "Springfield, IL", "male", False, "Farmer"),
            (0, "Martha", "Johnson", "Adams", None, "1790", date(1790, 7, 22), "Virginia",
             "1870", date(1870, 4, 18), "Springfield, IL", "female", False, "Homemaker"),
            (0, "Samuel", "Johnson", None, None, "1815", date(1815, 5, 10), "Virginia",
             "1890", date(1890, 12, 1), "Springfield, IL", "male", False, "Merchant"),
            (0, "Hannah", "Johnson", "Taylor", None, "1820", date(1820, 1, 3), "Kentucky",
             "1895", date(1895, 6, 15), "Springfield, IL", "female", False, "Teacher"),
            (0, "William", "Johnson", None, None, "1845", date(1845, 9, 20), "Springfield, IL",
             "1918", date(1918, 3, 8), "Springfield, IL", "male", False, "Attorney"),
            (0, "Elizabeth", "Johnson", "Brown", None, "1848", date(1848, 12, 1), "Springfield, IL",
             "1925", date(1925, 8, 22), "Springfield, IL", "female", False, "Nurse"),
            # Project 1: Springfield Founders
            (1, "Josiah", "Springfield", None, None, "1800", date(1800, 6, 4), "Massachusetts",
             "1875", date(1875, 2, 14), "Springfield, IL", "male", False, "Surveyor"),
            (1, "Catherine", "Springfield", "Whitfield", None, "1805", date(1805, 11, 30), "Massachusetts",
             "1880", date(1880, 9, 5), "Springfield, IL", "female", False, "Civic Leader"),
            (1, "Thomas", "Hartford", None, None, "1798", date(1798, 4, 17), "Connecticut",
             "1868", date(1868, 7, 22), "Springfield, IL", "male", False, "Banker"),
            (1, "Mary", "Hartford", "Price", None, "1802", date(1802, 8, 9), "Connecticut",
             "1871", date(1871, 1, 30), "Springfield, IL", "female", False, None),
            (1, "James", "Caldwell", None, None, "1810", date(1810, 2, 28), "New York",
             "1885", date(1885, 5, 11), "Springfield, IL", "male", False, "Publisher"),
            (1, "Sarah", "Caldwell", "Monroe", None, "1815", date(1815, 10, 12), "New York",
             "1892", date(1892, 12, 25), "Springfield, IL", "female", False, None),
            # Project 2: O'Brien Immigration
            (2, "Patrick", "O'Brien", None, None, "1820", date(1820, 3, 17), "County Cork, Ireland",
             "1890", date(1890, 8, 3), "Boston, MA", "male", False, "Laborer"),
            (2, "Brigid", "O'Brien", "Murphy", None, "1822", date(1822, 5, 1), "County Cork, Ireland",
             "1895", date(1895, 1, 20), "Boston, MA", "female", False, None),
            (2, "Michael", "O'Brien", None, None, "1845", date(1845, 12, 25), "Boston, MA",
             "1920", date(1920, 4, 5), "Springfield, IL", "male", False, "Railroad Worker"),
            (2, "Rose", "O'Brien", "Gallagher", None, "1850", date(1850, 6, 15), "New York, NY",
             "1930", date(1930, 10, 8), "Springfield, IL", "female", False, None),
            # Project 3: Williams Heritage
            (3, "Isaac", "Williams", None, None, "1830", date(1830, 1, 1), "Unknown",
             "1900", date(1900, 7, 4), "Springfield, IL", "male", False, "Blacksmith"),
            (3, "Harriet", "Williams", None, None, "1835", date(1835, 6, 19), "Kentucky",
             "1910", date(1910, 3, 15), "Springfield, IL", "female", False, "Midwife"),
            (3, "George", "Williams", None, None, "1860", date(1860, 9, 22), "Springfield, IL",
             "1935", date(1935, 11, 2), "Springfield, IL", "male", False, "Minister"),
            (3, "Clara", "Williams", "Jackson", None, "1865", date(1865, 4, 14), "Springfield, IL",
             "1940", date(1940, 2, 28), "Springfield, IL", "female", False, "Teacher"),
            # Project 4: Schmidt German Ancestry
            (4, "Friedrich", "Schmidt", None, None, "1825", date(1825, 8, 10), "Bavaria, Germany",
             "1900", date(1900, 12, 20), "Springfield, IL", "male", False, "Brewer"),
            (4, "Anna", "Schmidt", "Weber", None, "1830", date(1830, 2, 14), "Bavaria, Germany",
             "1905", date(1905, 5, 1), "Springfield, IL", "female", False, None),
            (4, "Karl", "Schmidt", None, None, "1855", date(1855, 7, 4), "Springfield, IL",
             "1925", date(1925, 9, 15), "Springfield, IL", "male", False, "Baker"),
            (4, "Greta", "Schmidt", "Muller", None, "1858", date(1858, 11, 30), "Springfield, IL",
             "1930", date(1930, 6, 8), "Springfield, IL", "female", False, None),
            # Some living people (project 3)
            (3, "Marcus", "Williams", None, None, "1955", date(1955, 8, 12), "Springfield, IL",
             None, None, None, "male", True, "Retired Teacher"),
            (3, "Dorothy", "Williams", "Freeman", None, "1958", date(1958, 3, 25), "Springfield, IL",
             None, None, None, "female", True, "Librarian"),
        ]
        person_ids_by_project = {}
        all_person_ids = []
        for proj_idx, given, surname, maiden, suffix, bd, bd_norm, bp, dd, dd_norm, dp, gender, living, occ in persons:
            pid = project_ids[proj_idx] if proj_idx < len(project_ids) else project_ids[0]
            r2 = await session.execute(text("""
                INSERT INTO genealogy_persons
                    (project_id, created_by, given_names, surname, maiden_name,
                     suffix, birth_date, birth_date_normalized, birth_place,
                     death_date, death_date_normalized, death_place,
                     gender, is_living, occupation, confidence_level,
                     is_verified, notes)
                VALUES
                    (:pid, :created_by, :given, :surname, :maiden,
                     :suffix, :bd, :bd_norm, :bp,
                     :dd, :dd_norm, :dp,
                     :gender, :living, :occ, :confidence,
                     :verified, :notes)
                RETURNING id
            """), {
                "pid": pid, "created_by": random.choice(all_ids),
                "given": given, "surname": surname, "maiden": maiden,
                "suffix": suffix, "bd": bd, "bd_norm": bd_norm, "bp": bp,
                "dd": dd, "dd_norm": dd_norm, "dp": dp,
                "gender": gender, "living": living, "occ": occ,
                "confidence": random.randint(3, 5),
                "verified": random.choice([True, True, False]),
                "notes": None,
            })
            person_id = r2.scalar()
            all_person_ids.append(person_id)
            if pid not in person_ids_by_project:
                person_ids_by_project[pid] = []
            person_ids_by_project[pid].append(person_id)
        print(f"    Created {len(persons)} genealogy persons")
        await session.commit()
    else:
        pr = await session.execute(text("SELECT id, project_id FROM genealogy_persons"))
        rows = pr.fetchall()
        all_person_ids = [r[0] for r in rows]
        person_ids_by_project = {}
        for pid, proj in rows:
            if proj not in person_ids_by_project:
                person_ids_by_project[proj] = []
            person_ids_by_project[proj].append(pid)

    # ────────────────────────────────────────────────────────────────
    # 18. GENEALOGY FAMILY RELATIONSHIPS
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_family_relationships"))
    if r.scalar() == 0 and all_person_ids:
        print("  Seeding genealogy_family_relationships...")
        # Create spouse and parent-child relationships within each project
        rel_count = 0
        for proj_id, pids in person_ids_by_project.items():
            if len(pids) < 2:
                continue
            # Pair consecutive persons as spouses (even-odd pairing)
            for i in range(0, len(pids) - 1, 2):
                await session.execute(text("""
                    INSERT INTO genealogy_family_relationships
                        (project_id, person1_id, person2_id, relationship_type,
                         marriage_date, marriage_place, is_current,
                         confidence_level, created_by)
                    VALUES
                        (:pid, :p1, :p2, 'spouse',
                         :md, :mp, true,
                         :conf, :creator)
                """), {
                    "pid": proj_id, "p1": pids[i], "p2": pids[i + 1],
                    "md": f"{random.randint(1815, 1885)}",
                    "mp": "Springfield, IL",
                    "conf": random.randint(3, 5),
                    "creator": random.choice(all_ids),
                })
                rel_count += 1
            # Link first pair as parents of third person (if exists)
            if len(pids) >= 3:
                await session.execute(text("""
                    INSERT INTO genealogy_family_relationships
                        (project_id, person1_id, person2_id, relationship_type,
                         is_current, confidence_level, created_by)
                    VALUES
                        (:pid, :p1, :p2, 'parent_child',
                         true, :conf, :creator)
                """), {
                    "pid": proj_id, "p1": pids[0], "p2": pids[2],
                    "conf": random.randint(4, 5),
                    "creator": random.choice(all_ids),
                })
                rel_count += 1
            if len(pids) >= 4:
                await session.execute(text("""
                    INSERT INTO genealogy_family_relationships
                        (project_id, person1_id, person2_id, relationship_type,
                         is_current, confidence_level, created_by)
                    VALUES
                        (:pid, :p1, :p2, 'parent_child',
                         true, :conf, :creator)
                """), {
                    "pid": proj_id, "p1": pids[1], "p2": pids[2],
                    "conf": random.randint(4, 5),
                    "creator": random.choice(all_ids),
                })
                rel_count += 1
        print(f"    Created {rel_count} family relationships")
        await session.commit()

    # ────────────────────────────────────────────────────────────────
    # 19. GENEALOGY DOCUMENTS + PERSON-DOCUMENT LINKS
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_documents"))
    if r.scalar() == 0 and project_ids:
        print("  Seeding genealogy_documents + person-document links...")
        docs_data = [
            ("Birth Certificate - Elijah Johnson", "Original birth certificate from Virginia parish records", "birth_certificate",
             "Virginia State Archives", "1785"),
            ("Marriage Record - Samuel & Hannah Johnson", "Marriage record from Sangamon County clerk", "marriage_certificate",
             "Sangamon County Courthouse", "1840"),
            ("1850 Census - Johnson Household", "Federal census record showing the Johnson family in Springfield", "census_record",
             "National Archives", "1850"),
            ("Immigration Record - Patrick O'Brien", "Passenger list from the ship arriving in Boston from Cork", "immigration_record",
             "Ellis Island Foundation", "1845"),
            ("Death Certificate - Isaac Williams", "Death certificate from Sangamon County", "death_certificate",
             "Illinois State Archives", "1900"),
            ("Military Record - Michael O'Brien", "Civil War service record from Illinois Volunteers", "military_record",
             "National Archives", "1863"),
            ("Naturalization Papers - Friedrich Schmidt", "Naturalization certificate from Sangamon County", "naturalization",
             "Sangamon County Courthouse", "1860"),
            ("Newspaper Clipping - Caldwell Family", "Article about James Caldwell's printing press in the Illinois State Journal", "newspaper_clipping",
             "Springfield Public Library Microfilm", "1855"),
            ("Church Baptism Record - George Williams", "Baptismal record from First AME Church of Springfield", "church_record",
             "First AME Church Archives", "1860"),
            ("Family Photograph - Schmidt Family 1880", "Studio portrait of the Schmidt family, circa 1880", "photograph",
             "Private Family Collection", "1880"),
        ]
        doc_ids = []
        for i, (title, desc, dtype, repo, doc_date) in enumerate(docs_data):
            pid = project_ids[i % len(project_ids)]
            r2 = await session.execute(text("""
                INSERT INTO genealogy_documents
                    (project_id, uploaded_by, title, description,
                     document_type, source_repository, source_citation,
                     file_type, document_date, document_date_normalized,
                     document_location, status)
                VALUES
                    (:pid, :uploader, :title, :desc,
                     :dtype, :repo, :citation,
                     :ftype, :doc_date, :doc_date_norm,
                     :location, 'verified')
                RETURNING id
            """), {
                "pid": pid, "uploader": random.choice(all_ids),
                "title": title, "desc": desc,
                "dtype": dtype, "repo": repo,
                "citation": f"{repo}, Record #{random.randint(1000, 9999)}",
                "ftype": random.choice(["pdf", "jpg", "png"]),
                "doc_date": doc_date,
                "doc_date_norm": date(int(doc_date), 1, 1) if doc_date.isdigit() else None,
                "location": "Springfield, IL",
            })
            doc_ids.append(r2.scalar())

        # Person-Document links
        link_count = 0
        if all_person_ids and doc_ids:
            for did in doc_ids:
                num_links = random.randint(1, 3)
                for _ in range(num_links):
                    await session.execute(text("""
                        INSERT INTO genealogy_person_document_links
                            (person_id, document_id, role_in_document,
                             notes, created_by)
                        VALUES
                            (:pid, :did, :role, :notes, :creator)
                    """), {
                        "pid": random.choice(all_person_ids),
                        "did": did,
                        "role": random.choice(["subject", "witness", "mentioned", "applicant"]),
                        "notes": None,
                        "creator": random.choice(all_ids),
                    })
                    link_count += 1
        print(f"    Created {len(docs_data)} documents, {link_count} person-document links")
        await session.commit()
    else:
        dr = await session.execute(text("SELECT id FROM genealogy_documents"))
        doc_ids = [r[0] for r in dr.fetchall()]

    # ────────────────────────────────────────────────────────────────
    # 20. GENEALOGY PROJECT COLLABORATORS
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_project_collaborators"))
    if r.scalar() == 0 and project_ids:
        print("  Seeding genealogy_project_collaborators...")
        collab_count = 0
        for pid in project_ids:
            num_collabs = random.randint(1, 3)
            used = set()
            for _ in range(num_collabs):
                uid = random.choice(all_ids)
                if uid in used:
                    continue
                used.add(uid)
                inviter = random.choice(staff_ids)
                await session.execute(text("""
                    INSERT INTO genealogy_project_collaborators
                        (project_id, user_id, role, invited_by,
                         accepted_at, is_active)
                    VALUES
                        (:pid, :uid, :role, :inviter,
                         :accepted, true)
                """), {
                    "pid": pid, "uid": uid,
                    "role": random.choice(["editor", "viewer", "admin"]),
                    "inviter": inviter,
                    "accepted": _past(random.randint(1, 60)),
                })
                collab_count += 1
        print(f"    Created {collab_count} project collaborators")
        await session.commit()

    # ────────────────────────────────────────────────────────────────
    # 21. GENEALOGY RESEARCH NOTES + GUIDANCE
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_research_notes"))
    if r.scalar() == 0 and project_ids:
        print("  Seeding genealogy_research_notes + guidance...")
        notes_data = [
            ("Census discrepancy: Johnson ages", "observation",
             "The 1850 and 1860 census records show different ages for Samuel Johnson that don't match. Need to cross-reference with other records."),
            ("Immigration ship manifest found", "breakthrough",
             "Located the passenger list for the ship Mary Catherine that brought the O'Brien family to Boston in 1845. Patrick listed as age 25, occupation: laborer."),
            ("Missing link: Williams pre-1850", "brick_wall",
             "Cannot find any records for Isaac Williams before 1850. This is consistent with enslaved persons not appearing in census records before emancipation."),
            ("Cemetery plot verified", "conclusion",
             "Visited Oak Ridge Cemetery and confirmed the Schmidt family plot. Friedrich, Anna, and Karl all buried there."),
            ("Check Bavarian church records", "todo",
             "Need to request baptism records from the parish in Oberpfalz, Bavaria for Friedrich Schmidt. Contact the Archdiocese of Regensburg."),
            ("DNA results support hypothesis", "hypothesis",
             "The autosomal DNA results show a strong match with descendants of the Virginia Johnsons, supporting our colonial Virginia origin theory."),
        ]
        for title, ntype, content in notes_data:
            pid = random.choice(project_ids)
            person_id = random.choice(all_person_ids) if all_person_ids and random.random() < 0.5 else None
            doc_id = random.choice(doc_ids) if doc_ids and random.random() < 0.3 else None
            await session.execute(text("""
                INSERT INTO genealogy_research_notes
                    (project_id, author_id, title, content, note_type,
                     person_id, document_id, is_resolved, is_pinned, priority)
                VALUES
                    (:pid, :author, :title, :content, :ntype,
                     :person_id, :doc_id, :resolved, :pinned, :priority)
            """), {
                "pid": pid, "author": random.choice(all_ids),
                "title": title, "content": content, "ntype": ntype,
                "person_id": person_id, "doc_id": doc_id,
                "resolved": ntype in ("conclusion", "breakthrough"),
                "pinned": ntype == "brick_wall",
                "priority": random.randint(1, 5),
            })

        # Research guidance suggestions
        guidance_data = [
            ("next_record", "Check 1870 Census for Johnson family",
             "The 1870 census would show the Johnson family after the Civil War. Look for changes in household composition.",
             "ancestry", "census", "Springfield, IL", "1870-1870"),
            ("geographic_lead", "Search Virginia land records",
             "The Johnson family originated in Virginia. Land deed records may reveal more about Elijah Johnson's property.",
             "familysearch", "land_deed", "Virginia", "1780-1850"),
            ("database_suggestion", "Try FindAGrave for Schmidt burials",
             "FindAGrave has extensive records for Illinois cemeteries and may have photos of the Schmidt headstones.",
             "findagrave", "burial", "Springfield, IL", None),
            ("missing_source", "Obtain marriage certificate",
             "The marriage date for Patrick and Brigid O'Brien is noted but no certificate has been found. Check County Cork parish records.",
             "other", "marriage_certificate", "County Cork, Ireland", "1840-1845"),
        ]
        for stype, title, desc, db_source, rec_type, location, date_range in guidance_data:
            pid = random.choice(project_ids)
            person_id = random.choice(all_person_ids) if all_person_ids and random.random() < 0.5 else None
            await session.execute(text("""
                INSERT INTO genealogy_research_guidance
                    (project_id, person_id, suggestion_type, title,
                     description, rationale, suggested_database,
                     suggested_record_type, suggested_location,
                     suggested_date_range, priority,
                     is_dismissed, is_completed)
                VALUES
                    (:pid, :person_id, :stype, :title,
                     :desc, :rationale, :db_source,
                     :rec_type, :location,
                     :date_range, :priority,
                     false, false)
            """), {
                "pid": pid, "person_id": person_id,
                "stype": stype, "title": title,
                "desc": desc,
                "rationale": f"Based on existing records, this search may yield new information.",
                "db_source": db_source, "rec_type": rec_type,
                "location": location, "date_range": date_range,
                "priority": random.randint(1, 5),
            })
        print(f"    Created {len(notes_data)} notes, {len(guidance_data)} guidance suggestions")
        await session.commit()

    # ────────────────────────────────────────────────────────────────
    # 22. GENEALOGY TIMELINE EVENTS
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_timeline_events"))
    if r.scalar() == 0 and all_person_ids and project_ids:
        print("  Seeding genealogy_timeline_events...")
        timeline_events = [
            ("birth", "Born in Virginia", "Elijah Johnson born in colonial Virginia", "1785", date(1785, 3, 15), "Virginia"),
            ("marriage", "Marriage to Martha Adams", "Elijah Johnson married Martha Adams at the parish church", "1810", date(1810, 6, 20), "Virginia"),
            ("immigration", "Family moves to Illinois", "The Johnson family relocated from Virginia to the new state of Illinois", "1830", date(1830, 5, 1), "Springfield, IL"),
            ("immigration", "Patrick O'Brien arrives in Boston", "Patrick O'Brien arrived from Ireland aboard the Mary Catherine", "1845", date(1845, 8, 15), "Boston, MA"),
            ("military_service", "Michael O'Brien enlists", "Michael O'Brien enlisted in the Illinois Volunteer Infantry during the Civil War", "1863", date(1863, 4, 12), "Springfield, IL"),
            ("occupation", "Friedrich Schmidt opens brewery", "Friedrich Schmidt established his brewing business on Main Street", "1865", date(1865, 9, 1), "Springfield, IL"),
            ("death", "Isaac Williams passes", "Isaac Williams died and was buried at Oak Ridge Cemetery", "1900", date(1900, 7, 4), "Springfield, IL"),
            ("education", "George Williams graduates seminary", "George Williams completed his seminary training and was ordained", "1885", date(1885, 6, 15), "Springfield, IL"),
            ("residence", "Williams family homestead", "The Williams family established their home at 142 Elm Street", "1870", date(1870, 3, 1), "Springfield, IL"),
            ("achievement", "James Caldwell publishes first issue", "James Caldwell published the first issue of the Springfield Weekly Press", "1850", date(1850, 1, 15), "Springfield, IL"),
        ]
        for etype, title, desc, ev_date, ev_date_norm, location in timeline_events:
            pid = random.choice(project_ids)
            person_id = random.choice(all_person_ids)
            await session.execute(text("""
                INSERT INTO genealogy_timeline_events
                    (project_id, person_id, event_type, title, description,
                     event_date, event_date_normalized, location,
                     source_citation, confidence_level, created_by)
                VALUES
                    (:pid, :person_id, :etype, :title, :desc,
                     :ev_date, :ev_date_norm, :location,
                     :citation, :conf, :creator)
            """), {
                "pid": pid, "person_id": person_id,
                "etype": etype, "title": title, "desc": desc,
                "ev_date": ev_date, "ev_date_norm": ev_date_norm,
                "location": location,
                "citation": f"Library genealogy collection, ref #{random.randint(100, 999)}",
                "conf": random.randint(3, 5),
                "creator": random.choice(all_ids),
            })
        print(f"    Created {len(timeline_events)} timeline events")
        await session.commit()

    # ────────────────────────────────────────────────────────────────
    # 23. GENEALOGY EXTERNAL REFERENCES + RECORD LINKS
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_external_references"))
    if r.scalar() == 0 and project_ids:
        print("  Seeding genealogy_external_references + record_links...")
        ext_refs = [
            ("familysearch", "FS-M1ZN-234", "https://www.familysearch.org/ark:/12345", "Johnson Family in 1850 Census", "Census Record"),
            ("ancestry", "AN-98765432", "https://www.ancestry.com/record/12345", "O'Brien Passenger List", "Immigration Record"),
            ("findagrave", "FG-12345678", "https://www.findagrave.com/memorial/12345", "Schmidt Family Plot", "Memorial"),
            ("newspapers_com", "NP-5678", "https://www.newspapers.com/clip/12345", "Caldwell Printing Press Article", "Newspaper"),
            ("wikitree", "WT-Johnson-123", "https://www.wikitree.com/wiki/Johnson-12345", "Johnson Family WikiTree Profile", "Family Tree"),
            ("FOLD3", "F3-MIL-456", "https://www.fold3.com/record/12345", "O'Brien Civil War Service Record", "Military Record"),
        ]
        for source, ext_id, url, title, rec_type in ext_refs:
            pid = random.choice(project_ids)
            person_id = random.choice(all_person_ids) if random.random() < 0.7 else None
            doc_id_val = random.choice(doc_ids) if doc_ids and random.random() < 0.3 else None
            await session.execute(text("""
                INSERT INTO genealogy_external_references
                    (project_id, person_id, document_id, source,
                     external_id, external_url, record_title,
                     record_type, sync_status, created_by)
                VALUES
                    (:pid, :person_id, :doc_id, :source,
                     :ext_id, :url, :title,
                     :rec_type, 'synced', :creator)
            """), {
                "pid": pid, "person_id": person_id,
                "doc_id": doc_id_val, "source": source,
                "ext_id": ext_id, "url": url, "title": title,
                "rec_type": rec_type,
                "creator": random.choice(all_ids),
            })

        # Record links (potential matches between documents/persons)
        if all_person_ids and len(all_person_ids) >= 4:
            links_data = [
                (all_person_ids[0], all_person_ids[2], 0.85, "Name and location match", "name,location", "confirmed"),
                (all_person_ids[1], all_person_ids[3], 0.72, "Name similar, date close", "name,date", "pending_review"),
                (all_person_ids[4], all_person_ids[6], 0.60, "Location match only", "location", "suggested"),
            ]
            for sp, tp, score, reasons, fields, status in links_data:
                pid = random.choice(project_ids)
                await session.execute(text("""
                    INSERT INTO genealogy_record_links
                        (project_id, source_person_id, target_person_id,
                         similarity_score, match_reasons, matched_fields,
                         status)
                    VALUES
                        (:pid, :sp, :tp, :score, :reasons, :fields, :status)
                """), {
                    "pid": pid, "sp": sp, "tp": tp,
                    "score": score, "reasons": reasons, "fields": fields,
                    "status": status,
                })
        print(f"    Created {len(ext_refs)} external references, 3 record links")
        await session.commit()

    # ────────────────────────────────────────────────────────────────
    # 24. GENEALOGY INQUIRIES
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_inquiries"))
    if r.scalar() == 0:
        print("  Seeding genealogy_inquiries...")
        inquiries = [
            ("Martha", "Peterson", "mpeterson@example.com", "555-0201", "email", "getting_started",
             "I'm brand new to genealogy and want to trace my family back to the 1800s. Where do I start?",
             "Don't know where to begin", "open",
             "Welcome! I'd recommend starting with what you know and working backward. We have free access to FamilySearch.org on our library computers and I'd love to schedule a one-on-one orientation."),
            ("Robert", "Kim", "rkim@example.com", None, "email", "dna",
             "I got my DNA results back from AncestryDNA and I'm confused by the matches. Can someone help me interpret them?",
             "Too many matches, don't know which are relevant", "in_progress", None),
            ("Sarah", "Blackwood", "sblackwood@example.com", "555-0203", "phone", "census",
             "I found my great-grandmother in the 1920 census but can't find her in 1910. She would have been about 15 in 1910.",
             "Possible name change or different household", "responded",
             "There are several reasons someone might be missing from a census. She may have been listed under a maiden name, living with relatives, or the record may have been damaged. Let's look together."),
            ("James", "Whitfield", "jwhitfield@example.com", "555-0204", "email", "immigration",
             "My family came from Germany in the 1880s. I have a last name and approximate arrival date. How can I find the ship records?",
             "Only have family oral history, no documents", "open", None),
            ("Dorothy", "Williams", "dwilliams@example.com", None, "email", "local_resources",
             "I'm researching African-American families in Springfield before 1860. What local resources do you have?",
             "Pre-Civil War records are very limited", "responded",
             "This is an area of special focus for our local history room. We have church records, freedmen's bureau records, and a growing digital collection. I'd recommend scheduling time with our genealogist."),
        ]
        for first, last, email, phone, pref, topic, desc, challenges, status, response in inquiries:
            uid = random.choice(all_ids) if random.random() < 0.5 else None
            responder = random.choice(staff_ids) if response else None
            await session.execute(text("""
                INSERT INTO genealogy_inquiries
                    (user_id, first_name, last_name, email, phone,
                     preferred_contact, research_topic, description,
                     current_challenges, status,
                     response_from_genealogist, responded_by,
                     responded_at, created_at)
                VALUES
                    (:uid, :first, :last, :email, :phone,
                     :pref, :topic, :desc,
                     :challenges, :status,
                     :response, :responder,
                     :responded_at, :created_at)
            """), {
                "uid": uid, "first": first, "last": last,
                "email": email, "phone": phone, "pref": pref,
                "topic": topic, "desc": desc,
                "challenges": challenges, "status": status,
                "response": response, "responder": responder,
                "responded_at": _past(random.randint(1, 14)) if response else None,
                "created_at": _past(random.randint(5, 60)),
            })
        print(f"    Created {len(inquiries)} genealogy inquiries")
        await session.commit()

    # ────────────────────────────────────────────────────────────────
    # 25. GENEALOGY TRAINING COURSES
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_training_courses"))
    if r.scalar() == 0:
        print("  Seeding genealogy_training_courses...")
        courses = [
            ("Introduction to Genealogy Research", "Learn the fundamentals of family history research including record types, research strategies, and getting started with online databases.",
             "beginner", 120, "Saturday", "10:00 AM", "Local History Room", False, True, 15),
            ("Using FamilySearch and Ancestry.com", "Hands-on workshop for navigating the two most popular genealogy databases. Bring your family names and dates!",
             "beginner", 90, "Wednesday", "6:30 PM", "Computer Lab", False, True, 12),
            ("Census Records Deep Dive", "Advanced techniques for extracting maximum information from US Census records, 1790-1940.",
             "intermediate", 90, "Thursday", "2:00 PM", "Local History Room", False, True, 10),
            ("DNA for Genealogists", "Understanding autosomal DNA results, genetic genealogy methodology, and how to use DNA to break through brick walls.",
             "advanced", 150, "Saturday", "1:00 PM", "Community Room A", False, True, 20),
            ("African-American Genealogy Research", "Specialized techniques for researching African-American ancestors, including pre-Civil War records, freedmen's bureau, and oral history methods.",
             "intermediate", 120, "Tuesday", "6:00 PM", "Local History Room", False, True, 15),
            ("Virtual Genealogy Help Desk", "Drop-in virtual session for one-on-one genealogy assistance. Bring your questions and brick walls!",
             "beginner", 60, "Monday", "12:00 PM", None, True, True, 8),
        ]
        for title, desc, level, duration, day, time_str, location, virtual, active, max_enroll in courses:
            await session.execute(text("""
                INSERT INTO genealogy_training_courses
                    (title, description, difficulty_level, duration_minutes,
                     next_session_day, next_session_time, location,
                     is_active, is_virtual, max_enrollment,
                     created_at, updated_at)
                VALUES
                    (:title, :desc, :level, :duration,
                     :day, :time, :location,
                     :active, :virtual, :max_enroll,
                     :created, :created)
            """), {
                "title": title, "desc": desc, "level": level,
                "duration": duration, "day": day, "time": time_str,
                "location": location, "active": active,
                "virtual": virtual, "max_enroll": max_enroll,
                "created": _past(random.randint(30, 120)),
            })
        print(f"    Created {len(courses)} training courses")
        await session.commit()

    # ────────────────────────────────────────────────────────────────
    # 26. GENEALOGY DNA PROFILES + DNA MATCHES
    # ────────────────────────────────────────────────────────────────
    r = await session.execute(text("SELECT COUNT(*) FROM genealogy_dna_profiles"))
    if r.scalar() == 0 and all_person_ids and project_ids:
        print("  Seeding genealogy_dna_profiles + dna_matches...")
        # Create DNA profiles for some persons
        dna_profiles = [
            ("autosomal", "AncestryDNA", "ANC-12345", date(2024, 6, 15), "R-M269",
             "English/Welsh 45%, Irish/Scottish 30%, Germanic 15%, Other 10%"),
            ("autosomal", "23andMe", "23M-67890", date(2025, 1, 10), None,
             "Irish 55%, British 25%, French/German 15%, Scandinavian 5%"),
            ("y_dna", "FamilyTreeDNA", "FT-Y-111", date(2024, 9, 20), "I-M253",
             "Bavarian/German ancestry confirmed"),
            ("mt_dna", "FamilyTreeDNA", "FT-MT-222", date(2025, 3, 1), "H1",
             "Western European maternal lineage"),
        ]
        profile_ids = []
        for test_type, company, kit, test_date, haplo, ethnicity in dna_profiles:
            person_id = random.choice(all_person_ids)
            pid = random.choice(project_ids)
            r2 = await session.execute(text("""
                INSERT INTO genealogy_dna_profiles
                    (person_id, project_id, test_type, testing_company,
                     kit_number, test_date, haplogroup, ethnicity_estimate,
                     consent_given, consent_date, consent_scope, created_by)
                VALUES
                    (:person_id, :pid, :test_type, :company,
                     :kit, :test_date, :haplo, :ethnicity,
                     true, :consent_date, 'research_and_matching', :creator)
                RETURNING id
            """), {
                "person_id": person_id, "pid": pid,
                "test_type": test_type, "company": company,
                "kit": kit, "test_date": test_date,
                "haplo": haplo, "ethnicity": ethnicity,
                "consent_date": _past(random.randint(30, 365)),
                "creator": random.choice(all_ids),
            })
            profile_ids.append(r2.scalar())

        # DNA matches between profiles
        if len(profile_ids) >= 2:
            matches = [
                (profile_ids[0], profile_ids[1], 1750.0, 68, 85.5, "1st-2nd Cousin", 0.92, "confirmed"),
                (profile_ids[0], profile_ids[2], 450.0, 22, 35.2, "3rd-4th Cousin", 0.75, "reviewing"),
            ]
            for p1, p2, cm, segs, longest, predicted, conf, status in matches:
                await session.execute(text("""
                    INSERT INTO genealogy_dna_matches
                        (profile1_id, profile2_id, shared_centimorgans,
                         shared_segments, longest_segment,
                         predicted_relationship, confidence_level, status, notes)
                    VALUES
                        (:p1, :p2, :cm, :segs, :longest,
                         :predicted, :conf, :status, :notes)
                """), {
                    "p1": p1, "p2": p2, "cm": cm, "segs": segs,
                    "longest": longest, "predicted": predicted,
                    "conf": conf, "status": status,
                    "notes": f"Match identified via {random.choice(['AncestryDNA', '23andMe', 'GEDmatch'])} database",
                })
        print(f"    Created {len(dna_profiles)} DNA profiles, {min(2, max(0, len(profile_ids) - 1))} matches")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "genealogy_research_projects", "genealogy_persons",
        "genealogy_family_relationships", "genealogy_documents",
        "genealogy_person_document_links", "genealogy_project_collaborators",
        "genealogy_research_notes", "genealogy_research_guidance",
        "genealogy_timeline_events", "genealogy_external_references",
        "genealogy_record_links", "genealogy_inquiries",
        "genealogy_training_courses", "genealogy_dna_profiles",
        "genealogy_dna_matches",
    ]
    for table in seq_tables:
        try:
            async with session.begin_nested():
                await session.execute(text(
                    f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                ))
        except SQLAlchemyError:
            pass

    await session.commit()
    print("  Niche domains (Cannabis + Genealogy) seeding complete!")
    return True
