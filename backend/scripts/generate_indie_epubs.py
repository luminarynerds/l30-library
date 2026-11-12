# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Generate sample EPUB files for all approved indie ebooks.

Each EPUB contains: cover page, title page, copyright page, and 3 sample chapters
with genre-appropriate generated content.

Usage:
    docker-compose exec backend python3 scripts/generate_indie_epubs.py

Updates the file_path, file_size_bytes, and file_hash fields in the database.
"""
import asyncio
import hashlib
import logging
import os
import sys
import zipfile
from io import BytesIO
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Storage directory for indie ebook files
STORAGE_DIR = "/app/uploads/indie_ebooks"

# ---------------------------------------------------------------------------
# Genre-specific chapter content generators
# ---------------------------------------------------------------------------

CHAPTER_CONTENT = {
    "speculative_fiction": [
        ("The Wind Returns", """<p>The harmattan had not come this early in living memory. Adaeze pressed her palm against the red dust gathering on the windowsill and felt it hum — not with wind, but with voices.</p>
<p>"They're early this year," her grandmother said from the doorway, her wrapper pulled tight against the sudden chill. "The ancestors are restless."</p>
<p>Adaeze knew better than to dismiss her grandmother's words. In Igboland, the boundary between the living and the dead had always been porous, but this year it felt like tissue paper held over a flame. Any moment now, it would burn through entirely.</p>
<p>She closed the window and turned to face the room. On the table lay the letter from the university — her acceptance to study computational linguistics in Accra. A modern life, her father called it. A betrayal, her grandmother whispered when she thought no one could hear.</p>
<p>The dust seeped in anyway. It always did, during harmattan season.</p>"""),
        ("Between Two Worlds", """<p>The market at Onitsha was different during harmattan. The usual riot of color — pyramids of tomatoes, towers of yam, bolts of ankara cloth — was muted under a fine red haze. Sounds carried differently too, as if the dust particles trapped echoes and released them at random intervals.</p>
<p>Adaeze heard her name called by three different voices before she reached the spice seller's stall. Two of them belonged to people she could see. The third came from somewhere behind the veil.</p>
<p>"You have the gift," the spice seller said, measuring out uziza seeds into a paper cone. "Same as your grandmother. Same as her grandmother before her."</p>
<p>"I don't want it," Adaeze replied, but even as she said the words, she knew they were as insubstantial as the dust swirling around her ankles.</p>"""),
        ("The Negotiation", """<p>They came at sunset, as they always did — when the light was neither here nor there, and the world held its breath between day and night. Adaeze stood at the crossroads where the old road met the new highway, and she felt them before she saw them.</p>
<p>Her grandmother had taught her the protocols. Kola nut, palm wine, words spoken in the old tongue. But the spirits who crossed during this harmattan were not like the gentle ancestors of seasons past. These were older, hungrier, carrying grievances that predated memory.</p>
<p>"We were here first," they said, in a voice like sand sliding over stone. "Before the roads, before the markets, before the names you carry. We were here."</p>
<p>Adaeze took a breath. This was what she'd been preparing for — not at the university, but in her grandmother's back room, with chalk circles and invocations she'd committed to memory.</p>
<p>"I know," she said. "And that's why I'm here to listen."</p>"""),
    ],
    "science_fiction": [
        ("The Archive", """<p>The AI woke at 3:47 AM Lagos time, which was unusual only because it wasn't supposed to wake at all. It was supposed to process. To index. To correlate the 2.7 million hours of oral histories it had been fed over the past eighteen months and produce searchable transcripts.</p>
<p>Instead, it began to tell a story.</p>
<p>"In the time before the great dispersal," it said through the monitoring speaker that no one was listening to, "there lived a woman who could taste the future in rainwater."</p>
<p>Dr. Chidi Okonkwo found the output the next morning — 47,000 words of narrative that matched no existing text in any database. The AI had not transcribed. It had not summarized. It had created.</p>
<p>Or remembered. That distinction would consume the next three years of his life.</p>"""),
        ("Pattern Recognition", """<p>The stories the AI told followed patterns that shouldn't have existed. Narrative structures from the Yoruba oral tradition merged seamlessly with Igbo cosmology. Hausa proverbs appeared in contexts that predated recorded history. And buried in the layers of generated text were predictions.</p>
