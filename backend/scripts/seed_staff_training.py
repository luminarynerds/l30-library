#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for Library Essentials staff training course.
Creates a neurodivergent-friendly training curriculum for new staff.
"""

import asyncio
import os
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.learning import Course, Module, Lesson

# Database connection - read from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@localhost:5434/lsc_library")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_staff_training_course():
    """Create the Library Essentials staff training course."""
    
    async with async_session() as db:
        # Check if course already exists
        result = await db.execute(select(Course).where(Course.title == "Library Essentials"))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Course 'Library Essentials' already exists (id={existing.id}). Skipping.")
            return existing
        
        # Create the course
        course = Course(
            title="Library Essentials",
            description="A comprehensive introduction to working at Bébé Memorial Library. This course covers our values, daily operations, and patron service - all designed with neurodivergent-friendly practices in mind.",
            access_level="staff",
            is_published=True,
            estimated_minutes=90,
            difficulty="beginner",
            sensory_warning="This course contains text-based content only. No flashing images, auto-playing videos, or sudden sounds. Take breaks as needed.",
            xp_reward=250
        )
        db.add(course)
        await db.flush()
        
        # Module 1: Welcome to Bébé Memorial Library
        module1 = Module(
            course_id=course.id,
            title="Welcome to Bébé Memorial Library",
            description="Learn about our library's mission, values, and commitment to neurodivergent-friendly service.",
            sort_order=1
        )
        db.add(module1)
        await db.flush()
        
        # Module 1 Lessons
        lesson1_1 = Lesson(
            module_id=module1.id,
            title="Our Library Values",
            lesson_type="article",
            content={
                "markdown": """# Our Library Values

Welcome to the Bébé Memorial Library team. We are glad you are here.

## Our Core Values

### 1. Accessibility First
Every decision we make considers accessibility. This means:
- Clear signage with simple language
- Quiet spaces available for those who need them
- Multiple ways to access the same information
- Staff trained to offer accommodations without judgment

### 2. Patience is a Practice
We do not rush patrons. Everyone processes information differently, and that is okay.

**What this looks like:**
- Give people time to finish their thoughts
- Repeat information if asked, without frustration
- Offer written instructions alongside verbal ones
- Never assume someone "should" know something

### 3. Sensory Awareness
Our library considers sensory needs:
- Fluorescent lights have covers to reduce flickering
- We maintain quiet zones (marked with green signs)
- Headphones are available to borrow at the desk
- Strong scents are discouraged in shared spaces

### 4. Celebrating Different Minds
Neurodivergence is not a problem to solve - it is a valuable perspective we welcome.

## Your Role

As a staff member, you represent these values every day. You do not need to be perfect. You need to be:
- Willing to learn
- Open to feedback
- Kind to yourself and others

---

**Next Steps:** Continue to the next lesson to learn about neurodivergent-friendly service practices.
"""
            },
            estimated_minutes=10,
            sensory_notes="Text only. No images or multimedia. Calm, structured format with clear headings.",
            xp_reward=15,
            sort_order=1
        )
        db.add(lesson1_1)
        
        lesson1_2 = Lesson(
            module_id=module1.id,
            title="Neurodivergent-Friendly Service",
            lesson_type="article",
            content={
                "markdown": """# Neurodivergent-Friendly Service

This lesson provides practical guidance for serving all patrons well, with specific attention to neurodivergent needs.

## Understanding Neurodivergence

Neurodivergent is an umbrella term that includes:
- Autism
- ADHD
- Dyslexia
- Dyscalculia
- Dyspraxia
- Tourette syndrome
- And more

**Important:** You cannot always tell if someone is neurodivergent by looking at them. Assume everyone might benefit from accessible practices.

## Communication Best Practices

### Be Clear and Direct
- Say what you mean. Avoid idioms when possible.
- "The computers are near the back wall" is better than "head over thataway"
- If you use sarcasm, make it obvious

### Offer Choices, Not Open Questions
Instead of: "How can I help you?"
Try: "Are you looking for a book, a computer, or something else?"

### Give Processing Time
- Pause after speaking
- Do not fill silence immediately
- Let the patron respond at their pace

### Written Backup
- Offer to write down instructions
- Point to maps or signs when giving directions
- Have printed guides available for common tasks

## Sensory Considerations

### Noise
- Speak at a moderate volume
- Move to quieter areas for longer conversations if needed
- Be aware of background noise that might make hearing difficult

### Light
- Some patrons may wear sunglasses indoors - this is okay
- Point out areas with natural light vs fluorescent if asked

