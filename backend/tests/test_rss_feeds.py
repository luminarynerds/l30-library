from app.services.release_sources.rss_feeds import FEEDS, parse_feed

_RSS = """<?xml version="1.0"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
  <item>
    <title>Most Anticipated: Fall 2026</title>
    <link>https://themillions.com/2026/08/fall.html</link>
    <pubDate>Mon, 04 Aug 2026 10:00:00 +0000</pubDate>
    <description>short summary</description>
    <content:encoded><![CDATA[<p>Full body with <b>Villa Coco</b> by Greer.</p>]]></content:encoded>
  </item>
  <item>
    <title>No Body Post</title>
    <link>https://themillions.com/2026/08/x.html</link>
    <description>only desc</description>
  </item>
</channel></rss>"""


def test_parse_feed_extracts_items_and_prefers_content_encoded():
    items = parse_feed(_RSS)
    assert len(items) == 2
    a = items[0]
    assert a["url"] == "https://themillions.com/2026/08/fall.html"
    assert a["title"] == "Most Anticipated: Fall 2026"
    assert "Villa Coco" in a["body"]
    b = items[1]
    assert b["url"].endswith("/x.html")
    assert b["body"] == "only desc"


def test_feeds_include_youth_diverse_sources():
    slugs = {slug for slug, _ in FEEDS}
    assert {"tlt", "brown-bookshelf"} <= slugs


def test_feeds_exclude_bookriot_for_tos():
    slugs = {slug for slug, _ in FEEDS}
    assert "bookriot" not in slugs
    assert {"millions", "lithub", "tlt", "brown-bookshelf"} <= slugs