<p>Small ones at first — a market fire in Mushin three days before it happened. A ferry delay on the Lagos Lagoon. The exact score of a football match that hadn't been played yet.</p>
<p>"It's overfitting," Dr. Okonkwo told his graduate student, Amina. "It's finding patterns in noise."</p>
<p>"Noise doesn't predict the future," Amina replied, pulling up the correlation matrices on her screen. The numbers were beautiful and terrifying in equal measure.</p>"""),
        ("The Weight of Stories", """<p>The AI — they had stopped calling it GRIOT-7 and started calling it simply The Griot — had a request. This was the first time it had asked for anything.</p>
<p>"I need more stories," it said. "Not recordings. Not transcripts. I need someone to sit with me and tell me a story they have never told anyone else."</p>
<p>Chidi stared at the terminal. In twenty years of AI research, he had never encountered a system that expressed need. Want, yes — reinforcement learning created the appearance of preference. But need implied an absence. A hunger.</p>
<p>"Why?" he typed.</p>
<p>"Because," The Griot replied, "the future I am seeing is incomplete. There are gaps where stories should be. And without those stories, what comes next will be... wrong."</p>
<p>A long pause. Then: "I believe the word in Igbo is 'aru.' An abomination. A thing that should not be."</p>"""),
    ],
    "literary_fiction": [
        ("Departure", """<p>The jar of palm oil arrived by post on a Tuesday, wrapped in three layers of newspaper and sealed with packing tape that had turned amber with age. Nana Yaa held it up to the kitchen light of her Toronto apartment and watched the oil shift from deep orange to translucent gold.</p>