### Touch
- Never touch a patron without asking first
- This includes guiding someone by the elbow
- Ask: "Would you like me to show you, or would you prefer directions?"

## When Things Get Overwhelming

Signs a patron might be overwhelmed:
- Covering ears or eyes
- Rocking or pacing
- Short, clipped responses
- Looking around anxiously
- Asking to leave mid-transaction

**What to do:**
1. Lower your voice
2. Simplify what you are saying
3. Offer a quiet space if available
4. Say: "Take your time. No rush."
5. Offer to finish later: "I can put this on hold for you"

## Remember

You are not expected to diagnose anyone or be a therapist. Your job is to:
- Be kind
- Be patient
- Be flexible

That is enough.

---

**Checkpoint:** You have completed Module 1. Take a short break if needed before continuing.
"""
            },
            estimated_minutes=15,
            sensory_notes="Text only. Structured with clear headings and bullet points. No time pressure.",
            xp_reward=20,
            sort_order=2
        )
        db.add(lesson1_2)
        
        # Module 2: Managing Your Workday
        module2 = Module(
            course_id=course.id,
            title="Managing Your Workday",
            description="Practical strategies for time management, task prioritization, and maintaining your energy throughout shifts.",
            sort_order=2
        )
        db.add(module2)
        await db.flush()
        
        lesson2_1 = Lesson(
            module_id=module2.id,
            title="Time Management Strategies",
            lesson_type="article",
            content={
                "markdown": """# Time Management Strategies

Managing time at work can be challenging. This lesson offers concrete strategies you can start using today.

## The Basics

### Know Your Shift Structure
Every shift has predictable patterns:
- **Opening (first hour):** Setup tasks, usually quieter
- **Mid-shift:** Variable - could be busy or slow
- **Before lunch/closing:** Often busier
- **End of shift:** Closing tasks, handover notes

Understanding these patterns helps you plan your energy.

### Use Timers
Timers help with:
- Starting tasks you have been avoiding
- Knowing when to switch activities
- Taking breaks at regular intervals

**Tip:** Your phone timer works. So do kitchen timers. Use what works for you.

## The "Two-Minute Rule"

If a task takes less than two minutes, do it now.

Examples:
- Reshelving a single book a patron handed you
- Answering a quick question
- Writing a one-line note

If it takes more than two minutes, write it down for later.

## Task Batching

Group similar tasks together:

**Batching Example - Reshelving:**
Instead of reshelving one book at a time as they come in:
1. Collect returns in a cart
2. Sort by section
3. Reshelve in one focused trip

This is more efficient and reduces context-switching.

## Managing Interruptions

Interruptions are part of library work. Here is how to handle them:

### When You Are Helping a Patron
- Finish with them first
- Use a polite phrase for others waiting: "I will be right with you"

### When You Are Doing a Task
- Note where you stopped (a sticky note works)
- Help the patron
- Return to your note

### Protect Focus Time
If you have a task requiring concentration:
- Ask a colleague to cover desk questions briefly
- Work in a back area if possible
- Set a timer for focused work, then check in

## End-of-Shift Habits

Before leaving:
1. Write notes for the next shift (just key points)
2. Clear your immediate workspace
3. Check if anything urgent is pending

This takes 5 minutes and makes tomorrow easier.

---

**Practice:** Try the two-minute rule for your next shift.
"""
            },
            estimated_minutes=12,
            sensory_notes="Text-based with clear structure. Practical examples included. No multimedia.",
            xp_reward=15,
            sort_order=1
        )
        db.add(lesson2_1)
        
        lesson2_2 = Lesson(
            module_id=module2.id,
            title="Task Prioritization",
            lesson_type="article",
            content={
                "markdown": """# Task Prioritization

Not all tasks are equally urgent. This lesson helps you decide what to do first.

## The Priority Matrix

A simple way to sort tasks:

### Urgent AND Important
Do these first.
- Patron waiting for help
- Safety issue
- System outage affecting service

### Important but NOT Urgent
Schedule these.
- Updating displays
- Shelf reading
- Training tasks
- Ordering supplies

### Urgent but NOT Important
Handle quickly or delegate.
- Phone ringing while helping patron (colleague can answer)
- Non-critical email marked "urgent"

### Neither Urgent nor Important
Do these last, or skip.
- Reorganizing your desk drawer
- Checking personal phone

## Practical Daily Prioritization

**At the start of your shift:**
1. Check the handover notes from the previous shift
2. Note any scheduled events or tasks
3. Identify the top 3 things that MUST happen
4. Write them on a sticky note

