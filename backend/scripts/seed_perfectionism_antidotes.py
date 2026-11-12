#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for perfectionism antidotes

Populates the database with all 10 perfectionism antidotes.
Run: python scripts/seed_perfectionism_antidotes.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import PerfectionismAntidote, AntidoteType


def seed_antidotes():
    """Seed all perfectionism antidotes"""
    db = SessionLocal()

    antidotes_data = [
        {
            "antidote_type": AntidoteType.DONE_IS_BETTER,
            "title": "Done is Better Than Perfect",
            "reminder_text": "Imperfect action beats perfect inaction. Ship it!",
            "description": "A reminder that finished work, even if imperfect, is more valuable than endlessly perfecting something.",
            "advice": "Set a deadline and stick to it. Good enough today is better than perfect someday.",
            "example_scenario": "You finished a presentation that's 85% of what you wanted. Release it rather than spending 5 more hours.",
            "sort_order": 1,
            "icon_name": "check-circle",
            "color_code": "#10B981",  # Emerald
            "priority_score": 0.95
        },
        {
            "antidote_type": AntidoteType.TIME_LIMIT,
            "title": "Time Limits on Tasks",
            "reminder_text": "Use time boxing to prevent perfectionism spirals.",
            "description": "Set strict time limits on tasks to force prioritization and prevent infinite refinement.",
            "advice": "Use a timer. When time is up, move on. You can always improve it later.",
            "example_scenario": "Give yourself 30 minutes to write an email, not 2 hours.",
            "time_limit_minutes": 30,
            "sort_order": 2,
            "icon_name": "clock",
            "color_code": "#F59E0B",  # Amber
            "priority_score": 0.90
        },
        {
            "antidote_type": AntidoteType.MOVE_ON_PROMPT,
            "title": "Move On When Stuck",
            "reminder_text": "If you've been stuck 10 minutes, move on and come back.",
            "description": "Recognize when you're caught in a perfectionism loop and give yourself permission to move forward.",
            "advice": "Set a 10-minute rule: if you're stuck on something, move on. Fresh eyes help.",
            "example_scenario": "You're tweaking the same sentence for 15 minutes. Close the document and work on something else.",
            "sort_order": 3,
            "icon_name": "arrow-right",
            "color_code": "#EF4444",  # Red
            "priority_score": 0.85
        },
        {
            "antidote_type": AntidoteType.EIGHTY_TWENTY,
            "title": "80/20 Prioritization",
            "reminder_text": "80% of results come from 20% of effort. Focus there.",
            "description": "Identify the high-impact 20% of work that matters most and stop perfecting the rest.",
            "advice": "Ask: 'What's the 20% that creates 80% of the value?' Focus on that.",
            "example_scenario": "Instead of perfecting 30 slides, focus on making 3-4 key slides excellent.",
            "sort_order": 4,
            "icon_name": "trending-up",
            "color_code": "#3B82F6",  # Blue
            "priority_score": 0.92
        },
        {
            "antidote_type": AntidoteType.IMPERFECT_ACTION,
            "title": "Imperfect Action Over Inaction",
            "reminder_text": "An imperfect attempt is infinitely better than perfect planning.",
            "description": "Take messy action. You learn faster by doing than by planning.",
            "advice": "Start before you're ready. Iteration beats perfection.",
            "example_scenario": "Launch your side project now with 70% features instead of waiting for all 100.",
            "sort_order": 5,
            "icon_name": "rocket",
            "color_code": "#8B5CF6",  # Purple
            "priority_score": 0.88
        },
        {
            "antidote_type": AntidoteType.LEARN_ENOUGH,
            "title": "Learning From Good-Enough",
            "reminder_text": "You learn more from 'good enough' attempts than from perfect planning.",
            "description": "Imperfect attempts generate real feedback and learning that perfection never will.",
            "advice": "Share your work early. Get feedback. Iterate. This is how you improve.",
            "example_scenario": "Share a rough draft with a mentor. Their feedback is worth 10 hours of solo perfecting.",
            "sort_order": 6,
            "icon_name": "lightbulb",
            "color_code": "#FBBF24",  # Yellow
            "priority_score": 0.85
        },
        {
            "antidote_type": AntidoteType.CELEBRATE_PROGRESS,
            "title": "Celebrate Progress, Not Perfection",
            "reminder_text": "Notice and celebrate each win, no matter how small.",
            "description": "Acknowledge progress and incremental improvements instead of fixating on remaining imperfections.",
            "advice": "Keep a wins list. Each day, notice one thing you did well (even if imperfect).",
            "example_scenario": "You shipped something with bugs. Celebrate shipping. You'll fix bugs in v1.1.",
            "sort_order": 7,
            "icon_name": "star",
            "color_code": "#EC4899",  # Pink
            "priority_score": 0.90
        },
        {
            "antidote_type": AntidoteType.MANAGER_BALANCE,
            "title": "Manager Modeling Balance",
            "reminder_text": "Leaders, your team watches how you handle imperfection.",
            "description": "Managers who visibly embrace imperfection give permission to their teams to do the same.",
            "advice": "Share your work-in-progress. Admit mistakes. Show boundaries. This sets culture.",
            "example_scenario": "In a meeting, say 'I usually would spend 3 hours on this, but I'm giving myself 45 min to demo progress.'",
            "sort_order": 8,
            "icon_name": "users",
            "color_code": "#06B6D4",  # Cyan
            "priority_score": 0.88
        },
        {
            "antidote_type": AntidoteType.HUMAN_GRACE,
            "title": "Grace for Human Limitations",
            "reminder_text": "You're human. Humans have limits. That's OK.",
            "description": "Accept that finite time, energy, and attention are features, not bugs.",
            "advice": "When you hit limits, it's not failure. It's physics. Adjust accordingly.",
            "example_scenario": "You're tired. The work won't be perfect today. And that's fine. Rest matters.",
            "sort_order": 9,
            "icon_name": "heart",
            "color_code": "#F87171",  # Light Red
            "priority_score": 0.92
        },
        {
            "antidote_type": AntidoteType.PERMISSION_HUMAN,
            "title": "Permission to Be Human",
            "reminder_text": "You have permission to be imperfect, messy, and still worthy.",
            "description": "The most important antidote: explicit permission to be human with all the messiness that entails.",
            "advice": "Say it: 'I give myself permission to be human.' Repeat as needed.",
            "example_scenario": "You made a mistake. You're not a failure. You're human. That's enough.",
            "sort_order": 10,
            "icon_name": "smile",
            "color_code": "#A78BFA",  # Light Purple
            "priority_score": 1.0
        }
    ]

    try:
        for antidote_data in antidotes_data:
            # Check if already exists
            existing = db.query(PerfectionismAntidote).filter(
                PerfectionismAntidote.antidote_type == antidote_data["antidote_type"]
            ).first()

            if not existing:
                antidote = PerfectionismAntidote(**antidote_data)
                db.add(antidote)
                print(f"✓ Created: {antidote_data['title']}")
            else:
                print(f"⊘ Already exists: {antidote_data['title']}")

        db.commit()
        print("\n✓ Successfully seeded all perfectionism antidotes!")

    except Exception as e:
        db.rollback()
        print(f"✗ Error seeding antidotes: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_antidotes()