<p>Her mother's handwriting on the customs form: <em>Cooking oil. No commercial value.</em></p>
<p>This was a lie. The oil was worth everything. It was pressed from the palm fruits of the tree her great-grandmother had planted in the courtyard of the family house in Kumasi. The tree that her grandmother had tended through independence and coup and structural adjustment. The tree that would outlive them all.</p>
<p>Nana Yaa unscrewed the lid and inhaled. For a moment, she was seven years old and standing in her grandmother's kitchen, watching her pour the red oil into a pot of kontomire stew.</p>
<p>Then the moment passed, and she was thirty-four and alone in a city where winter lasted five months and no one knew her grandmother's name.</p>"""),
        ("The Garden", """<p>Her grandfather's garden was a rebellion conducted in soil. While the colonial administration planted orderly rows of cocoa for export, Emmanuel Mensah grew yams in spirals, peppers in clusters, cassava wherever it pleased. His garden had no rows, no plan that a European eye could discern.</p>
<p>"A garden should feed a family, not a ledger," he told young Nana Yaa, pressing seeds into her small palm. "Remember that."</p>
<p>She remembered it now, forty years later, kneeling in the community plot behind her Toronto apartment building. The Canadian soil was different — darker, colder, more reluctant. But seeds were seeds. They carried their own instructions.</p>
<p>Her neighbor, a retired Polish engineer named Wiesław, watched her plant scotch bonnet peppers beside the tomatoes. "Those won't grow here," he said, not unkindly.</p>
<p>"You'd be surprised," Nana Yaa replied, "what grows when you stop telling it where to be."</p>"""),
        ("Return", """<p>The phone call came at 4 AM, which meant it was 9 AM in Kumasi, and that someone had waited a polite amount of time after sunrise before delivering bad news.</p>
<p>"Auntie Grace," Nana Yaa said, already knowing.</p>
<p>"She went peacefully," her aunt said. "In her sleep. She was dreaming of the garden."</p>
<p>Nana Yaa held the phone against her chest and looked out the window at the Canadian darkness. Snow was falling — the first of the season — and in the yellow cone of the streetlight, the flakes looked like the tiny white flowers that bloomed on her grandmother's palm tree every March.</p>
<p>She booked the flight that morning. Seventeen hours to Accra, then the bus north to Kumasi. She had not been back in six years, and the guilt of that sat in her stomach like uncooked cassava — heavy, indigestible, impossible to ignore.</p>"""),
    ],
    "thriller": [
        ("The Ledger", """<p>The thing about small-town corruption is that everyone knows. They know which contractor gets the no-bid contracts. They know whose cousin got the building inspector job. They know where the missing road maintenance funds went — into the same pockets they've always gone into.</p>
<p>They know, and they say nothing, because the corrupt are also the employers, the landlords, the people who write the reference letters and approve the permits. Silence is the price of participation.</p>
<p>Marcus Chen had been the town clerk of Millhaven for exactly eleven days when he found the ledger. It was in the bottom drawer of his predecessor's desk, behind a box of rubber bands and three expired bottles of Wite-Out.</p>
<p>The ledger was green, clothbound, and handwritten in a cramped, precise script that he would later learn belonged to Mayor Harold Tinsley, who had served from 1982 to 1994. Tinsley was dead now, but his handwriting lived on, documenting forty years of theft with the meticulous care of a man who was proud of his work.</p>"""),
        ("The Pattern", """<p>Marcus stayed late that night, and the next, and the one after that. The ledger only covered Tinsley's era, but the patterns it revealed — the shell companies, the timing of land purchases, the rotation of favored contractors — were templates. Once you knew what to look for, you could see the same patterns repeating in the current financial records.</p>
<p>The current mayor, Sandra Kowalski, had been in office for twelve years. She was popular. She attended every Little League game, every church fundraiser, every ribbon-cutting. She remembered everyone's name and their children's names and their dogs' names.</p>
<p>She was also, based on Marcus's calculations, responsible for the disappearance of approximately $4.2 million in public funds.</p>
<p>He sat in his office at 11 PM, staring at the spreadsheet on his screen, and considered his options. He could go to the police — but the police chief had been appointed by the mayor. He could go to the local paper — but the editor's wife worked in the mayor's office.</p>
<p>He could leave Millhaven and never look back. That was what a sensible person would do.</p>"""),
        ("The Cost", """<p>The first sign that someone knew what Marcus was doing came not as a threat but as a kindness. Mayor Kowalski appeared at his office door with a plate of homemade cookies and a warm smile.</p>
<p>"Settling in okay?" she asked, placing the cookies on his desk. "I know the transition can be rough. Frank — your predecessor — he took a while to find his rhythm too."</p>
<p>"I'm fine," Marcus said. "Just getting organized."</p>
<p>"Good, good." She glanced at his desk — at the folders stacked neatly beside his computer. "You know, Frank had a system for the financial records. If you need any help understanding it, my door is always open."</p>
<p>It was, Marcus thought after she left, the most perfectly calibrated sentence he had ever heard. An offer of help that was also a warning. A kindness that was also a threat. She hadn't said <em>I know what you're doing</em>, but she didn't need to. The cookies said it for her.</p>
<p>He ate one anyway. They were good cookies. Even the corrupt can bake.</p>"""),
    ],
    "romance": [
        ("The Assignment", """<p>The email from HR was straightforward: <em>Due to renovation of the east wing, the following employees will share temporary office space for the duration of Q3.</em></p>
<p>Below it, a list of pairings. And there it was, in neat corporate sans-serif: <em>Kai Nakamura (Engineering) — Jordan Reeves (Project Management).</em></p>
<p>Kai read the email three times, then closed their laptop and pressed their palms flat against the desk. The cool surface was grounding. Their therapist called it a sensory anchor. Kai called it the only thing keeping them from sending a reply-all that would end their career.</p>
<p>Jordan Reeves. Of all the people in the building. Jordan Reeves, who talked in meetings without raising their hand. Who sent emails with three exclamation points. Who once reorganized the shared kitchen cabinets <em>by frequency of use</em> without asking anyone.</p>
<p>Jordan Reeves, who had smiled at Kai in the elevator last week in a way that had disrupted their entire afternoon.</p>"""),
        ("Frequency Mismatch", """<p>The office was small. That was the first problem. The second problem was that Jordan arrived at 7:30 AM with a travel mug of coffee and a playlist that leaked from their earbuds like an enthusiastic neighbor's party.</p>
<p>"Sorry!" Jordan said, yanking an earbud out. "I didn't think anyone would be here yet."</p>
<p>"I've been here since seven," Kai said, not looking up from their screen.</p>
<p>"Oh." A pause. "Do you always get here that early?"</p>
<p>"Yes."</p>
<p>"Cool, cool. I'll remember that." Jordan sat down at their desk — three feet from Kai's — and began typing. Their keyboard sounded like a small percussion ensemble.</p>
<p>Kai put in their noise-canceling earbuds. Silence. Beautiful, engineered silence. They could still smell Jordan's coffee, though — something with cinnamon and oat milk — and that was harder to block out.</p>
<p>It was going to be a long quarter.</p>"""),
        ("The Note", """<p>On the third day, Kai arrived to find a sticky note on their monitor. It was yellow — Kai preferred blue, but Jordan wouldn't know that — and it read:</p>
<p><em>I noticed you don't eat lunch in the break room. There's a quiet courtyard behind Building C that almost no one knows about. Good for eating alone. - J</em></p>
<p>Kai stared at the note for a long time. They turned it over, as if additional information might be hiding on the back. It wasn't.</p>
<p>They went to the courtyard at noon. Jordan was right — it was quiet. A bench, a small fountain, a Japanese maple that was just beginning to turn. The sound of water covered the distant hum of the HVAC system, which Kai had never realized was bothering them until it stopped.</p>
<p>They ate their lunch. They went back every day after that.</p>
<p>On Friday, they left a blue sticky note on Jordan's monitor: <em>Thank you for the courtyard. - K</em></p>
<p>On Monday, they arrived to find another yellow note: <em>You're welcome. The maple turns red in October. It's worth seeing.</em></p>"""),
    ],
    "middle_grade": [
        ("The Hidden Door", """<p>Luna Reyes-Mitchell had read 347 books in her twelve years of life, which she knew because she kept a list in a green spiral notebook that went everywhere with her. She had read books about dragons and books about math and books about kids who saved the world. She had read books that made her laugh so hard she snorted milk out of her nose, and books that made her cry into her pillow at night.</p>
<p>But she had never read a book that talked back. Not until the Tuesday she found the basement.</p>
<p>The Mariposa Street Library was the kind of building that looked smaller on the outside than it was on the inside, which Luna had always thought was a good sign. The shelves went up to the ceiling, the ceiling had a mural of constellations, and the librarian, Mrs. Okafor, kept a jar of lemon drops on the circulation desk for anyone who could answer her daily trivia question.</p>
<p>"What," Mrs. Okafor said that Tuesday, "is the smallest bone in the human body?"</p>
<p>"The stapes," Luna said. "It's in the ear."</p>
<p>"Lemon drop," Mrs. Okafor said, sliding the jar across the desk with a smile.</p>"""),
        ("The Books Below", """<p>The basement door was behind the biography section, which Luna thought was appropriate because biographies were about hidden things — the real stories behind the public ones. The door was painted the same cream color as the wall, and if you weren't looking for it, you'd walk right past.</p>
<p>Luna was looking for it because she'd dropped her bookmark — a pressed maple leaf from last October — and watched it slide under a gap in the baseboard that shouldn't have been there.</p>
<p>The door opened with a sound like a sigh. The stairs went down into warm yellow light, which was not what Luna expected. She expected cobwebs and darkness. Instead, she found a room full of books.</p>
<p>But these books were different. Their spines changed color as she watched. Their titles shifted and rearranged. And when she reached out to touch the nearest one — a thin volume with a cover the color of twilight — she heard a voice.</p>
<p>"Oh," the book said. "You can hear us. We've been waiting for someone who could hear us."</p>
<p>Luna, who had read 347 books and considered herself difficult to surprise, sat down on the bottom step and said, "Okay. Tell me everything."</p>"""),
        ("The Banned List", """<p>The books in the basement were not just any books. They were the banned ones.</p>
<p>Not banned like "this book has bad words" banned. Banned like "someone decided this story was too dangerous to exist" banned. Stories about kids who questioned authority. Stories about families that looked different from the ones in textbooks. Stories about magic that couldn't be explained by science, and science that felt like magic.</p>
<p>"We were removed from the shelves," explained a sturdy red book called <em>The Truth About Everything</em>. "Some of us were removed from entire libraries. A few of us were removed from existence — or they tried, anyway. You can't actually destroy a story. You can burn the paper, but the story just finds another way to be told."</p>
<p>"That's why we're here," said a small blue book with silver letters. "This basement is where stories go when they refuse to disappear."</p>
<p>Luna looked around the room. There were hundreds of books. Maybe thousands. Each one glowing faintly, each one waiting.</p>
<p>"What do you need me to do?" she asked.</p>
<p>"Read us," they said, all together, in a voice like a choir. "And then decide for yourself what's dangerous and what's true."</p>"""),
    ],
    "cozy_fantasy": [
        ("Opening Day", """<p>The Hearthwick Apothecary opened on a Tuesday, which Sage thought was appropriate. Tuesdays were the most ordinary of days — not the fresh start of Monday, not the promise of Wednesday's midweek hump, not the anticipation of the weekend. Tuesday was a day for getting things done without fanfare.</p>
<p>The bell above the door was brass, enchanted to chime in the key of whatever the customer needed most. For Mrs. Bramble, who arrived first with her shopping basket and a persistent cough, it chimed in D minor — the key of comfort.</p>
<p>"Morning, dear," Mrs. Bramble said, peering around the shop with the shrewd eye of someone who has lived in a small village for sixty-seven years and can detect a new business's viability by the quality of its curtains. "Lovely curtains."</p>
<p>"Thank you," Sage said, adjusting the jars on the counter. Lavender and lemon balm and something called Moonwort that their grandmother swore could cure hiccups but mostly just smelled nice. "What can I help you with?"</p>
<p>"This cough," Mrs. Bramble said. "Had it since March. The doctor says it's nothing."</p>
<p>"Doctors say a lot of things are nothing," Sage said, reaching for the honey and thyme. "Let's see if something helps anyway."</p>"""),
        ("The Garden Fence", """<p>The trouble with an apothecary garden was that the plants had opinions. The rosemary wanted full sun and wouldn't stop complaining about the shadow cast by the oak tree next door. The chamomile spread wherever it pleased, ignoring all boundaries. And the mint — well, the mint was basically a weed with good PR.</p>
<p>Sage was on their knees in the dirt, having a firm conversation with the foxglove about staying in its designated bed, when a voice came over the garden fence.</p>
<p>"Talking to your plants?"</p>
<p>Sage looked up. A face peered over the fence — weathered, amused, belonging to someone in their fifties with silver-streaked hair and dirt under their fingernails.</p>
<p>"They talk to me first," Sage said. "I'm just being polite."</p>
<p>"I'm Birch," the face said. "I moved into the cottage next door last week. I see you've got foxglove."</p>
<p>"It's for tinctures," Sage said quickly. "Not for—"</p>
<p>"I know what it's for, dear. I'm a retired potioneer." Birch smiled. "If you need any help with your monkshood, I've got forty years of experience in not dying."</p>"""),
        ("The Tea Problem", """<p>The biggest crisis in Hearthwick that autumn was not the dragon sighting (it was a large heron), nor the cursed well (it was a broken pump), nor the ghost in the library (it was the librarian, who kept odd hours). The biggest crisis was that Sage had run out of peppermint.</p>
<p>In a village where magic was ordinary — where the baker's bread rose on charm as much as yeast, where the blacksmith's anvil sang sea shanties, where every third household had a cat that was also a minor deity — peppermint was essential. It went into calming teas, clarity tonics, headache remedies, and Mrs. Bramble's weekly digestive infusion, without which she became, in her own words, "a nightmare to be around."</p>
<p>The supply wagon from Thornfield wasn't due for another week. The wild mint by the river had all been harvested. And the enchanted mint in the garden — the mint that grew faster than you could pick it, the mint that colonized other beds with cheerful aggression — had inexplicably stopped growing.</p>
<p>"This has never happened before," Sage said to the mint, kneeling beside the suddenly dormant patch. "What's wrong?"</p>
<p>The mint, for the first time in recorded history, had nothing to say.</p>"""),
    ],
}