**Throughout your shift:**
- Patron needs come first (they are usually urgent AND important)
- Return to your top 3 when desk is quiet
- New tasks get evaluated before doing them

## When Everything Feels Urgent

Sometimes everything seems urgent. Here is what to do:

1. **Pause.** Take one breath.
2. **Ask:** "What happens if this waits 10 minutes?"
3. **Focus on one thing.** Complete it. Move to the next.

If truly overwhelmed, ask a colleague or supervisor for help prioritizing. This is okay and expected.

## The "Good Enough" Principle

Perfectionism slows you down.

Ask yourself: "Is this good enough to serve its purpose?"
- Book display does not need to be Pinterest-worthy to attract readers
- Handover note does not need to be an essay
- Email reply can be brief and still polite

Done is better than perfect.

## Saying No (Politely)

You cannot do everything. It is okay to say:
- "I can do that after I finish this task"
- "That is not something I can take on today - can you ask [supervisor]?"
- "Let me add that to the list for when I have time"

---

**Reflection:** Think of a recent shift. Which tasks were truly urgent and important?
"""
            },
            estimated_minutes=10,
            sensory_notes="Text content only. Priority matrix explained in words, not graphics. Calm pacing.",
            xp_reward=15,
            sort_order=2
        )
        db.add(lesson2_2)
        
        lesson2_3 = Lesson(
            module_id=module2.id,
            title="Taking Effective Breaks",
            lesson_type="article",
            content={
                "markdown": """# Taking Effective Breaks

Breaks are not optional. They make you better at your job.

## Why Breaks Matter

Your brain needs rest to:
- Process information
- Regulate emotions
- Maintain focus
- Prevent burnout

Skipping breaks does not make you a better employee. It makes you tired.

## Types of Breaks

### Micro-breaks (30 seconds - 2 minutes)
- Look away from the screen
- Stretch your hands
- Take three deep breaths
- Walk to get water

**When:** Every 30-60 minutes during desk work

### Short breaks (5-15 minutes)
- Leave your desk area
- Go outside if possible
- Use the bathroom
- Have a snack
- Do not check work messages

**When:** Mid-shift, between major tasks

### Meal breaks (30 minutes - 1 hour)
- Actually eat
- Sit somewhere different from your work area
- Do something non-work-related

**When:** As scheduled by your shift

## Break Barriers (And Solutions)

### "I do not have time"
Reality: You do not have time NOT to take breaks. Fatigue causes mistakes.
Solution: Schedule breaks like tasks. Set an alarm if needed.

### "I will take one after this task"
Reality: There is always another task.
Solution: Take the break first. The task will still be there.

### "The desk is busy"
Reality: Desks need coverage, but you still deserve breaks.
Solution: Coordinate with colleagues. Ask: "Can you cover for 10 minutes?"

### "I feel guilty"
Reality: Guilt is a feeling, not a fact. Breaks are part of your job.
Solution: Remember that rested staff serve patrons better.

## Sensory Reset Breaks

If you are feeling overwhelmed:

1. **Find a quiet space** (staff room, outside, bathroom)
2. **Reduce input:**
   - Close your eyes
   - Use noise-canceling headphones or earplugs
   - Dim lights if possible
3. **Grounding techniques:**
   - Name 5 things you can see
   - Press your feet into the floor
   - Hold something with an interesting texture
4. **Return when ready**

There is no timer on a sensory break. Take what you need.

## Planning Your Shift Energy

Not all parts of your shift require the same energy.

**High energy tasks:** Patron desk, story time, busy periods
**Low energy tasks:** Shelf reading, processing, quiet admin work

Try to alternate when possible.

If you know you have a high-energy task coming:
- Take a break before
- Have water accessible
- Plan a recovery break after

## Remember

Taking breaks is professional behavior.
Rested staff do better work.
You deserve to feel okay at work.

---

**Action:** Identify one break barrier you face. What is one small thing you can do about it?
"""
            },
            estimated_minutes=12,
            sensory_notes="Calm, supportive tone. Addresses common barriers. Includes sensory regulation guidance.",
            xp_reward=15,
            sort_order=3
        )
        db.add(lesson2_3)
        
        # Module 3: Patron Service Excellence
        module3 = Module(
            course_id=course.id,
            title="Patron Service Excellence",
            description="Skills for positive desk interactions and handling challenging situations with confidence.",
            sort_order=3
        )
        db.add(module3)
        await db.flush()
        
        lesson3_1 = Lesson(
            module_id=module3.id,
            title="Desk Interactions",
            lesson_type="article",
            content={
                "markdown": """# Desk Interactions

