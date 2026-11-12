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


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


def _future_date(days_ahead: int) -> date:
    return (datetime.now(utc) + timedelta(days=days_ahead)).date()


async def seed_batch_compliance(session: AsyncSession) -> bool:

    # Grab reusable IDs
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    branches_r = await session.execute(text("SELECT id, name FROM branches"))
    branches = branches_r.fetchall()
    branch_names = [b[1] for b in branches]

    ucr_r = await session.execute(text("SELECT id FROM unified_compliance_requirements"))
    ucr_ids = [r[0] for r in ucr_r.fetchall()]

    now = datetime.now(utc)
    ORG_ID = 1  # organization_id has no FK constraint

    # ════════════════════════════════════════════════════════════════
    # 1. LEGAL TOPICS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM legal_topics"))
    if r.scalar() == 0:
        print("  Seeding legal_topics...")
        topics = [
            ("Family Law", "family-law", "Information about divorce, custody, child support, and adoption.", 1, "users", "#8B5CF6",
             '\'{"family","divorce","custody","child-support","adoption"}\''),
            ("Housing & Tenant Rights", "housing-tenant-rights", "Guides for renters, landlords, eviction defense, and fair housing.", 2, "home", "#3B82F6",
             '\'{"housing","tenant","eviction","rent","landlord"}\''),
            ("Consumer Rights", "consumer-rights", "Protection against fraud, debt collection, and unfair practices.", 3, "shield", "#10B981",
             '\'{"consumer","debt","fraud","credit","collections"}\''),
            ("Employment Law", "employment-law", "Workplace rights, discrimination, wage theft, and unemployment.", 4, "briefcase", "#F59E0B",
             '\'{"employment","wages","discrimination","unemployment","workers-rights"}\''),
            ("Immigration", "immigration", "Visa information, citizenship, DACA, and immigrant rights.", 5, "globe", "#EC4899",
             '\'{"immigration","visa","citizenship","daca","naturalization"}\''),
            ("Criminal Law", "criminal-law", "Understanding charges, rights of the accused, and expungement.", 6, "gavel", "#EF4444",
             '\'{"criminal","expungement","rights","charges","defense"}\''),
            ("Small Claims Court", "small-claims", "Filing and defending small claims cases up to the jurisdictional limit.", 7, "scale", "#6366F1",
             '\'{"small-claims","court","dispute","filing"}\''),
            ("Elder Law", "elder-law", "Legal issues affecting seniors including guardianship and elder abuse.", 8, "heart", "#F97316",
             '\'{"elder","senior","guardianship","abuse","estate"}\''),
        ]
        for name, slug, desc, order, icon, color, kw_literal in topics:
            await session.execute(text(f"""
                INSERT INTO legal_topics (name, slug, description, display_order, icon, color,
                    is_active, is_featured, keywords, view_count, created_by_id)
                VALUES (:name, :slug, :desc, :ord, :icon, :color,
                    true, :featured, {kw_literal}::varchar[], :views, :creator)
            """), {
                "name": name, "slug": slug, "desc": desc, "ord": order,
                "icon": icon, "color": color,
                "featured": order <= 4,
                "views": random.randint(50, 500),
                "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(topics)} legal topics")
        await session.commit()

    # Fetch topic IDs for later use
    topic_r = await session.execute(text("SELECT id FROM legal_topics ORDER BY id"))
    topic_ids = [r[0] for r in topic_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 2. LEGAL GLOSSARY TERMS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM legal_glossary_terms"))
    if r.scalar() == 0:
        print("  Seeding legal_glossary_terms...")
        terms = [
            ("Plaintiff", "plaintiff", "The person who starts a lawsuit.", "The person who files a complaint in court to start a legal case.", "The party who initiates a civil action by filing a complaint with the court.", "PLAYN-tif"),
            ("Defendant", "defendant", "The person being sued.", "The person or entity against whom a lawsuit or criminal charge is brought.", "The party against whom relief or recovery is sought in an action or suit.", "dih-FEN-dunt"),
            ("Subpoena", "subpoena", "A court order to appear in court.", "A written order issued by a court requiring a person to appear in court or produce documents.", "A writ commanding a person designated in it to appear in court under penalty for failure.", "suh-PEE-nuh"),
            ("Affidavit", "affidavit", "A written statement sworn to be true.", "A written statement of facts that a person swears is true, signed before a notary public.", "A voluntary declaration of facts written down and sworn to by the declarant before an officer authorized to administer oaths.", "af-ih-DAY-vit"),
            ("Jurisdiction", "jurisdiction", "The power of a court to hear a case.", "The legal authority of a court to hear and decide a particular type of case.", "The power, right, or authority to interpret and apply the law within a defined territory.", "joor-is-DIK-shun"),
            ("Statute of Limitations", "statute-of-limitations", "The deadline for filing a lawsuit.", "The maximum time allowed by law to file a lawsuit after an event has occurred.", "A legislative enactment prescribing the period within which a legal action may be brought.", "STACH-oot of lim-ih-TAY-shunz"),
            ("Pro Bono", "pro-bono", "Free legal work.", "Legal services provided for free, usually for people who cannot afford an attorney.", "Professional work undertaken voluntarily and without payment as a public service.", "pro BOH-noh"),
            ("Deposition", "deposition", "Giving testimony outside of court.", "A witness's sworn out-of-court testimony that is recorded for later use in court.", "The testimony of a witness taken upon oral examination, under oath, and reduced to writing.", "dep-oh-ZIH-shun"),
            ("Arraignment", "arraignment", "The first court appearance after arrest.", "The formal court proceeding where a defendant hears the charges and enters a plea.", "The initial step in a criminal prosecution whereby the defendant is brought before the court to hear charges and enter a plea.", "uh-RAYN-ment"),
            ("Expungement", "expungement", "Erasing a criminal record.", "The legal process of sealing or destroying a criminal record so it is no longer visible to the public.", "The judicial process by which a record of criminal conviction is destroyed or sealed from the state or federal repository.", "ex-PUNJ-ment"),
            ("Lien", "lien", "A legal claim on property.", "A legal right to keep or sell someone's property until a debt is paid.", "A charge upon real or personal property for the satisfaction of some debt or duty.", "LEEN"),
            ("Habeas Corpus", "habeas-corpus", "A request to bring a prisoner to court.", "A legal action that requires a person being detained to be brought before a judge.", "A writ requiring a person under arrest to be brought before a judge or into court to secure their release.", "HAY-bee-us KOR-pus"),
            ("Tort", "tort", "A wrongful act that causes harm.", "A wrongful act, other than a breach of contract, that causes injury and for which the injured party can sue.", "A wrongful act other than a breach of contract for which relief may be obtained in the form of damages.", "TORT"),
            ("Probate", "probate", "The legal process after someone dies.", "The court-supervised process of distributing a deceased person's assets according to their will or state law.", "The judicial process whereby a will is proved in a court of competent jurisdiction and is established as a valid public document.", "PROH-bayt"),
            ("Power of Attorney", "power-of-attorney", "Legal permission to act for someone else.", "A legal document giving one person the authority to act on behalf of another person.", "An instrument authorizing another to act as one's agent or attorney-in-fact.", "POW-er of uh-TUR-nee"),
        ]
        for term, slug, simple, standard, legal, pron in terms:
            await session.execute(text("""
                INSERT INTO legal_glossary_terms (term, slug, definition_simple, definition_standard,
                    definition_legal, pronunciation, is_active, view_count)
                VALUES (:term, :slug, :simple, :standard, :legal, :pron, true, :views)
            """), {
                "term": term, "slug": slug, "simple": simple, "standard": standard,
                "legal": legal, "pron": pron, "views": random.randint(10, 300),
            })
        print(f"    Created {len(terms)} legal glossary terms")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 3. LEGAL GUIDES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM legal_guides"))
    if r.scalar() == 0 and topic_ids:
        print("  Seeding legal_guides...")
        guides = [
            ("How to File for Divorce", "how-to-file-for-divorce", 0, "Step-by-step guide to filing for divorce in your state.",
             "This guide walks you through the divorce process from filing the initial petition through the final decree.",
             "high_school", True),
            ("Understanding Your Rights as a Tenant", "understanding-tenant-rights", 1, "Know your rights before signing a lease.",
             "This guide covers lease agreements, security deposits, maintenance responsibilities, and eviction protections.",
             "middle_school", True),
            ("How to Dispute a Debt", "how-to-dispute-a-debt", 2, "Steps to challenge incorrect or unfair debt collection.",
             "Learn how to verify a debt, write a dispute letter, and understand your rights under the Fair Debt Collection Practices Act.",
             "high_school", False),
            ("Filing a Wage Claim", "filing-a-wage-claim", 3, "What to do when your employer owes you wages.",
             "This guide explains how to calculate unpaid wages, file a complaint with the labor department, and pursue legal action if needed.",
             "high_school", False),
            ("Small Claims Court: A Complete Guide", "small-claims-court-guide", 6, "Everything you need to know about small claims court.",
             "From filing your claim to presenting your case, this guide covers the entire small claims process.",
             "college", True),
            ("Expungement: Clearing Your Record", "expungement-guide", 5, "How to petition for expungement of a criminal record.",
             "This guide explains eligibility requirements, the petition process, and what to expect at the hearing.",
             "high_school", False),
        ]
        for title, slug, topic_idx, summary, content, level, featured in guides:
            tid = topic_ids[topic_idx] if topic_idx < len(topic_ids) else topic_ids[0]
            await session.execute(text("""
                INSERT INTO legal_guides (title, slug, topic_id, summary, content, reading_level,
                    is_published, is_featured, view_count, helpful_count, not_helpful_count,
                    published_at, created_by_id)
                VALUES (:title, :slug, :tid, :summary, :content, :level,
                    true, :featured, :views, :helpful, :not_helpful,
                    :published, :creator)
            """), {
                "title": title, "slug": slug, "tid": tid, "summary": summary,
                "content": content, "level": level, "featured": featured,
                "views": random.randint(100, 1000),
                "helpful": random.randint(20, 200),
                "not_helpful": random.randint(1, 20),
                "published": _past(random.randint(30, 365)),
                "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(guides)} legal guides")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 4. LEGAL DOCUMENTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM legal_documents"))
    if r.scalar() == 0:
        print("  Seeding legal_documents...")
        docs = [
            ("Library Internet Use Policy", "DOC-2024-001", "OTHER", "patron_services", "Official internet and computer use policy for all branches.", "verified"),
            ("Patron Privacy Policy", "DOC-2024-002", "OTHER", "privacy_data", "Comprehensive patron data privacy and confidentiality policy.", "verified"),
            ("CIPA Compliance Certification", "DOC-2024-003", "OTHER", "technology", "Annual CIPA compliance certification for E-Rate eligibility.", "verified"),
            ("Collection Development Policy", "DOC-2024-004", "OTHER", "collections", "Guidelines for material selection, acquisition, and weeding.", "reviewed"),
            ("Meeting Room Use Agreement", "DOC-2024-005", "OTHER", "facilities", "Terms and conditions for public use of library meeting spaces.", "verified"),
            ("Volunteer Agreement Form", "DOC-2023-006", "OTHER", "volunteer_management", "Volunteer rights, responsibilities, and liability waiver.", "reviewed"),
            ("Staff Acceptable Use Policy", "DOC-2024-007", "OTHER", "hr_employment", "Employee technology use and data handling requirements.", "verified"),
            ("ADA Accessibility Plan", "DOC-2024-008", "OTHER", "accessibility", "Plan for ensuring ADA compliance across all facilities and services.", "reviewed"),
            ("Records Retention Schedule", "DOC-2024-009", "OTHER", "governance", "Official schedule for retention and disposal of library records.", "verified"),
            ("Intellectual Freedom Statement", "DOC-2023-010", "OTHER", "patron_services", "Board-adopted statement on intellectual freedom and censorship.", "verified"),
        ]
        for title, doc_num, doc_type, category, desc, review_status in docs:
            await session.execute(text("""
                INSERT INTO legal_documents (title, document_number, document_type, category, description,
                    status, effective_date, last_reviewed_date, next_review_date,
                    responsible_department, owner_id, approval_required, created_by_id)
                VALUES (:title, :doc_num, :doc_type, :cat, :desc,
                    :status, :eff, :reviewed, :next_review,
                    :dept, :owner, true, :creator)
            """), {
                "title": title, "doc_num": doc_num, "doc_type": doc_type, "cat": category,
                "desc": desc, "status": review_status,
                "eff": _past_date(random.randint(60, 400)),
                "reviewed": _past_date(random.randint(10, 90)),
                "next_review": _future_date(random.randint(90, 365)),
                "dept": "Administration",
                "owner": random.choice(staff_ids),
                "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(docs)} legal documents")
        await session.commit()

    # Fetch legal_document IDs
    doc_r = await session.execute(text("SELECT id FROM legal_documents ORDER BY id"))
    legal_doc_ids = [r[0] for r in doc_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 5. LEGAL FORMS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM legal_forms"))
    if r.scalar() == 0 and topic_ids:
        print("  Seeding legal_forms...")
        forms = [
            ("Petition for Dissolution of Marriage", "FL-100", 0, "Family", "State Court", "Petition to begin divorce proceedings.",
             "easy", 4, 435.00, 30),
            ("Response to Petition for Dissolution", "FL-120", 0, "Family", "State Court", "Response form for the non-filing spouse.",
             "moderate", 4, 435.00, 45),
            ("Request for Fee Waiver", "FW-001", 2, "General", "All Courts", "Application to waive court filing fees based on financial need.",
             "easy", 3, 0.00, 15),
            ("Small Claims Complaint", "SC-100", 6, "Civil", "Small Claims Court", "Form to file a small claims case.",
             "easy", 2, 75.00, 20),
            ("Unlawful Detainer Answer", "UD-105", 1, "Housing", "Civil Court", "Response form for tenants facing eviction.",
             "moderate", 4, 0.00, 45),
            ("Petition for Expungement", "CR-180", 5, "Criminal", "Superior Court", "Petition to seal or expunge a criminal record.",
             "complex", 6, 150.00, 60),
            ("Wage Claim Application", "DLSE-1", 3, "Employment", "Labor Board", "Form to file a wage claim with the state labor department.",
             "easy", 3, 0.00, 30),
            ("Name Change Petition", "NC-100", 0, "Family", "Superior Court", "Petition for legal name change.",
             "moderate", 5, 435.00, 45),
        ]
        for title, form_num, topic_idx, category, court, desc, difficulty, pages, fee, est_time in forms:
            tid = topic_ids[topic_idx] if topic_idx < len(topic_ids) else topic_ids[0]
            await session.execute(text("""
                INSERT INTO legal_forms (title, form_number, topic_id, category, jurisdiction,
                    court_type, description, difficulty_level, page_count, filing_fee,
                    estimated_completion_time, status, view_count, download_count, created_by_id)
                VALUES (:title, :form_num, :tid, :cat, 'CALIFORNIA',
                    :court, :desc, :difficulty, :pages, :fee,
                    :est_time, 'active', :views, :downloads, :creator)
            """), {
                "title": title, "form_num": form_num, "tid": tid, "cat": category,
                "court": court, "desc": desc, "difficulty": difficulty,
                "pages": pages, "fee": fee, "est_time": est_time,
                "views": random.randint(50, 500),
                "downloads": random.randint(10, 200),
                "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(forms)} legal forms")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 6. LEGAL SERVICE PROVIDERS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM legal_service_providers"))
    if r.scalar() == 0:
        print("  Seeding legal_service_providers...")
        providers = [
            ("Legal Aid Society of Metro", "legal-aid-society-metro", "legal_aid",
             "Free civil legal services for low-income residents.",
             "(555) 123-4567", "intake@legalaidmetro.org", "https://legalaidmetro.org",
             "100 Justice Blvd", "Springfield", "IL", "62701"),
            ("Pro Bono Legal Clinic", "pro-bono-legal-clinic", "pro_bono",
             "Volunteer attorneys providing free consultations on civil matters.",
             "(555) 234-5678", "info@probonolegal.org", "https://probonolegal.org",
             "200 Court St", "Springfield", "IL", "62702"),
            ("State University Law School Clinic", "state-law-school-clinic", "law_school_clinic",
             "Law students supervised by professors offer free legal help.",
             "(555) 345-6789", "lawclinic@stateuniv.edu", "https://law.stateuniv.edu/clinic",
             "500 University Ave", "Springfield", "IL", "62703"),
            ("County Bar Association Referral Service", "county-bar-referral", "bar_association",
             "Referrals to local attorneys offering reduced-rate initial consultations.",
             "(555) 456-7890", "referrals@countybar.org", "https://countybar.org",
             "75 Bar Association Dr", "Springfield", "IL", "62704"),
            ("Senior Legal Helpline", "senior-legal-helpline", "hotline",
             "Free telephone legal advice for residents age 60 and older.",
             "(555) 567-8901", "help@seniorlegal.org", "https://seniorlegal.org",
             None, None, None, None),
        ]
        for name, slug, ptype, desc, phone, email, website, addr, city, state, zipcode in providers:
            langs_literal = "'{\"English\",\"Spanish\"}'"
            await session.execute(text(f"""
                INSERT INTO legal_service_providers (name, slug, provider_type, description,
                    phone, email, website, address_line1, city, state, zip_code,
                    languages_spoken, is_active, is_verified, view_count, referral_count, created_by_id)
                VALUES (:name, :slug, :ptype, :desc,
                    :phone, :email, :website, :addr, :city, :state, :zip,
                    {langs_literal}::varchar[], true, true, :views, :refs, :creator)
            """), {
                "name": name, "slug": slug, "ptype": ptype, "desc": desc,
                "phone": phone, "email": email, "website": website,
                "addr": addr, "city": city, "state": state, "zip": zipcode,
                "views": random.randint(20, 200),
                "refs": random.randint(5, 50),
                "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(providers)} legal service providers")
        await session.commit()

    # Fetch provider IDs
    prov_r = await session.execute(text("SELECT id FROM legal_service_providers ORDER BY id"))
    provider_ids = [r[0] for r in prov_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 7. LEGAL CLINICS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM legal_clinics"))
    if r.scalar() == 0 and topic_ids and provider_ids:
        print("  Seeding legal_clinics...")
        clinics = [
            ("Free Family Law Clinic", 0, 0, "One-on-one consultations with volunteer family law attorneys.",
             30, "Community Room A", False, "completed", 12, 2),
            ("Tenant Rights Workshop", 1, 1, "Group workshop on tenant rights followed by individual Q&A.",
             60, "Community Room B", False, "completed", 20, 0),
            ("Expungement Clinic", 5, 2, "Help filing expungement petitions with law student assistance.",
             14, None, True, "scheduled", 15, 3),
            ("Small Claims Court Help Desk", 6, 3, "Drop-in help with small claims forms and procedures.",
             90, "Reference Desk Area", False, "registration_open", 10, 2),
        ]
        for name, topic_idx, prov_idx, desc, days_offset, location, virtual, status, cap, waitlist_cap in clinics:
            tid = topic_ids[topic_idx] if topic_idx < len(topic_ids) else topic_ids[0]
            pid = provider_ids[prov_idx] if prov_idx < len(provider_ids) else provider_ids[0]
            clinic_date = _past_date(days_offset) if status == "completed" else _future_date(days_offset)
            regs = random.randint(3, cap) if status == "completed" else random.randint(0, cap // 2)
            langs_literal = "'{\"English\",\"Spanish\"}'"
            what_to_bring = json.dumps(["Photo ID", "Relevant documents", "Court papers if any"])
            await session.execute(text(f"""
                INSERT INTO legal_clinics (name, topic_id, description, provider_id,
                    date, start_time, end_time, timezone, is_virtual, location,
                    capacity, current_registrations, waitlist_capacity, current_waitlist,
                    registration_required, status, languages_available,
                    what_to_bring, wheelchair_accessible, created_by_id)
                VALUES (:name, :tid, :desc, :pid,
                    :dt, :start_t, :end_t, 'America/Chicago', :virtual, :loc,
                    :cap, :regs, :wl_cap, :wl_cur,
                    true, :status, {langs_literal}::varchar[],
                    cast(:wtb as jsonb), true, :creator)
            """), {
                "name": name, "tid": tid, "desc": desc, "pid": pid,
                "dt": clinic_date, "start_t": "10:00", "end_t": "14:00",
                "virtual": virtual, "loc": location,
                "cap": cap, "regs": regs, "wl_cap": waitlist_cap, "wl_cur": 0,
                "status": status,
                "wtb": what_to_bring,
                "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(clinics)} legal clinics")
        await session.commit()

    # Fetch clinic IDs
    clinic_r = await session.execute(text("SELECT id FROM legal_clinics ORDER BY id"))
    clinic_ids = [r[0] for r in clinic_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 8. LEGAL CLINIC REGISTRATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM legal_clinic_registrations"))
    if r.scalar() == 0 and clinic_ids and patron_ids:
        print("  Seeding legal_clinic_registrations...")
        first_names = ["Maria", "James", "Patricia", "Robert", "Jennifer", "Michael",
                       "Linda", "David", "Elizabeth", "William"]
        last_names = ["Garcia", "Johnson", "Williams", "Brown", "Jones", "Davis",
                      "Miller", "Wilson", "Moore", "Taylor"]
        statuses = ["confirmed", "attended", "no_show", "cancelled", "waitlisted"]
        count = 0
        for cid in clinic_ids:
            num_regs = random.randint(2, 4)
            used_patrons = set()
            for i in range(num_regs):
                pid = random.choice(patron_ids)
                while pid in used_patrons and len(used_patrons) < len(patron_ids):
                    pid = random.choice(patron_ids)
                used_patrons.add(pid)
                fname = random.choice(first_names)
                lname = random.choice(last_names)
                status = random.choice(statuses)
                await session.execute(text("""
                    INSERT INTO legal_clinic_registrations (clinic_id, patron_id, name, email,
                        phone, status, confirmation_sent, issue_description)
                    VALUES (:cid, :pid, :name, :email,
                        :phone, :status, true, :issue)
                """), {
                    "cid": cid, "pid": pid,
                    "name": f"{fname} {lname}",
                    "email": f"{fname.lower()}.{lname.lower()}@email.com",
                    "phone": f"(555) {random.randint(100,999)}-{random.randint(1000,9999)}",
                    "status": status,
                    "issue": "General legal question regarding my situation.",
                })
                count += 1
        print(f"    Created {count} legal clinic registrations")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 9. COMPLIANCE REPORTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM compliance_reports"))
    if r.scalar() == 0:
        print("  Seeding compliance_reports...")
        reports = [
            ("cipa_erate", "Annual CIPA/E-Rate Compliance Report", 365, "approved",
             "All filtering and monitoring requirements met. Internet safety policy current.",
             95.0, 12, 11, 1, 0, 0),
            ("coppa_annual", "COPPA Compliance Assessment", 365, "approved",
             "Children's online privacy protections verified across all digital services.",
             100.0, 8, 8, 0, 0, 0),
            ("data_retention", "Data Retention Policy Compliance Review", 180, "reviewed",
             "Patron data retention schedules reviewed. Two areas need updated deletion procedures.",
             87.5, 16, 14, 2, 0, 0),
            ("law_enforcement_transparency", "Law Enforcement Request Transparency Report", 365, "submitted",
             "Annual transparency report on law enforcement data requests received and handled.",
             100.0, 5, 5, 0, 1, 0),
            ("staff_access_review", "Staff Access Privilege Review", 90, "generated",
             "Quarterly review of staff access levels and permission assignments.",
             92.0, 25, 23, 2, 0, 0),
            ("full_audit", "Full Compliance Audit - FY2025", 365, "approved",
             "Comprehensive annual compliance audit covering all regulatory areas.",
             94.5, 50, 47, 3, 2, 1),
        ]
        for rtype, title, period_days, status, summary, score, total, comp, noncomp, violations, incidents in reports:
            period_end = _past_date(random.randint(5, 30))
            period_start = period_end - timedelta(days=period_days)
            report_data = json.dumps({"audit_scope": "all_branches", "methodology": "document_review_and_testing"})
            recommendations = json.dumps(["Continue annual staff privacy training", "Update data retention automation"])
            await session.execute(text("""
                INSERT INTO compliance_reports (organization_id, report_type, title, period_start, period_end,
                    status, report_data, summary, recommendations,
                    total_requirements, compliant_count, non_compliant_count,
                    violations_count, incidents_count, compliance_score,
                    generated_by_id, generated_at, reviewed_by_id, reviewed_at)
                VALUES (:org, :rtype, :title, :ps, :pe,
                    :status, cast(:rdata as jsonb), :summary, cast(:recs as jsonb),
                    :total, :comp, :noncomp,
                    :violations, :incidents, :score,
                    :gen_by, :gen_at, :rev_by, :rev_at)
            """), {
                "org": ORG_ID, "rtype": rtype, "title": title,
                "ps": period_start, "pe": period_end,
                "status": status, "rdata": report_data,
                "summary": summary, "recs": recommendations,
                "total": total, "comp": comp, "noncomp": noncomp,
                "violations": violations, "incidents": incidents, "score": score,
                "gen_by": random.choice(staff_ids), "gen_at": _past(random.randint(5, 60)),
                "rev_by": random.choice(staff_ids), "rev_at": _past(random.randint(1, 30)),
            })
        print(f"    Created {len(reports)} compliance reports")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 10. COMPLIANCE ALERTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM compliance_alerts"))
    if r.scalar() == 0:
        print("  Seeding compliance_alerts...")
        alerts = [
            ("Privacy Policy Review Overdue", "The patron privacy policy is 30 days past its scheduled annual review date.",
             "high", "acknowledged", "policy_review_overdue", 10, "Schedule and complete the privacy policy review."),
            ("CIPA Filter Update Required", "Internet content filter definitions are 45 days old. Update recommended every 30 days.",
             "medium", "resolved", "filter_maintenance", -15, "Update content filter definitions to latest version."),
            ("Staff Privacy Training Due", "Three staff members have not completed their annual privacy and confidentiality training.",
             "medium", "active", "training_overdue", 30, "Ensure all staff complete privacy training by the deadline."),
            ("Data Retention Deletion Backlog", "Automated patron data deletion has a backlog of 150 records past retention period.",
             "high", "active", "data_retention", 14, "Clear the data deletion backlog and verify automation is working."),
            ("E-Rate Certification Deadline Approaching", "Annual E-Rate CIPA certification is due in 45 days.",
             "low", "acknowledged", "certification_deadline", 45, "Prepare and submit E-Rate CIPA certification."),
        ]
        for title, msg, severity, status, atype, due_days, action in alerts:
            due_date = _future_date(due_days) if due_days > 0 else _past_date(abs(due_days))
            await session.execute(text("""
                INSERT INTO compliance_alerts (title, message, severity, status, alert_type,
                    due_date, action_required, assigned_to_id, created_at)
                VALUES (:title, :msg, :severity, :status, :atype,
                    :due, :action, :assigned, :created)
            """), {
                "title": title, "msg": msg, "severity": severity, "status": status,
                "atype": atype, "due": due_date, "action": action,
                "assigned": random.choice(staff_ids),
                "created": _past(random.randint(5, 60)),
            })
        print(f"    Created {len(alerts)} compliance alerts")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 11. COMPLIANCE VIOLATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM compliance_violations"))
    if r.scalar() == 0 and ucr_ids:
        print("  Seeding compliance_violations...")
        violations = [
            ("Patron Data Retained Beyond Policy", "Circulation records for 47 patrons were retained 6 months beyond the 3-year retention period.",
             "medium", "resolved", "Internal audit", "automated_scan", 47, 47, False),
            ("Staff Access to Patron Records Without Need", "A staff member accessed patron borrowing history outside their job duties.",
             "high", "remediating", "Access log review", "log_analysis", 1, 1, False),
            ("CIPA Filter Bypass on Children Terminal", "Content filter was temporarily disabled on a children area computer during maintenance and not re-enabled.",
             "critical", "resolved", "Staff report", "manual_discovery", 0, 0, True),
        ]
        for title, desc, severity, status, detected_by, method, records, users_count, minors in violations:
            await session.execute(text("""
                INSERT INTO compliance_violations (organization_id, requirement_id, title, description,
                    severity, status, detected_at, detected_by, detection_method,
                    affected_records_count, affected_users_count, involves_minors,
                    assigned_to_id, remediation_plan, remediation_deadline)
                VALUES (:org, :req_id, :title, :desc,
                    :severity, :status, :detected, :detected_by, :method,
                    :records, :users, :minors,
                    :assigned, :plan, :deadline)
            """), {
                "org": ORG_ID, "req_id": random.choice(ucr_ids),
                "title": title, "desc": desc,
                "severity": severity, "status": status,
                "detected": _past(random.randint(10, 90)),
                "detected_by": detected_by, "method": method,
                "records": records, "users": users_count, "minors": minors,
                "assigned": random.choice(staff_ids),
                "plan": "Investigate root cause, remediate, and implement preventive controls.",
                "deadline": _future_date(random.randint(7, 30)),
            })
        print(f"    Created {len(violations)} compliance violations")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 12. COMPLIANCE INCIDENTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM compliance_incidents"))
    if r.scalar() == 0:
        print("  Seeding compliance_incidents...")
        incidents = [
            ("INC-2025-001", "unauthorized_access", "minor", "resolved",
             "Unauthorized Access to Patron Account",
             "Staff member accessed a patron account without a service-related reason. Discovered during routine access log review.",
             "log_review"),
            ("INC-2025-002", "filtering_failure", "major", "closed",
             "Content Filter Outage During Peak Hours",
             "Internet content filter service experienced a 2-hour outage affecting all public terminals. Children terminals were taken offline as a precaution.",
             "staff_report"),
            ("INC-2026-001", "policy_violation", "minor", "resolved",
             "Patron Data Shared Without Authorization",
             "A staff member verbally confirmed a patron borrowing status to a family member over the phone without proper verification. No written records disclosed.",
             "patron_complaint"),
        ]
        for inc_num, category, severity, status, title, desc, discovery in incidents:
            containment = json.dumps(["Disabled staff access temporarily", "Reviewed access logs"])
            remediation = json.dumps(["Retrained staff on privacy policy", "Updated access controls"])
            preventive = json.dumps(["Enhanced monitoring alerts", "Quarterly access reviews"])
            await session.execute(text("""
                INSERT INTO compliance_incidents (organization_id, incident_number, category, severity, status,
                    title, description, discovery_method, discovery_date,
                    affected_systems, affected_data_types, regulations_implicated,
                    reported_by_id, assigned_to_id, reported_at,
                    is_contained, containment_actions, remediation_actions, preventive_measures,
                    notification_required, notification_sent, lessons_learned)
                VALUES (:org, :inc_num, :cat, :sev, :status,
                    :title, :desc, :discovery, :disc_date,
                    '{"ILS","patron_database"}'::varchar[], '{"patron_records"}'::varchar[], '{"state_privacy_law"}'::varchar[],
                    :reporter, :assigned, :reported,
                    true, cast(:contain as jsonb), cast(:remed as jsonb), cast(:prevent as jsonb),
                    false, false, :lessons)
            """), {
                "org": ORG_ID, "inc_num": inc_num, "cat": category, "sev": severity,
                "status": status, "title": title, "desc": desc,
                "discovery": discovery, "disc_date": _past(random.randint(30, 180)),
                "reporter": random.choice(staff_ids), "assigned": random.choice(staff_ids),
                "reported": _past(random.randint(30, 180)),
                "contain": containment, "remed": remediation, "prevent": preventive,
                "lessons": "Reinforced importance of privacy training and access control monitoring.",
            })
        print(f"    Created {len(incidents)} compliance incidents")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 13. COMPLIANCE CHECKLIST ITEMS
    # ════════════════════════════════════════════════════════════════
    lcr_r = await session.execute(text("SELECT id FROM legal_compliance_requirements LIMIT 5"))
    lcr_ids = [r[0] for r in lcr_r.fetchall()]

    r = await session.execute(text("SELECT COUNT(*) FROM compliance_checklist_items"))
    checklist_count = r.scalar()
    if checklist_count == 0 and lcr_ids:
        print("  Seeding compliance_checklist_items...")
        items = [
            ("Internet safety policy is posted at all public terminals", True),
            ("Content filtering software is active on all children computers", True),
            ("Staff have completed annual privacy training", True),
            ("Patron data retention schedule is current and enforced", True),
            ("CIPA compliance certification has been filed for E-Rate", True),
            ("Law enforcement request procedures are documented", True),
            ("Patron privacy notices are displayed at service points", True),
            ("Data breach response plan is current and tested", False),
            ("ADA accessibility audit completed within last 12 months", True),
            ("Records retention schedule reviewed and updated", True),
            ("Volunteer background check procedures are current", True),
            ("Meeting room use policy is posted and enforced", True),
            ("Collection challenge/reconsideration process is documented", True),
            ("Staff access permissions reviewed quarterly", False),
            ("Emergency procedures posted and staff trained", True),
        ]
        for i, (item_text, completed) in enumerate(items):
            req_id = lcr_ids[i % len(lcr_ids)]
            await session.execute(text("""
                INSERT INTO compliance_checklist_items (requirement_id, item_text, item_order,
                    is_completed, completed_date, completed_by_id, created_at)
                VALUES (:req_id, :text, :ord,
                    :completed, :comp_date, :comp_by, :created)
            """), {
                "req_id": req_id, "text": item_text, "ord": i + 1,
                "completed": completed,
                "comp_date": _past_date(random.randint(5, 60)) if completed else None,
                "comp_by": random.choice(staff_ids) if completed else None,
                "created": _past(90),
            })
        print(f"    Created {len(items)} compliance checklist items")
        await session.commit()
    elif checklist_count == 0 and not lcr_ids:
        print("  Skipping compliance_checklist_items (no legal_compliance_requirements)")

    # ════════════════════════════════════════════════════════════════
    # 14. AUDIT READINESS CHECKLISTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM audit_readiness_checklists"))
    if r.scalar() == 0:
        print("  Seeding audit_readiness_checklists...")
        checklists = [
            ("State Library Annual Audit", 60, 18, 1, 1, 20, 90.0, True, True, True, True,
             "Sarah Mitchell, CPA", "State Audit Services LLC"),
            ("CIPA/E-Rate Compliance Audit", 120, 12, 0, 0, 12, 100.0, True, True, True, True,
             "Federal Communications Commission", "USAC"),
            ("Internal Data Privacy Audit", 30, 8, 2, 0, 10, 80.0, False, True, True, False,
             None, None),
        ]
        for audit_type, days_ahead, complete, in_prog, not_ready, total, pct, overall, docs, staff_informed, resources, auditor, company in checklists:
            items_data = json.dumps([
                {"item": "Gather circulation statistics", "status": "complete"},
                {"item": "Compile financial reports", "status": "complete"},
                {"item": "Review policy documents", "status": "in_progress"},
            ])
            await session.execute(text("""
                INSERT INTO audit_readiness_checklists (organization_id, audit_type,
                    created_for_audit_date, checklist_created_date, checklist_last_updated_date,
                    items, items_complete, items_in_progress, items_not_ready, items_total,
                    completion_percentage, overall_ready, documentation_complete,
                    staff_informed, resources_allocated,
                    auditor_name, auditor_company,
                    audit_start_date, audit_end_date, audit_completed)
                VALUES (:org, :atype,
                    :audit_date, :created_date, :updated_date,
                    cast(:items as jsonb), :complete, :in_prog, :not_ready, :total,
                    :pct, :overall, :docs,
                    :staff, :resources,
                    :auditor, :company,
                    :start_date, :end_date, :completed)
            """), {
                "org": ORG_ID, "atype": audit_type,
                "audit_date": _future_date(days_ahead),
                "created_date": _past_date(30),
                "updated_date": _past_date(2),
                "items": items_data, "complete": complete, "in_prog": in_prog,
                "not_ready": not_ready, "total": total,
                "pct": pct, "overall": overall, "docs": docs,
                "staff": staff_informed, "resources": resources,
                "auditor": auditor, "company": company,
                "start_date": _future_date(days_ahead),
                "end_date": _future_date(days_ahead + 5),
                "completed": False,
            })
        print(f"    Created {len(checklists)} audit readiness checklists")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 15. POLICY REVIEWS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM policy_reviews"))
    if r.scalar() == 0:
        print("  Seeding policy_reviews...")
        reviews = [
            ("Circulation Policy", "Governs lending rules, fines, and renewals.", "circulation", "3.1", "current", 12),
            ("Internet Use Policy", "Acceptable use of library computers and WiFi.", "technology", "2.4", "current", 12),
            ("Privacy and Confidentiality Policy", "Patron data protection and records privacy.", "privacy", "3.0", "current", 12),
            ("Collection Development Policy", "Material selection, acquisition, and weeding.", "collection", "4.0", "pending_review", 24),
            ("Meeting Room Policy", "Public use of library meeting spaces.", "facilities", "2.0", "current", 24),
            ("Code of Conduct", "Behavioral expectations for library visitors.", "general", "2.2", "current", 12),
            ("Volunteer Policy", "Guidelines for library volunteer programs.", "human_resources", "1.1", "under_revision", 24),
            ("Social Media Policy", "Staff guidelines for official social media accounts.", "communications", "1.0", "pending_review", 12),
        ]
        for pname, desc, cat, version, status, freq in reviews:
            last_review = _past_date(random.randint(30, 365))
            next_due = last_review + timedelta(days=freq * 30)
            await session.execute(text("""
                INSERT INTO policy_reviews (organization_id, policy_name, policy_description,
                    policy_category, current_version, last_updated_date, status,
                    review_frequency_months, last_review_date, next_review_due,
                    requires_board_approval, owner_id)
                VALUES (:org, :name, :desc,
                    :cat, :ver, :updated, :status,
                    :freq, :last_rev, :next_due,
                    :board, :owner)
            """), {
                "org": ORG_ID, "name": pname, "desc": desc,
                "cat": cat, "ver": version,
                "updated": last_review,
                "status": status, "freq": freq,
                "last_rev": last_review,
                "next_due": next_due,
                "board": cat in ("circulation", "privacy", "collection"),
                "owner": random.choice(staff_ids),
            })
        print(f"    Created {len(reviews)} policy reviews")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 16. POLICY CHANGE LOG
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM policy_change_log"))
    if r.scalar() == 0:
        print("  Seeding policy_change_log...")
        changes = [
            ("circulation", "Circulation Policy", "Updated fine amounts from $0.10/day to $0.25/day for standard items."),
            ("circulation", "Circulation Policy", "Increased maximum checkouts from 20 to 25 items."),
            ("technology", "Internet Use Policy", "Added section on 3D printer acceptable use."),
            ("technology", "Internet Use Policy", "Updated CIPA filtering language to match current regulations."),
            ("privacy", "Privacy Policy", "Added data breach notification procedures per state law update."),
            ("privacy", "Privacy Policy", "Clarified patron opt-out rights for reading history."),
            ("collection", "Collection Development Policy", "Added ebook and digital resource selection criteria."),
            ("facilities", "Meeting Room Policy", "Added virtual/hybrid meeting technology provisions."),
            ("general", "Code of Conduct", "Added section on photography and recording in the library."),
            ("human_resources", "Volunteer Policy", "Updated background check requirements per state mandate."),
        ]
        for ptype, pname, reason in changes:
            before = json.dumps({"version": "previous", "status": "active"})
            after = json.dumps({"version": "current", "status": "active"})
            fields = json.dumps(["content", "version"])
            await session.execute(text("""
                INSERT INTO policy_change_log (policy_type, policy_name, changed_by_staff_id,
                    before_value, after_value, fields_changed, reason, created_at)
                VALUES (:ptype, :pname, :staff,
                    cast(:before as jsonb), cast(:after as jsonb), cast(:fields as jsonb),
                    :reason, :created)
            """), {
                "ptype": ptype, "pname": pname, "staff": random.choice(staff_ids),
                "before": before, "after": after, "fields": fields,
                "reason": reason, "created": _past(random.randint(10, 365)),
            })
        print(f"    Created {len(changes)} policy change log entries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 17. POLICY FEEDBACK
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM policy_feedback"))
    if r.scalar() == 0:
        print("  Seeding policy_feedback...")
        feedback = [
            ("Fine Structure Feedback", "Circulation Policy", "proposal",
             "Consider eliminating overdue fines for children materials to encourage reading.",
             "Research shows fine-free models increase youth engagement.", "under_review"),
            ("WiFi Time Limits", "Internet Use Policy", "concern",
             "The 60-minute WiFi session limit is too short for patrons doing job applications.",
             "Extend WiFi sessions to 2 hours or remove the limit entirely.", "accepted"),
            ("Meeting Room Hours", "Meeting Room Policy", "amendment",
             "Allow meeting room bookings until 8 PM on weeknights to accommodate working adults.",
             "Many community groups cannot meet during current restricted hours.", "partially_accepted"),
            ("Privacy Opt-Out Process", "Privacy Policy", "comment",
             "The privacy opt-out form is confusing. Could it be simplified?",
             None, "submitted"),
            ("Volunteer Age Requirement", "Volunteer Policy", "proposal",
             "Lower the minimum volunteer age from 14 to 12 with parental consent for shelving tasks.",
             "Many eager middle schoolers want to volunteer for community service hours.", "deferred"),
        ]
        for title, pname, ftype, content, proposed, status in feedback:
            await session.execute(text("""
                INSERT INTO policy_feedback (organization_id, submitted_by_id, is_anonymous,
                    policy_name, feedback_type, title, content, proposed_change, status)
                VALUES (:org, :submitted, :anon,
                    :pname, :ftype, :title, :content, :proposed, :status)
            """), {
                "org": ORG_ID,
                "submitted": random.choice(all_ids),
                "anon": random.choice([True, False]),
                "pname": pname, "ftype": ftype, "title": title,
                "content": content, "proposed": proposed, "status": status,
            })
        print(f"    Created {len(feedback)} policy feedback entries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 18. POLICY ENFORCEMENT TRACKING
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM policy_enforcement_tracking"))
    if r.scalar() == 0 and legal_doc_ids:
        print("  Seeding policy_enforcement_tracking...")
        enforcements = [
            (30, "Staff member accessed patron records without work-related need.",
             "Section 4.2 - Data Access Controls", "Circulation", "warning",
             "Verbal warning issued. Staff reminded of privacy policy requirements.", True, True),
            (60, "Failure to log off shared workstation, leaving patron data visible.",
             "Section 3.1 - Workstation Security", "IT", "training_required",
             "Staff assigned to complete workstation security refresher training.", True, True),
            (90, "Meeting room left unlocked overnight after an event.",
             "Section 2.4 - Facility Security", "Facilities", "policy_review",
             "Reviewed closing procedures with staff. Added to closing checklist.", True, True),
        ]
        for days_ago, desc, section, dept, action, details, followup, resolved in enforcements:
            await session.execute(text("""
                INSERT INTO policy_enforcement_tracking (document_id, incident_date,
                    incident_description, policy_section_violated, staff_member_id,
                    department, action_taken, action_date, action_details,
                    follow_up_required, is_resolved, resolution_date, is_confidential, created_by_id)
                VALUES (:doc_id, :inc_date,
                    :desc, :section, :staff,
                    :dept, :action, :action_date, :details,
                    :followup, :resolved, :res_date, true, :creator)
            """), {
                "doc_id": random.choice(legal_doc_ids),
                "inc_date": _past_date(days_ago),
                "desc": desc, "section": section,
                "staff": random.choice(staff_ids),
                "dept": dept, "action": action,
                "action_date": _past_date(days_ago - 2),
                "details": details,
                "followup": followup,
                "resolved": resolved,
                "res_date": _past_date(days_ago - 14) if resolved else None,
                "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(enforcements)} policy enforcement records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 19. CIPA COMPLIANCE REPORTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM cipa_compliance_reports"))
    if r.scalar() == 0:
        print("  Seeding cipa_compliance_reports...")
        cipa_reports = [
            ("Main Branch", 365, 8500, 2100, 5800, 600, 8200, 2050, 45, 38, 3, 320, 180),
            ("East Branch", 365, 4200, 1100, 2800, 300, 4100, 1080, 22, 18, 1, 150, 85),
            ("All Branches", 90, 3200, 850, 2100, 250, 3100, 830, 15, 12, 0, 95, 50),
        ]
        for branch, period_days, total, minors, adults, guests, accepts, minor_accepts, bypass_total, bypass_approved, bypass_revoked, blocks, blocks_minors in cipa_reports:
            period_end = _past(random.randint(5, 30))
            period_start = period_end - timedelta(days=period_days)
            await session.execute(text("""
                INSERT INTO cipa_compliance_reports (report_period_start, report_period_end,
                    branch_location, total_sessions, minor_sessions, adult_sessions, guest_sessions,
                    policy_acceptances, minor_policy_acceptances,
                    bypass_requests_total, bypass_requests_approved, bypass_requests_revoked,
                    filter_blocks_total, filter_blocks_minors,
                    generated_by_id)
                VALUES (:ps, :pe,
                    :branch, :total, :minors, :adults, :guests,
                    :accepts, :minor_accepts,
                    :bypass_total, :bypass_approved, :bypass_revoked,
                    :blocks, :blocks_minors,
                    :gen_by)
            """), {
                "ps": period_start, "pe": period_end,
                "branch": branch, "total": total, "minors": minors,
                "adults": adults, "guests": guests,
                "accepts": accepts, "minor_accepts": minor_accepts,
                "bypass_total": bypass_total, "bypass_approved": bypass_approved,
                "bypass_revoked": bypass_revoked,
                "blocks": blocks, "blocks_minors": blocks_minors,
                "gen_by": random.choice(staff_ids),
            })
        print(f"    Created {len(cipa_reports)} CIPA compliance reports")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 20. CIPA COMPLIANCE TRACKING
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM cipa_compliance_tracking"))
    if r.scalar() == 0:
        print("  Seeding cipa_compliance_tracking...")
        await session.execute(text("""
            INSERT INTO cipa_compliance_tracking (organization_id, status,
                blocking_filter_active, monitoring_software_active,
                content_blocks, internet_use_policy,
                written_policy_effective_date, policy_approved_by,
                monitor_activity, monitor_behavior, monitor_email,
                staff_trained_on_policy, staff_training_date,
                minor_notification_provided, parent_notification_provided,
                educational_exemptions_allowed, authorized_staff_can_bypass,
                last_check_date, next_check_due, notes)
            VALUES (:org, 'compliant',
                true, true,
                '{"obscene_material","child_pornography","harmful_to_minors"}'::varchar[], 'DOC-2024-002',
                :eff_date, 'Library Board of Trustees',
                true, true, false,
                true, :training_date,
                true, true,
                true, true,
                :last_check, :next_check, 'All CIPA requirements currently met.')
        """), {
            "org": ORG_ID,
            "eff_date": date(2024, 7, 1),
            "training_date": _past_date(45),
            "last_check": _past_date(15),
            "next_check": _future_date(75),
        })
        print("    Created 1 CIPA compliance tracking record")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 21. PUBLIC RECORDS REQUESTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM public_records_requests"))
    if r.scalar() == 0:
        print("  Seeding public_records_requests...")
        requests_data = [
            ("PRR-2025-001", "media_inquiry", "illinois", "Sarah Chen", "Daily Tribune",
             "Request for library operating budget and expenditure reports for FY2024-2025.",
             True, False, "completed", 30, 15, 3, 0),
            ("PRR-2025-002", "state_open_records", "illinois", "Michael Torres", None,
             "Request for meeting minutes from all Board of Trustees meetings in 2024.",
             False, False, "completed", 45, 12, 0, 0),
            ("PRR-2026-001", "research_request", "illinois", "Dr. Emily Watson", "State University",
             "Request for anonymized circulation statistics by material type for academic research.",
             False, False, "in_progress", 10, None, None, None),
            ("PRR-2026-002", "state_open_records", "illinois", "Robert Kim", None,
             "Request for all staff salary and benefits information for current fiscal year.",
             False, False, "records_located", 14, None, None, None),
            ("PRR-2026-003", "municipal_records", "illinois", "Jennifer Park", "City Council Office",
             "Request for facility maintenance and capital improvement expenditure reports.",
             False, False, "received", 3, None, None, None),
        ]
        for tracking, rtype, jurisdiction, name, org, desc, media, commercial, status, days_ago, resp_days, provided, withheld in requests_data:
            received = _past(days_ago)
            deadline = (received + timedelta(days=5)).date()
            await session.execute(text("""
                INSERT INTO public_records_requests (tracking_number, request_type, jurisdiction,
                    requester_name, requester_organization, is_media, is_commercial,
                    date_received, description, response_deadline,
                    extension_granted, status, fee_waived, appeal_filed,
                    records_provided_count, records_withheld_count,
                    assigned_to_id, created_by_id)
                VALUES (:tracking, :rtype, :jurisdiction,
                    :name, :org, :media, :commercial,
                    :received, :desc, :deadline,
                    false, :status, true, false,
                    :provided, :withheld,
                    :assigned, :creator)
            """), {
                "tracking": tracking, "rtype": rtype, "jurisdiction": jurisdiction,
                "name": name, "org": org, "media": media, "commercial": commercial,
                "received": received, "desc": desc, "deadline": deadline,
                "status": status,
                "provided": provided, "withheld": withheld,
                "assigned": random.choice(staff_ids),
                "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(requests_data)} public records requests")
        await session.commit()

    # Fetch public records request IDs for audit logs
    prr_r = await session.execute(text("SELECT id FROM public_records_requests ORDER BY id"))
    prr_ids = [r[0] for r in prr_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 22. PUBLIC RECORDS AUDIT LOGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM public_records_audit_logs"))
    if r.scalar() == 0 and prr_ids:
        print("  Seeding public_records_audit_logs...")
        count = 0
        actions_sequence = ["request_received", "request_acknowledged", "records_search_started",
                            "records_located", "records_released"]
        for pid in prr_ids:
            num_actions = random.randint(2, len(actions_sequence))
            for i in range(num_actions):
                details = json.dumps({"action_detail": f"Step {i+1} completed"})
                await session.execute(text("""
                    INSERT INTO public_records_audit_logs (request_id, action,
                        performed_by_id, details, created_at)
                    VALUES (:req_id, :action, :staff, cast(:details as json), :created)
                """), {
                    "req_id": pid,
                    "action": actions_sequence[i],
                    "staff": random.choice(staff_ids),
                    "details": details,
                    "created": _past(random.randint(1, 30)),
                })
                count += 1
        print(f"    Created {count} public records audit log entries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 23. DATA RETENTION POLICIES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM data_retention_policies"))
    if r.scalar() == 0:
        print("  Seeding data_retention_policies...")
        ret_policies = [
            ("Patron Circulation Records", "Borrowing history, checkout/return dates, and hold requests.", "circulation_records", 3, "Automated database purge", True, False),
            ("Patron Account Information", "Name, contact info, library card number, and account status.", "patron_accounts", 5, "Manual review then secure deletion", True, False),
            ("Internet Use Logs", "Public computer session logs, WiFi connection records.", "internet_logs", 1, "Automated log rotation and deletion", False, False),
            ("Financial Transaction Records", "Fine payments, fee collections, and donation records.", "financial_records", 7, "Archived then securely shredded", True, True),
            ("Staff Employment Records", "Personnel files, evaluations, and training records.", "employment_records", 7, "Secure shredding after retention period", True, True),
            ("Security Camera Footage", "Video surveillance recordings from all branches.", "security_footage", 0, "Automatic overwrite after 30 days", False, False),
        ]
        for name, desc, dtype, years, method, legal_hold, union_exc in ret_policies:
            await session.execute(text("""
                INSERT INTO data_retention_policies (name, description, data_type,
                    retention_years, deletion_method, has_legal_hold_exception,
                    has_union_agreement_exception, created_by_id, is_active, effective_date)
                VALUES (:name, :desc, :dtype,
                    :years, :method, :legal_hold,
                    :union_exc, :creator, true, :eff)
            """), {
                "name": name, "desc": desc, "dtype": dtype,
                "years": years, "method": method, "legal_hold": legal_hold,
                "union_exc": union_exc, "creator": random.choice(staff_ids),
                "eff": _past(365),
            })
        print(f"    Created {len(ret_policies)} data retention policies")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 24. DATA SHARING LOGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM data_sharing_logs"))
    if r.scalar() == 0:
        print("  Seeding data_sharing_logs...")
        sharing_logs = [
            ("State Interlibrary Loan Network", "library_consortium", "interlibrary_loan", "Patron name and card number for ILL fulfillment.", "ILL protocol agreement", True),
            ("Payment Processing (Stripe)", "payment_processor", "payment_processing", "Card payment for fine/fee collection.", "PCI compliance agreement", True),
            ("Email Service (Resend)", "email_provider", "email_delivery", "Patron email for hold notifications.", "Data processing agreement", False),
            ("SMS Provider", "sms_provider", "sms_delivery", "Patron phone for text notifications.", "Data processing agreement", False),
            ("Collection Agency (ABC Collections)", "collection_agency", "collection_agency", "Patron name and amount owed for accounts over $25.", "Collection agreement", True),
            ("State Library Annual Report", "state_agency", "analytics", "Aggregated, anonymized circulation and usage statistics.", "State reporting requirement", False),
            ("Insurance Provider (after incident)", "insurance_company", "insurance_claim", "Incident details for property damage claim.", "Insurance policy terms", True),
            ("Consortium Analytics Dashboard", "library_consortium", "consortium_sharing", "Anonymized collection and usage metrics.", "Consortium data sharing MOU", False),
            ("Legal compliance reporting", "regulatory_body", "legal_compliance", "Required data for state compliance audit.", "State library law", True),
        ]
        for recipient, rtype, purpose, notes, legal_basis, notified in sharing_logs:
            categories = json.dumps(["patron_data"] if "patron" in notes.lower() else ["operational_data"])
            await session.execute(text("""
                INSERT INTO data_sharing_logs (user_id, recipient_name, recipient_type,
                    purpose, data_categories, legal_basis,
                    patron_notified, shared_by_staff_id, notes, created_at)
                VALUES (:uid, :recipient, :rtype,
                    :purpose, cast(:cats as json), :legal,
                    :notified, :staff, :notes, :created)
            """), {
                "uid": random.choice(patron_ids) if notified else None,
                "recipient": recipient, "rtype": rtype,
                "purpose": purpose, "cats": categories,
                "legal": legal_basis,
                "notified": notified,
                "staff": random.choice(staff_ids),
                "notes": notes,
                "created": _past(random.randint(5, 180)),
            })
        print(f"    Created {len(sharing_logs)} data sharing log entries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 25. STATE LIBRARY REQUIREMENTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM state_library_requirements"))
    if r.scalar() == 0:
        print("  Seeding state_library_requirements...")
        state_reqs = [
            ("IL", "Annual Statistical Report", "Submit annual report of library statistics to the Illinois State Library.",
             "23 Ill. Admin. Code 3030", "compliant", True, 8),
            ("IL", "Open Meetings Act Compliance", "All board meetings must comply with Illinois Open Meetings Act.",
             "5 ILCS 120", "compliant", False, None),
            ("IL", "FOIA Compliance", "Respond to Freedom of Information requests within 5 business days.",
             "5 ILCS 140", "compliant", False, None),
            ("IL", "Minimum Hours of Operation", "Maintain minimum weekly hours as required for state certification.",
             "23 Ill. Admin. Code 3030.115", "compliant", False, None),
            ("IL", "Certified Librarian Requirement", "Employ at least one Illinois-certified librarian.",
             "23 Ill. Admin. Code 3030.110", "compliant", False, None),
            ("IL", "Per Capita Grant Requirements", "Meet all requirements for Illinois per capita grant eligibility.",
             "75 ILCS 10/8", "compliant", True, 6),
            ("IL", "Patron Privacy - Library Records Confidentiality Act", "Protect patron records per the Library Records Confidentiality Act.",
             "75 ILCS 70", "compliant", False, None),
            ("IL", "ADA Compliance", "Ensure facilities and services are accessible per ADA requirements.",
             "42 U.S.C. 12101", "partial_compliance", False, None),
        ]
        for state_code, name, desc, citation, status, report_req, report_month in state_reqs:
            annual_due = date(2026, report_month, 15) if report_month else None
            await session.execute(text("""
                INSERT INTO state_library_requirements (organization_id, state_code,
                    requirement_name, requirement_description, regulation_citation,
                    status, last_verified_date, next_verification_due,
                    annual_report_required, annual_report_due_date, annual_report_submitted,
                    responsible_person_id)
                VALUES (:org, :state,
                    :name, :desc, :citation,
                    :status, :last_ver, :next_ver,
                    :report_req, :due_date, :submitted,
                    :person)
            """), {
                "org": ORG_ID, "state": state_code,
                "name": name, "desc": desc, "citation": citation,
                "status": status,
                "last_ver": _past_date(random.randint(30, 180)),
                "next_ver": _future_date(random.randint(90, 365)),
                "report_req": report_req,
                "due_date": annual_due,
                "submitted": report_req and random.choice([True, False]),
                "person": random.choice(staff_ids),
            })
        print(f"    Created {len(state_reqs)} state library requirements")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 26. STATE REPORT TEMPLATES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM state_report_templates"))
    if r.scalar() == 0:
        print("  Seeding state_report_templates...")
        templates = [
            ("IL", "Illinois Public Library Annual Report (IPLAR)", "Annual statistical and financial report for the Illinois State Library.",
             {"total_checkouts": "circulation.total_checkouts", "total_patrons": "patrons.active_count"},
             "CSV", "https://ilsos.gov/library/reporting", "2026.1"),
            ("IL", "Per Capita Grant Application", "Application for Illinois per capita state aid grant.",
             {"population_served": "demographics.population", "hours_open": "operations.weekly_hours"},
             "PDF", "https://ilsos.gov/library/grants", "FY2026"),
            ("IL", "E-Rate CIPA Certification", "Federal E-Rate program CIPA compliance certification.",
             {"filter_active": "cipa.filter_status", "policy_posted": "cipa.policy_status"},
             "PDF", "https://www.usac.org/e-rate/", "2026"),
        ]
        for state_code, name, desc, field_map, fmt, url, version in templates:
            required = json.dumps(["library_name", "fiscal_year", "population_served"])
            calculated = json.dumps(["per_capita_expenditure", "turnover_rate"])
            await session.execute(text("""
                INSERT INTO state_report_templates (state_code, template_name, template_description,
                    field_mappings, required_fields, calculated_fields,
                    output_format, submission_portal_url, is_active, version)
                VALUES (:state, :name, :desc,
                    cast(:fields as json), cast(:required as json), cast(:calc as json),
                    :fmt, :url, true, :ver)
            """), {
                "state": state_code, "name": name, "desc": desc,
                "fields": json.dumps(field_map), "required": required, "calc": calculated,
                "fmt": fmt, "url": url, "ver": version,
            })
        print(f"    Created {len(templates)} state report templates")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 27. STATE CONFIDENTIALITY EXCEPTIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM state_confidentiality_exceptions"))
    if r.scalar() == 0:
        print("  Seeding state_confidentiality_exceptions...")
        exceptions = [
            ("IL", "Court Order / Subpoena", "Patron records may be disclosed pursuant to a valid court order or subpoena.",
             "law_enforcement", "circulation_records", False, False, "75 ILCS 70/1"),
            ("IL", "Child Abuse Reporting", "Mandatory reporting exception when there is reasonable cause to believe a child is being abused or neglected.",
             "child_protective_services", "patron_records", True, True, "325 ILCS 5"),
            ("IL", "Imminent Threat to Safety", "Exception for situations involving imminent threat to the life or safety of an individual.",
             "law_enforcement", "patron_records", True, False, "75 ILCS 70/1"),
        ]
        for state_code, name, desc, agency, record_type, emergency, minor, statute in exceptions:
            await session.execute(text("""
                INSERT INTO state_confidentiality_exceptions (state_code, exception_name,
                    exception_description, applies_to_agency_type, applies_to_record_type,
                    requires_emergency, requires_minor_involved, statute_reference, is_active)
                VALUES (:state, :name, :desc, :agency, :record_type,
                    :emergency, :minor, :statute, true)
            """), {
                "state": state_code, "name": name, "desc": desc,
                "agency": agency, "record_type": record_type,
                "emergency": emergency, "minor": minor, "statute": statute,
            })
        print(f"    Created {len(exceptions)} state confidentiality exceptions")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 28. REGULATION MONITORS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM regulation_monitors"))
    if r.scalar() == 0:
        print("  Seeding regulation_monitors...")
        monitors = [
            ("Illinois Library Records Confidentiality Act", "75-ILCS-70", "STATE_LIBRARY", "IL",
             "EFFECTIVE", "Protects the privacy of library patron records in Illinois.",
             True, False, False, False, False, False, "high"),
            ("Children Internet Protection Act (CIPA)", "47-USC-254", "FEDERAL", None,
             "EFFECTIVE", "Requires internet filtering on computers accessible by minors in libraries receiving E-Rate.",
             True, False, False, False, True, False, "high"),
            ("Illinois Freedom of Information Act", "5-ILCS-140", "STATE_LEGISLATURE", "IL",
             "EFFECTIVE", "Governs public access to government records including library records.",
             False, False, False, False, True, False, "medium"),
            ("Proposed Digital Privacy Enhancement Act", "HB-2847", "STATE_LEGISLATURE", "IL",
             "PROPOSED", "Would expand patron privacy protections to include digital service usage data.",
             True, True, False, False, False, False, "high"),
        ]
        for name, reg_num, source, jurisdiction_code, status, summary, privacy, retention, law_enf, access, reporting, registration, priority in monitors:
            await session.execute(text("""
                INSERT INTO regulation_monitors (regulation_name, regulation_number,
                    jurisdiction_type, jurisdiction_code, source, status,
                    summary, affects_patron_privacy, affects_data_retention,
                    affects_law_enforcement, affects_accessibility, affects_reporting,
                    affects_registration, priority, requires_action, reviewed, is_active)
                VALUES (:name, :reg_num,
                    :jtype, :jcode, :source, :status,
                    :summary, :privacy, :retention,
                    :law_enf, :access, :reporting,
                    :registration, :priority, :req_action, :reviewed, true)
            """), {
                "name": name, "reg_num": reg_num,
                "jtype": "state" if source in ("STATE_LIBRARY", "STATE_LEGISLATURE") else "federal",
                "jcode": jurisdiction_code, "source": source, "status": status,
                "summary": summary, "privacy": privacy, "retention": retention,
                "law_enf": law_enf, "access": access, "reporting": reporting,
                "registration": registration, "priority": priority,
                "req_action": status == "PROPOSED",
                "reviewed": status == "EFFECTIVE",
            })
        print(f"    Created {len(monitors)} regulation monitors")
        await session.commit()

    # Fetch regulation_monitor IDs
    rm_r = await session.execute(text("SELECT id FROM regulation_monitors ORDER BY id"))
    rm_ids = [r[0] for r in rm_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 29. REGULATION ALERTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM regulation_alerts"))
    if r.scalar() == 0 and rm_ids:
        print("  Seeding regulation_alerts...")
        reg_alerts = [
            ("new_regulation", "New Digital Privacy Bill Introduced", "HB-2847 introduced in state legislature affecting library patron digital privacy.", "high", False),
            ("amendment_proposed", "CIPA Amendment Under Discussion", "Federal advisory committee discussing potential updates to CIPA filtering requirements.", "medium", False),
            ("compliance_deadline", "Annual State Report Filing Deadline", "Illinois Public Library Annual Report due August 15, 2026.", "high", True),
            ("review_needed", "Library Records Act Case Law Update", "New court decision may affect interpretation of patron privacy protections.", "medium", False),
            ("training_required", "Updated FOIA Procedures Effective", "New FOIA response timeline requirements take effect next quarter.", "low", True),
        ]
        for atype, title, desc, priority, resolved in reg_alerts:
            await session.execute(text("""
                INSERT INTO regulation_alerts (regulation_monitor_id, alert_type,
                    title, description, priority,
                    assigned_to_id, is_resolved, notification_sent)
                VALUES (:rm_id, :atype,
                    :title, :desc, :priority,
                    :assigned, :resolved, true)
            """), {
                "rm_id": random.choice(rm_ids), "atype": atype,
                "title": title, "desc": desc, "priority": priority,
                "assigned": random.choice(staff_ids),
                "resolved": resolved,
            })
        print(f"    Created {len(reg_alerts)} regulation alerts")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 30. REGULATORY CHANGES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM regulatory_changes"))
    if r.scalar() == 0:
        print("  Seeding regulatory_changes...")
        reg_changes = [
            ("Updated State Library Annual Report Requirements", "amendment",
             "Illinois State Library updated the required fields for the annual statistical report, adding digital service metrics.",
             "23 Ill. Admin. Code 3030", "Illinois", "Illinois State Library", 120, 180, "medium"),
            ("CIPA Filtering Technology Update Guidance", "interpretation",
             "FCC issued updated guidance on acceptable content filtering technologies for CIPA compliance.",
             "47 USC 254(h)", "Federal", "Federal Communications Commission", 90, 365, "low"),
            ("Patron Data Breach Notification Amendment", "new_regulation",
             "New state law requiring libraries to notify patrons within 30 days of a data breach affecting personal information.",
             "HB-3456", "Illinois", "Illinois General Assembly", 60, 120, "high"),
            ("E-Rate Modernization Updates", "amendment",
             "USAC updated E-Rate eligible services list and application procedures for FY2026.",
             "47 CFR 54", "Federal", "USAC/FCC", 180, 365, "medium"),
        ]
        for title, ctype, desc, citation, jurisdiction, authority, announce_days, deadline_days, impact in reg_changes:
            req_actions = json.dumps(["Review changes", "Update internal procedures", "Train affected staff"])
            await session.execute(text("""
                INSERT INTO regulatory_changes (title, change_type, description,
                    legal_citation, jurisdiction, issuing_authority,
                    announcement_date, effective_date, compliance_deadline,
                    impact_level, affected_departments,
                    required_actions, is_reviewed, created_by_id)
                VALUES (:title, :ctype, :desc,
                    :citation, :jurisdiction, :authority,
                    :announced, :effective, :deadline,
                    :impact, '{"Administration","IT"}'::varchar[],
                    cast(:actions as jsonb), :reviewed, :creator)
            """), {
                "title": title, "ctype": ctype, "desc": desc,
                "citation": citation, "jurisdiction": jurisdiction, "authority": authority,
                "announced": _past_date(announce_days),
                "effective": _future_date(deadline_days - announce_days) if deadline_days > announce_days else _past_date(announce_days - deadline_days),
                "deadline": _future_date(deadline_days),
                "impact": impact, "actions": req_actions,
                "reviewed": random.choice([True, False]),
                "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(reg_changes)} regulatory changes")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 31. INSURANCE POLICIES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM insurance_policies"))
    if r.scalar() == 0:
        print("  Seeding insurance_policies...")
        ins_policies = [
            ("general_liability", "General Liability Insurance", "GL-2024-5567",
             "Municipal Insurance Alliance", 2000000.00, 5000.00, True, "Johnson Insurance Group"),
            ("property_insurance", "Property and Contents Insurance", "PROP-2024-8821",
             "Library Mutual Insurance", 5000000.00, 10000.00, True, "Johnson Insurance Group"),
            ("cyber_liability", "Cyber Liability and Data Breach Insurance", "CYBER-2024-3344",
             "TechGuard Insurance Co.", 1000000.00, 2500.00, True, "Smith and Associates"),
            ("directors_officers", "Directors and Officers Liability", "DO-2024-9012",
             "Board Protection Insurance", 1000000.00, 5000.00, True, "Johnson Insurance Group"),
        ]
        for ptype, name, policy_num, provider, coverage, deductible, auto_renew, broker in ins_policies:
            eff = date(2024, 7, 1)
            exp = date(2025, 6, 30)
            await session.execute(text("""
                INSERT INTO insurance_policies (organization_id, policy_type, policy_name,
                    policy_number, provider_name, coverage_amount, deductible,
                    effective_date, expiration_date, renewal_reminder_days_before,
                    auto_renews, renewal_pending, claims_filed,
                    broker_name, notes)
                VALUES (:org, :ptype, :name,
                    :pol_num, :provider, :coverage, :deductible,
                    :eff, :exp, 60,
                    :auto_renew, false, 0,
                    :broker, 'Current policy in good standing.')
            """), {
                "org": ORG_ID, "ptype": ptype, "name": name,
                "pol_num": policy_num, "provider": provider,
                "coverage": coverage, "deductible": deductible,
                "eff": eff, "exp": exp,
                "auto_renew": auto_renew, "broker": broker,
            })
        print(f"    Created {len(ins_policies)} insurance policies")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 32. INSURANCE DOCUMENTATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM insurance_documentations"))
    if r.scalar() == 0:
        print("  Seeding insurance_documentations...")
        ins_docs = [
            (180, "water_damage", "Water damage to children area carpet from roof leak during storm.",
             "Main Branch - Children Area", "Library Mutual Insurance", "Janet Wilson",
             "(555) 888-1234", "janet@librarymutual.com", 4500.00, 4200.00, 4200.00, 3800.00, 3800.00),
            (90, "equipment_damage", "Public computer damaged by power surge during electrical storm.",
             "East Branch - Computer Lab", "TechGuard Insurance Co.", "Mark Stevens",
             "(555) 888-5678", "mark@techguard.com", 2200.00, 2100.00, 2100.00, None, None),
        ]
        for days_ago, itype, desc, location, company, agent, phone, email, initial, final_amt, claimed, approved, reimbursed in ins_docs:
            await session.execute(text("""
                INSERT INTO insurance_documentations (incident_date, incident_type,
                    incident_description, incident_location,
                    insurance_company, agent_name, agent_phone, agent_email,
                    initial_damage_estimate, final_damage_amount, claimed_amount,
                    approved_amount, reimbursed_amount,
                    documentation_complete, claim_submitted, claim_approved,
                    has_incident_report, has_photos, assigned_to_id)
                VALUES (:inc_date, :itype,
                    :desc, :loc,
                    :company, :agent, :phone, :email,
                    :initial, :final_amt, :claimed,
                    :approved, :reimbursed,
                    true, true, :claim_approved,
                    true, true, :assigned)
            """), {
                "inc_date": _past(days_ago), "itype": itype,
                "desc": desc, "loc": location,
                "company": company, "agent": agent, "phone": phone, "email": email,
                "initial": initial, "final_amt": final_amt, "claimed": claimed,
                "approved": approved, "reimbursed": reimbursed,
                "claim_approved": approved is not None,
                "assigned": random.choice(staff_ids),
            })
        print(f"    Created {len(ins_docs)} insurance documentation records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 33. LAW ENFORCEMENT RESPONSE TEMPLATES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM law_enforcement_response_templates"))
    if r.scalar() == 0:
        print("  Seeding law_enforcement_response_templates...")
        le_templates = [
            ("Subpoena Acknowledgment", "Standard acknowledgment letter for received subpoenas.", "subpoena_response",
             "RE: Subpoena [TRACKING_NUMBER]",
             "Dear [AGENCY_CONTACT],\n\nThis letter acknowledges receipt of the subpoena dated [DATE_RECEIVED]. We are reviewing the request with our legal counsel and will respond within the required timeframe.\n\nSincerely,\n[LIBRARY_DIRECTOR]"),
            ("Request Rejection - Insufficient Legal Process", "Template for rejecting informal requests without proper legal process.", "rejection",
             "RE: Information Request [TRACKING_NUMBER]",
             "Dear [AGENCY_CONTACT],\n\nUnder the Library Records Confidentiality Act, patron records are confidential and may only be disclosed pursuant to a valid court order or subpoena.\n\nWe are unable to provide the requested information based on an informal request.\n\nSincerely,\n[LIBRARY_DIRECTOR]"),
            ("Compliance Response", "Template for providing records in compliance with valid legal process.", "compliance_response",
             "RE: Response to [REQUEST_TYPE] [TRACKING_NUMBER]",
             "Dear [AGENCY_CONTACT],\n\nIn response to the [REQUEST_TYPE] dated [DATE_RECEIVED], please find enclosed the requested records, limited to the scope specified in the order.\n\nSincerely,\n[LIBRARY_DIRECTOR]"),
        ]
        applicable_types = json.dumps(["SUBPOENA", "WARRANT", "COURT_ORDER"])
        for name, desc, ttype, subject, body in le_templates:
            await session.execute(text("""
                INSERT INTO law_enforcement_response_templates (name, description, template_type,
                    applicable_request_types, subject_template, body_template,
                    is_active, created_by_id)
                VALUES (:name, :desc, :ttype,
                    cast(:types as json), :subject, :body,
                    true, :creator)
            """), {
                "name": name, "desc": desc, "ttype": ttype,
                "types": applicable_types, "subject": subject, "body": body,
                "creator": random.choice(staff_ids),
            })
        print(f"    Created {len(le_templates)} law enforcement response templates")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 34. LAW ENFORCEMENT REQUESTS (redacted samples)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM law_enforcement_requests"))
    if r.scalar() == 0:
        print("  Seeding law_enforcement_requests...")
        le_requests = [
            ("LE-2025-001", "Springfield Police Department", "SUBPOENA", 180,
             "Records of computer use sessions for a specific date range.",
             "approved", "completed", True, True),
            ("LE-2026-001", "County Sheriff Office", "COURT_ORDER", 30,
             "Patron account information associated with a specific library card number.",
             "under_review", "LEGAL_REVIEW", False, False),
        ]
        for tracking, agency, rtype, days_ago, data_req, legal_status, workflow, notif_permitted, responded in le_requests:
            received = _past(days_ago)
            await session.execute(text("""
                INSERT INTO law_enforcement_requests (tracking_number, requesting_agency,
                    request_type, date_received, data_requested,
                    legal_review_status, workflow_status,
                    patron_notification_permitted,
                    created_by_id, legal_reviewer_id)
                VALUES (:tracking, :agency,
                    :rtype, :received, :data_req,
                    :legal_status, :workflow,
                    :notif_permitted,
                    :creator, :reviewer)
            """), {
                "tracking": tracking, "agency": agency,
                "rtype": rtype, "received": received, "data_req": data_req,
                "legal_status": legal_status, "workflow": workflow,
                "notif_permitted": notif_permitted,
                "creator": random.choice(staff_ids),
                "reviewer": random.choice(staff_ids),
            })
        print(f"    Created {len(le_requests)} law enforcement requests")
        await session.commit()

    # Fetch law enforcement request IDs
    le_r = await session.execute(text("SELECT id FROM law_enforcement_requests ORDER BY id"))
    le_ids = [r[0] for r in le_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 35. LAW ENFORCEMENT CHECKLISTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM law_enforcement_checklists"))
    if r.scalar() == 0 and le_ids:
        print("  Seeding law_enforcement_checklists...")
        checklist_items = [
            ("RECEIVE_REQUEST", "Log receipt of request with date, time, and delivery method.", True, True, 1),
            ("VERIFY_VALIDITY", "Verify the legal document is valid and properly issued.", True, True, 2),
            ("VERIFY_JURISDICTION", "Confirm the issuing court has jurisdiction.", True, True, 3),
            ("VERIFY_SCOPE", "Review scope of request - ensure it is specific and not overbroad.", True, True, 4),
            ("LEGAL_REVIEW", "Forward to legal counsel for review and approval.", True, True, 5),
            ("DIRECTOR_APPROVAL", "Obtain Library Director approval before responding.", True, True, 6),
            ("NOTIFY_PATRON", "Notify patron if permitted and not under gag order.", False, True, 7),
            ("PREPARE_RESPONSE", "Prepare response with minimum necessary information.", True, True, 8),
            ("MINIMIZE_DATA", "Ensure only requested data is included - nothing extraneous.", True, True, 9),
            ("DOCUMENT_COMPLIANCE", "Document all actions taken for the audit trail.", True, True, 10),
            ("SEND_RESPONSE", "Send response via secure method to requesting agency.", True, True, 11),
            ("FINAL_REVIEW", "Complete final review and close the request.", True, True, 12),
        ]
        count = 0
        for le_id in le_ids:
            for itype, desc, required, applicable, sort_order in checklist_items:
                completed = sort_order <= 6 if le_id == le_ids[0] else sort_order <= 4
                await session.execute(text("""
                    INSERT INTO law_enforcement_checklists (request_id, item_type,
                        item_description, is_completed, is_required, is_applicable,
                        completed_by_id, completed_at, sort_order)
                    VALUES (:req_id, :itype,
                        :desc, :completed, :required, :applicable,
                        :comp_by, :comp_at, :sort_order)
                """), {
                    "req_id": le_id, "itype": itype,
                    "desc": desc, "completed": completed,
                    "required": required, "applicable": applicable,
                    "comp_by": random.choice(staff_ids) if completed else None,
                    "comp_at": _past(random.randint(1, 30)) if completed else None,
                    "sort_order": sort_order,
                })
                count += 1
        print(f"    Created {count} law enforcement checklist items")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 36. LAW ENFORCEMENT AUDIT LOGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM law_enforcement_audit_logs"))
    if r.scalar() == 0 and le_ids:
        print("  Seeding law_enforcement_audit_logs...")
        count = 0
        le_actions = ["REQUEST_CREATED", "STATUS_CHANGED", "LEGAL_REVIEW_UPDATED", "CHECKLIST_UPDATED"]
        for le_id in le_ids:
            for action in le_actions:
                details = json.dumps({"action": action, "notes": "Automated audit log entry."})
                await session.execute(text("""
                    INSERT INTO law_enforcement_audit_logs (request_id, action,
                        performed_by_id, details, created_at)
                    VALUES (:req_id, :action, :staff, cast(:details as json), :created)
                """), {
                    "req_id": le_id, "action": action,
                    "staff": random.choice(staff_ids),
                    "details": details,
                    "created": _past(random.randint(1, 60)),
                })
                count += 1
        print(f"    Created {count} law enforcement audit log entries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 37. ANNUAL REPORTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM annual_reports"))
    if r.scalar() == 0:
        print("  Seeding annual_reports...")
        annual_data = [
            (2024, "submitted", True, 125000, 8500, 2100, 45000, 3500, 850, 92, 180, 4500,
             1800000, 1750000, 12.5, 4.2, 56),
            (2025, "draft", False, 132000, 9200, 2400, 47000, 3800, 920, 98, 195, 4800,
             1950000, 1900000, 13.0, 4.5, 58),
            (2023, "submitted", True, 118000, 7800, 1900, 43000, 3200, 780, 88, 165, 4200,
             1700000, 1650000, 12.0, 4.0, 54),
        ]
        checkouts_by_type = json.dumps({"books": 65000, "dvds": 15000, "audiobooks": 8000, "ebooks": 12000, "magazines": 5000})
        patrons_by_age = json.dumps({"0-12": 2500, "13-17": 1800, "18-34": 3500, "35-54": 4200, "55-64": 2800, "65+": 2200})
        items_by_format = json.dumps({"print_books": 85000, "dvds": 12000, "audiobooks": 5000, "ebooks": 25000, "periodicals": 3000})
        programs_by_audience = json.dumps({"children": 120, "young_adult": 45, "adult": 80, "all_ages": 25})
        revenue_by_source = json.dumps({"property_tax": 1500000, "state_aid": 150000, "fines_fees": 25000, "donations": 50000, "grants": 75000})
        expenditure_by_cat = json.dumps({"personnel": 1100000, "collections": 250000, "technology": 150000, "facilities": 200000, "other": 50000})

        for fy, status, validated, checkouts, renewals, returns, holds_placed, holds_filled, ill_loaned, ill_borrowed, programs, attendance, revenue, expenditure, staff_fte, librarian_fte, hours_per_week in annual_data:
            await session.execute(text("""
                INSERT INTO annual_reports (fiscal_year, state_code, library_name, library_type,
                    status, is_validated,
                    total_checkouts, total_renewals, total_returns,
                    checkouts_by_item_type,
                    total_holds_placed, total_holds_filled,
                    items_loaned_to_other_libraries, items_borrowed_from_other_libraries,
                    total_registered_patrons, active_patrons, new_patrons_registered,
                    patrons_by_age_group,
                    total_items_owned, items_by_format,
                    total_programs_offered, total_program_attendance,
                    programs_by_audience,
                    total_hours_open_per_week, number_of_locations,
                    total_operating_revenue, total_operating_expenditure,
                    revenue_by_source, expenditure_by_category,
                    total_staff_fte, librarian_fte,
                    legal_service_area_population,
                    generated_by_id, last_modified_by_id)
                VALUES (:fy, 'IL', 'L30 Public Library', 'municipal',
                    :status, :validated,
                    :checkouts, :renewals, :returns,
                    cast(:checkouts_type as jsonb),
                    :holds_placed, :holds_filled,
                    :ill_loaned, :ill_borrowed,
                    17000, :active, :new_patrons,
                    cast(:patrons_age as jsonb),
                    130000, cast(:items_fmt as jsonb),
                    :programs, :attendance,
                    cast(:progs_audience as jsonb),
                    :hours, 4,
                    :revenue, :expenditure,
                    cast(:rev_source as jsonb), cast(:exp_cat as jsonb),
                    :staff_fte, :lib_fte,
                    45000,
                    :gen_by, :mod_by)
            """), {
                "fy": fy, "status": status, "validated": validated,
                "checkouts": checkouts, "renewals": renewals, "returns": returns,
                "checkouts_type": checkouts_by_type,
                "holds_placed": holds_placed, "holds_filled": holds_filled,
                "ill_loaned": ill_loaned, "ill_borrowed": ill_borrowed,
                "active": int(checkouts * 0.35), "new_patrons": random.randint(800, 1500),
                "patrons_age": patrons_by_age,
                "items_fmt": items_by_format,
                "programs": programs, "attendance": attendance,
                "progs_audience": programs_by_audience,
                "hours": hours_per_week,
                "revenue": revenue, "expenditure": expenditure,
                "rev_source": revenue_by_source, "exp_cat": expenditure_by_cat,
                "staff_fte": staff_fte, "lib_fte": librarian_fte,
                "gen_by": random.choice(staff_ids),
                "mod_by": random.choice(staff_ids),
            })
        print(f"    Created {len(annual_data)} annual reports")
        await session.commit()

    # Fetch annual report IDs
    ar_r = await session.execute(text("SELECT id FROM annual_reports ORDER BY id"))
    ar_ids = [r[0] for r in ar_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 38. ANNUAL REPORT HISTORY
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM annual_report_history"))
    if r.scalar() == 0 and ar_ids:
        print("  Seeding annual_report_history...")
        history_entries = [
            ("total_checkouts", "124500", "125000", "Corrected after reconciling branch reports."),
            ("total_programs_offered", "175", "180", "Added 5 outreach programs that were miscategorized."),
            ("status", "draft", "submitted", "Report submitted to Illinois State Library."),
            ("total_registered_patrons", "16800", "17000", "Updated after database cleanup removed duplicates."),
        ]
        count = 0
        for ar_id in ar_ids[:2]:
            for field, old, new, reason in history_entries:
                await session.execute(text("""
                    INSERT INTO annual_report_history (annual_report_id, field_name,
                        old_value, new_value, change_reason, changed_by_id, changed_at)
                    VALUES (:ar_id, :field, :old, :new, :reason, :changed_by, :changed_at)
                """), {
                    "ar_id": ar_id, "field": field, "old": old, "new": new,
                    "reason": reason, "changed_by": random.choice(staff_ids),
                    "changed_at": _past(random.randint(5, 60)),
                })
                count += 1
        print(f"    Created {count} annual report history entries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 39. ANNUAL REPORT VALIDATION RULES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM annual_report_validation_rules"))
    if r.scalar() == 0:
        print("  Seeding annual_report_validation_rules...")
        rules = [
            ("IL", "total_checkouts", "required", "Total checkouts is required.", None),
            ("IL", "total_checkouts", "min_value", "Total checkouts must be non-negative.", "0"),
            ("IL", "total_registered_patrons", "required", "Total registered patrons is required.", None),
            ("IL", "total_operating_revenue", "required", "Total operating revenue is required.", None),
            ("IL", "total_operating_expenditure", "required", "Total operating expenditure is required.", None),
            ("IL", "fiscal_year", "range", "Fiscal year must be between 2000 and 2030.", "2000-2030"),
            (None, "total_items_owned", "min_value", "Total items owned must be non-negative.", "0"),
        ]
        for state_code, field, rtype, error_msg, rule_val in rules:
            await session.execute(text("""
                INSERT INTO annual_report_validation_rules (state_code, field_name, rule_type,
                    description, rule_value, error_message, is_active)
                VALUES (:state, :field, :rtype, :desc, :rule_val, :error, true)
            """), {
                "state": state_code, "field": field, "rtype": rtype,
                "desc": error_msg, "rule_val": rule_val, "error": error_msg,
            })
        print(f"    Created {len(rules)} annual report validation rules")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 40. STATISTICAL REPORTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM statistical_reports"))
    if r.scalar() == 0:
        print("  Seeding statistical_reports...")
        report_types = [
            ("Monthly Circulation Report", "circulation"),
            ("Monthly Program Attendance Report", "program_att"),
        ]
        count = 0
        for i in range(12):
            month_num = (i % 12) + 1
            month_start = date(2025, month_num, 1)
            if month_num == 12:
                month_end = date(2025, 12, 31)
            else:
                month_end = date(2025, month_num + 1, 1) - timedelta(days=1)
            for rname, rtype in report_types:
                branch = random.choice(branch_names) if branch_names else "Main Branch"
                params = json.dumps({"branch": branch, "include_renewals": True})
                stats = json.dumps({"total": random.randint(5000, 15000), "daily_avg": random.randint(200, 500)})
                await session.execute(text("""
                    INSERT INTO statistical_reports (report_name, report_type, period_start, period_end,
                        fiscal_year, branch_location, includes_all_branches,
                        report_parameters, included_statistics,
                        status, generated_by_id, generated_at, download_count)
                    VALUES (:name, :rtype, :ps, :pe,
                        2025, :branch, false,
                        cast(:params as jsonb), cast(:stats as jsonb),
                        'completed', :gen_by, :gen_at, :downloads)
                """), {
                    "name": f"{rname} - {month_start.strftime('%B %Y')}",
                    "rtype": rtype, "ps": month_start, "pe": month_end,
                    "branch": branch, "params": params, "stats": stats,
                    "gen_by": random.choice(staff_ids),
                    "gen_at": _past(random.randint(1, 365)),
                    "downloads": random.randint(0, 10),
                })
                count += 1
        print(f"    Created {count} statistical reports")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 41. REFERENCE STATISTICS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM reference_statistics"))
    if r.scalar() == 0:
        print("  Seeding reference_statistics...")
        count = 0
        for i in range(12):
            month_num = (i % 12) + 1
            month_start = date(2025, month_num, 1)
            if month_num == 12:
                month_end = date(2025, 12, 31)
            else:
                month_end = date(2025, month_num + 1, 1) - timedelta(days=1)
            branch = random.choice(branch_names) if branch_names else "Main Branch"
            total_q = random.randint(200, 600)
            by_type = json.dumps({"directional": int(total_q * 0.3), "ready_reference": int(total_q * 0.25),
                                  "research": int(total_q * 0.2), "technology": int(total_q * 0.15),
                                  "reader_advisory": int(total_q * 0.1)})
            by_method = json.dumps({"in_person": int(total_q * 0.6), "phone": int(total_q * 0.2),
                                    "email": int(total_q * 0.1), "chat": int(total_q * 0.1)})
            by_patron = json.dumps({"adult": int(total_q * 0.5), "young_adult": int(total_q * 0.15),
                                    "child": int(total_q * 0.25), "other": int(total_q * 0.1)})
            by_subject = json.dumps({"general": int(total_q * 0.3), "science": int(total_q * 0.1),
                                     "history": int(total_q * 0.15), "literature": int(total_q * 0.1),
                                     "technology": int(total_q * 0.15), "local_history": int(total_q * 0.1),
                                     "government": int(total_q * 0.1)})
            referrals = random.randint(5, 30)
            await session.execute(text("""
                INSERT INTO reference_statistics (period_start, period_end, period_type,
                    branch_location, total_questions,
                    questions_by_type, questions_by_method,
                    questions_by_patron_type, questions_by_subject,
                    avg_duration_minutes, total_referrals, generated_by_id)
                VALUES (:ps, :pe, 'monthly',
                    :branch, :total,
                    cast(:by_type as jsonb), cast(:by_method as jsonb),
                    cast(:by_patron as jsonb), cast(:by_subject as jsonb),
                    :avg_dur, :referrals, :gen_by)
            """), {
                "ps": month_start, "pe": month_end,
                "branch": branch, "total": total_q,
                "by_type": by_type, "by_method": by_method,
                "by_patron": by_patron, "by_subject": by_subject,
                "avg_dur": round(random.uniform(3.0, 12.0), 1),
                "referrals": referrals,
                "gen_by": random.choice(staff_ids),
            })
            count += 1
        print(f"    Created {count} reference statistics records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "legal_topics", "legal_glossary_terms", "legal_guides", "legal_documents",
        "legal_forms", "legal_service_providers", "legal_clinics", "legal_clinic_registrations",
        "compliance_reports", "compliance_alerts", "compliance_violations", "compliance_incidents",
        "compliance_checklist_items", "audit_readiness_checklists",
        "policy_reviews", "policy_change_log", "policy_feedback", "policy_enforcement_tracking",
        "cipa_compliance_reports", "cipa_compliance_tracking",
        "public_records_requests", "public_records_audit_logs",
        "data_retention_policies", "data_sharing_logs",
        "state_library_requirements", "state_report_templates", "state_confidentiality_exceptions",
        "regulation_monitors", "regulation_alerts", "regulatory_changes",
        "insurance_policies", "insurance_documentations",
        "law_enforcement_requests", "law_enforcement_checklists",
        "law_enforcement_response_templates", "law_enforcement_audit_logs",
        "annual_reports", "annual_report_history", "annual_report_validation_rules",
        "statistical_reports", "reference_statistics",
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
    print("  Compliance/legal/policy/governance seeding complete!")
    return True