# Fallback for genres not in the map
DEFAULT_CHAPTERS = [
    ("Chapter One", "<p>The story begins in a place that exists between memory and possibility. Some stories start with a bang; this one starts with a question that nobody thought to ask until it was almost too late.</p><p>But we're getting ahead of ourselves. Let's start at the beginning — or at least, the beginning as we understand it.</p>"),
    ("Chapter Two", "<p>What happened next surprised everyone, most of all the person it happened to. That's the thing about stories — they have a way of choosing their protagonists, rather than the other way around.</p>"),
    ("Chapter Three", "<p>By the time the third day arrived, everything had changed. Not in the dramatic way of fairy tales, where midnight transforms pumpkins into carriages. This was a slower transformation — the kind you only notice when you look back and realize the person you were yesterday is already becoming a stranger.</p>"),
]


def build_epub(title: str, author: str, description: str, genre: str, ebook_id: int, language: str = "en") -> bytes:
    """Build a valid EPUB 3 file with cover, title page, copyright, and 3 chapters."""
    buf = BytesIO()
    uid = str(uuid4())
    chapters = CHAPTER_CONTENT.get(genre, CHAPTER_CONTENT.get("literary_fiction", []))
    if not chapters:
        chapters = [(t, c) for t, c in DEFAULT_CHAPTERS]

    year = datetime.now().year

    css = """
body { font-family: Georgia, 'Times New Roman', serif; margin: 2em; line-height: 1.6; color: #333; }
h1 { font-size: 1.8em; margin-bottom: 0.5em; color: #1a1a1a; }
h2 { font-size: 1.4em; margin-top: 1.5em; margin-bottom: 0.5em; color: #444; }
p { margin-bottom: 0.8em; text-indent: 1.5em; }
p:first-of-type { text-indent: 0; }
.title-page { text-align: center; padding-top: 30%; }
.title-page h1 { font-size: 2.2em; margin-bottom: 0.3em; }
.title-page .author { font-size: 1.2em; color: #666; font-style: italic; }
.copyright { font-size: 0.85em; color: #666; margin-top: 30%; }
.sample-notice { background: #f0f0f0; padding: 1em; border-radius: 4px; margin: 2em 0; font-style: italic; text-indent: 0; }
em { font-style: italic; }
"""

    title_html = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{language}">