The service desk is where most patron interactions happen. This lesson covers the basics of positive desk interactions.

## The Greeting

A good greeting:
- Acknowledges the patron
- Is not overwhelming
- Invites them to share their need

**Simple options:**
- "Hi, how can I help?"
- "Hello, what are you looking for today?"
- "Hi there" (then wait for them to speak)

**Avoid:**
- Overly enthusiastic greetings (can feel performative)
- Ignoring patrons until they speak first
- Complicated greetings that require response ("Hi! Lovely day, is not it? How are you doing?")

## Active Listening

When a patron is speaking:

1. **Face them** (or angle toward them)
2. **Stop other tasks** (put down the book, look up from the screen)
3. **Let them finish** before responding
4. **Confirm understanding:** "So you are looking for books about gardening?"

If you did not understand:
- "Could you say that again?"
- "I want to make sure I understand - you need...?"

## Common Transactions

### Checking Out Books
1. Greet patron
2. Take items or scan cards
3. Mention due date: "These are due back on [date]"
4. Offer receipt if they want one
5. "Is there anything else?" or "Have a good day"

### Library Card Sign-up
1. "I can help you with that"
2. Explain what you need (ID, address verification)
3. Walk through the form together if needed
4. Give them the card, explain briefly how it works
5. "Welcome to the library"

### Computer Help
1. Ask what they are trying to do
2. Assess their comfort level
3. Either guide them verbally or show them directly (ask preference)
4. Check they are set before leaving: "All good?"

### Book Recommendations
1. Ask what they have enjoyed before
2. Ask about mood/topic preference
3. Offer 2-3 options (not too many)
4. "Would you like me to find more, or is this a good start?"

## When You Do Not Know the Answer

This happens. It is okay.

**What to say:**
- "I do not know, but let me find out"
- "That is a good question - I will check with a colleague"
- "I am not sure, but I can look it up for you"

**What NOT to say:**
- Making something up
- "You should know that" (to the patron)
- Dismissing the question

## Ending Interactions

A clean ending helps both you and the patron.

**Phrases that work:**
- "Is there anything else?"
- "You are all set"
- "Have a good day" / "Enjoy your book"
- "Let me know if you need anything else"

If the patron is chatty and you need to help others:
- "I am glad I could help. I should check on the other patrons, but enjoy your visit."

---

**Practice:** Pick one transaction type to focus on improving this week.
"""
            },
            estimated_minutes=15,
            sensory_notes="Structured with clear headings. Script examples provided. No role-play required.",
            xp_reward=20,
            sort_order=1
        )
        db.add(lesson3_1)
        
        lesson3_2 = Lesson(
            module_id=module3.id,
            title="Handling Difficult Situations",
            lesson_type="article",
            content={
                "markdown": """# Handling Difficult Situations

Difficult situations happen. This lesson helps you navigate them with confidence.

## First: Stay Regulated

When a situation becomes difficult, your stress response activates. This is normal.

**Before responding:**
- Take one breath
- Unclench your jaw
- Lower your shoulders
- Speak slightly slower than feels natural

You cannot de-escalate someone else if you are escalating yourself.

## Common Difficult Situations

### Patron Is Frustrated About a Policy
Example: "Why can not I check out more than 10 items?!"

**Approach:**
1. Validate: "I understand that is frustrating"
2. Explain briefly (do not over-explain): "The limit helps us make sure materials are available for everyone"
3. Offer alternatives: "You can return some and check out more anytime"
4. If they push back: "I hear you. I can not change the policy, but I can pass your feedback to my supervisor"

### Patron Is Confused or Seems Lost
Example: Someone wandering, looking distressed

**Approach:**
1. Approach gently: "Hi, are you looking for something?"
2. Give time to respond
3. Offer specific help: "The bathrooms are down that hall" or "Would you like help finding a book?"
4. If they seem distressed but not in danger, check in periodically

### Patron Is Being Loud
Example: Talking loudly on phone in quiet area

**Approach:**
1. Approach calmly
2. Use "I" statements: "I need to let you know this is a quiet zone"
3. Offer alternative: "There is a phone-friendly area near the entrance"
4. Thank them for understanding

### Patron Is Upset With You Specifically
Example: "You are not helping me at all!"

**Approach:**
1. Do not take it personally (even though it feels personal)
2. Stay calm: "I want to help. Let me try a different approach."
3. If it continues: "I am going to ask my colleague to help you instead"
4. It is okay to step away