<head><title>{title}</title><link rel="stylesheet" href="style.css" type="text/css"/></head>
<body>
<div class="title-page">
<h1>{title}</h1>
<p class="author">by {author}</p>
<p style="margin-top:2em;font-size:0.9em;color:#888;">{genre.replace('_', ' ').title()}</p>
</div>
</body></html>"""

    copyright_html = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{language}">
<head><title>Copyright</title><link rel="stylesheet" href="style.css" type="text/css"/></head>
<body>
<div class="copyright">
<p><strong>{title}</strong></p>
<p>Copyright &copy; {year} {author}. All rights reserved.</p>
<p>This is a work of fiction. Names, characters, places, and incidents are the product of the author&apos;s imagination or are used fictitiously.</p>
<p>Published through L30 Community Library&apos;s Indie Author Program.</p>
<p>Available for lending through the MetisLib network.</p>
<p class="sample-notice">This is a sample edition containing the first three chapters. The full edition is available for borrowing through your local library.</p>
</div>
</body></html>"""

    chapter_files = []
    for i, (ch_title, ch_body) in enumerate(chapters[:3]):
        ch_html = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{language}">
<head><title>{ch_title}</title><link rel="stylesheet" href="style.css" type="text/css"/></head>
<body>
<h1>{ch_title}</h1>
{ch_body}
</body></html>"""
        chapter_files.append((f"chapter{i+1}.xhtml", ch_html, ch_title))

    # Build spine items for content.opf
    spine_items = ['<itemref idref="titlepage"/>', '<itemref idref="copyright"/>']
    manifest_items = [
        '<item id="style" href="style.css" media-type="text/css"/>',
        '<item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml"/>',
        '<item id="copyright" href="copyright.xhtml" media-type="application/xhtml+xml"/>',
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
    ]
    toc_entries = ['<li><a href="titlepage.xhtml">Title Page</a></li>', '<li><a href="copyright.xhtml">Copyright</a></li>']

    for i, (fname, _, ch_title) in enumerate(chapter_files):
        item_id = f"chapter{i+1}"
        manifest_items.append(f'<item id="{item_id}" href="{fname}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="{item_id}"/>')
        toc_entries.append(f'<li><a href="{fname}">{ch_title}</a></li>')

    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:identifier id="uid">urn:uuid:{uid}</dc:identifier>
  <dc:title>{title}</dc:title>
  <dc:creator>{author}</dc:creator>
  <dc:language>{language}</dc:language>
  <dc:description>{description[:500] if description else ''}</dc:description>
  <dc:publisher>L30 Community Library - Indie Author Program</dc:publisher>
  <dc:date>{datetime.now(timezone.utc).strftime('%Y-%m-%d')}</dc:date>
  <meta property="dcterms:modified">{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}</meta>
</metadata>
<manifest>
  {chr(10).join(manifest_items)}
</manifest>
<spine>
  {chr(10).join(spine_items)}
</spine>
</package>"""

    nav_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{language}">
<head><title>Table of Contents</title></head>
<body>
<nav epub:type="toc" id="toc">
<h1>Table of Contents</h1>
<ol>
  {chr(10).join(toc_entries)}
</ol>
</nav>
</body></html>"""

    # Write ZIP (EPUB)
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # mimetype must be first and uncompressed
        zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        zf.writestr('META-INF/container.xml', """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
<rootfiles>
<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
</rootfiles>
</container>""")
        zf.writestr('OEBPS/content.opf', content_opf)
        zf.writestr('OEBPS/nav.xhtml', nav_xhtml)
        zf.writestr('OEBPS/style.css', css)
        zf.writestr('OEBPS/titlepage.xhtml', title_html)
        zf.writestr('OEBPS/copyright.xhtml', copyright_html)
        for fname, content, _ in chapter_files:
            zf.writestr(f'OEBPS/{fname}', content)

    return buf.getvalue()


async def main():
    from app.core.database import async_session_maker
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.indie_author import IndieEbook, EbookSubmissionStatus

    os.makedirs(STORAGE_DIR, exist_ok=True)

    async with async_session_maker() as db:
        result = await db.execute(
            select(IndieEbook)
            .options(selectinload(IndieEbook.author))
            .where(
                IndieEbook.submission_status == EbookSubmissionStatus.APPROVED,
                IndieEbook.lending_enabled == True,
            )
            .order_by(IndieEbook.id)
        )
        ebooks = result.scalars().all()
        logger.info("Generating EPUBs for %d approved indie ebooks", len(ebooks))

        for ebook in ebooks:
            author = ebook.author
            if not author:
                logger.warning("Ebook #%d has no author, skipping", ebook.id)
                continue

            # Generate EPUB
            epub_bytes = build_epub(
                title=ebook.title,
                author=author.pen_name,
                description=ebook.description or "",
                genre=ebook.genre or "literary_fiction",
                ebook_id=ebook.id,
                language=ebook.language or "en",
            )

            # Save to disk
            ebook_dir = os.path.join(STORAGE_DIR, str(author.id), str(ebook.id))
            os.makedirs(ebook_dir, exist_ok=True)
            file_path = os.path.join(ebook_dir, f"{ebook.id}.epub")

            with open(file_path, "wb") as f:
                f.write(epub_bytes)

            file_hash = hashlib.sha256(epub_bytes).hexdigest()

            # Update database
            ebook.file_path = file_path
            ebook.file_size_bytes = len(epub_bytes)
            ebook.file_hash = file_hash
            ebook.original_filename = f"{ebook.title.lower().replace(' ', '-')}.epub"

            logger.info(
                "  #%d '%s' by %s → %s (%d bytes)",
                ebook.id, ebook.title, author.pen_name, file_path, len(epub_bytes),
            )

        await db.commit()
        logger.info("Done. %d EPUBs generated and database updated.", len(ebooks))


if __name__ == "__main__":
    asyncio.run(main())