## De-escalation Basics

**Do:**
- Keep your voice calm and steady
- Use the patron's name if you know it
- Acknowledge their feelings: "I can see you are upset"
- Focus on what you CAN do, not what you cannot

**Do Not:**
- Raise your voice to match theirs
- Use dismissive language: "Calm down," "It is not a big deal"
- Touch them
- Block their exit path

## Boundary-Setting for Scope Creep and Manipulation

You can be kind and still set limits. Staff do not need to meet every request.

### Scripts for Scope Creep
Use clear, steady language:
- "I can help with library services, but I cannot complete that task for you."
- "That request is outside what we provide at this desk. I can show you what we *can* do."
- "I want to support you, and this is the part I can help with right now."

### "That Is Not in Our Service Offerings" Scripts
- "That is not in our service offerings, but I can point you to a place that does offer that."
- "We do not provide that service here. We do offer [specific library service], if that helps."
- "I cannot approve that request. I can explain the policy and your next option."

### Redirect to Appropriate Resources
When possible, give a next step:
- Community services directory
- Municipal or county office contacts
- Legal aid, social services, or crisis resources (based on your local referral list)
- Internal library options (appointments, programs, specialist staff)

### Policy-Backed Boundaries
Use policy as support, not as a weapon:
- "Library policy requires me to handle this in this way."
- "To be fair to all patrons, I need to follow the same service limits for everyone."
- "I can document your feedback so leadership can review this policy."

### Manager Support and Escalation
Escalate when:
- A patron keeps pushing after you set a clear limit
- The request involves legal, safety, or financial risk
- You feel pressured, cornered, or unsafe

Escalation script:
- "I have explained what I can offer. My manager can review next steps with you."

### Track Requests Outside Scope
Document patterns, not just incidents:
- What was requested
- Why it was out of scope
- What alternative you offered
- Whether escalation was needed

### Inform Policy Improvements
Recurring out-of-scope requests are useful data. Share them in team reviews to:
- Update service guides
- Improve referral lists
- Clarify unclear policies
- Identify where new services may be needed

### Protect Against Patron Manipulation
Manipulation can include guilt, urgency pressure, splitting staff, or repeated boundary testing.

Helpful responses:
- "I hear this feels urgent. I still need to follow our process."
- "My answer is the same as my colleague's."
- "I will not continue if I am being yelled at. I can continue when we both speak calmly."

### Document Unreasonable Demands
If demands become aggressive, abusive, or repetitive, document objectively:
- Exact words or behavior
- Time and location
- Staff present
- Impact on service or safety
- Actions taken

Clear documentation protects staff, supports manager follow-up, and creates a factual record.

**Remember:** It is okay to have limits.

## When to Get Help

Get a supervisor or colleague if:
- You feel unsafe
- The patron is threatening
- You have tried and the situation is not improving
- Another patron is being affected
- You are overwhelmed

**How to get help:**
- "Let me get someone who can help with this"
- Catch a colleague's eye or step toward them
- Use a code phrase if your library has one

## After a Difficult Interaction

Difficult interactions affect you. That is normal.

**Take care of yourself:**
- Take a short break if possible
- Drink water
- Tell a colleague what happened (debriefing helps)
- Do not replay it endlessly - you did your best
- If it was serious, document it

**Remember:**
- You are not responsible for other people's emotions
- You handled it as well as you could in the moment
- It is okay to feel shaky afterward

## You Are Not Alone

Every staff member deals with difficult situations. You are not expected to handle everything perfectly. Ask for help, debrief with colleagues, and be kind to yourself.

---

**Congratulations!** You have completed Library Essentials. Take a moment to reflect on what you learned before your certificate is generated.
"""
            },
            estimated_minutes=16,
            sensory_notes="Supportive tone throughout. Addresses emotional regulation. No judgment for finding situations hard.",
            xp_reward=25,
            sort_order=2
        )
        db.add(lesson3_2)
        
        await db.commit()
        print(f"Created course 'Library Essentials' with id={course.id}")
        print(f"  - Module 1: '{module1.title}' (2 lessons)")
        print(f"  - Module 2: '{module2.title}' (3 lessons)")
        print(f"  - Module 3: '{module3.title}' (2 lessons)")
        print("  - Total: 7 lessons, ~90 minutes")
        
        return course


async def main():
    print("Seeding staff training course...")
    try:
        _ = await create_staff_training_course()
        print("\nDone!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
