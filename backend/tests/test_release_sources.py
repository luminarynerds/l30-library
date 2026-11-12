from datetime import date

from app.services.release_sources.base import clean_isbn13, parse_us_date


def test_clean_isbn13_strips_and_validates():
    assert clean_isbn13("978-0-06-231609-7") == "9780062316097"
    assert clean_isbn13("9798217187492") == "9798217187492"
    assert clean_isbn13("not an isbn") is None
    assert clean_isbn13(None) is None
    assert clean_isbn13("") is None


def test_parse_us_date():
    assert parse_us_date("7/15/2026") == date(2026, 7, 15)
    assert parse_us_date("07/15/2026") == date(2026, 7, 15)
    assert parse_us_date("") is None
    assert parse_us_date("TBD") is None
    assert parse_us_date(None) is None


from app.services.release_sources.libraryreads_source import LibraryReadsSource

_LR_CSV = (
    'Month,"Author (Last, First)",Title,Publisher,ISBN,Pub Date,Top Pick,HoF,Debut,Bonus Pick,Book Clubs,Genre,Annotation,Nominator/Library\n'
    '6/2026,"Clear, James",Atomic Habits Redux,Avery,9780062316097,6/15/2026,Top Pick,,,,Book Clubs,Self-Help,"A great pick.","Mara Bandy Fass, Champaign PL"\n'
    '6/2026,"Doe, Jane",A Hall Of Famer,Tor,9781250000000,6/2/2026,,HoF,,,,Fantasy,"Older buzz.","Sam, LSCL"\n'
    '5/2026,"Past, Author",Last Month Title,Penguin,9789999999999,5/1/2026,,,,,,Fiction,"Wrong month.","X"\n'
)


def test_libraryreads_parse_filters_month_and_maps_fields():
    src = LibraryReadsSource()
    titles = src._parse_csv(_LR_CSV, month="6/2026")
    assert len(titles) == 2
    top = next(t for t in titles if t.title == "Atomic Habits Redux")
    assert top.source == "libraryreads"
    assert top.isbn_13 == "9780062316097"
    assert top.release_date.isoformat() == "2026-06-15"
    assert top.author_name == "James Clear"
    assert top.blurb == "A great pick."
    assert top.blurb_credit == "Mara Bandy Fass, Champaign PL"
    assert top.genre == "Self-Help"
    assert top.is_featured is True
    assert top.source_url == "https://libraryreads.org"


def test_libraryreads_rejects_unexpected_headers():
    bad = "Foo,Bar\n1,2\n"
    src = LibraryReadsSource()
    try:
        src._parse_csv(bad, month="6/2026")
        assert False, "expected ValueError on bad headers"
    except ValueError as e:
        assert "header" in str(e).lower()


from app.services.release_sources.lj_prepub_source import LJPrepubSource

_LJ_CSV = (
    "Title,Author,EAN,Publisher Name,PubDate,List Price,BISAC Category Description,Series\n"
    '"The Gothic Hour","Smith, Ada",9798217187492,William Morrow,8/4/2026,27,Fiction / Gothic,Night Series\n'
    '"No Date Book","Jones, Bo",9780062316097,Berkley,,18.99,Fiction / Thrillers,\n'
)


def test_lj_prepub_parse_maps_columns_and_optional_series():
    src = LJPrepubSource()
    titles = src._parse_csv(_LJ_CSV)
    assert len(titles) == 2
    g = next(t for t in titles if t.title == "The Gothic Hour")
    assert g.source == "lj_prepub"
    assert g.isbn_13 == "9798217187492"
    assert g.author_name == "Ada Smith"
    assert g.publisher == "William Morrow"
    assert g.release_date.isoformat() == "2026-08-04"
    assert g.list_price == 27.0
    assert g.genre == "Fiction / Gothic"
    assert g.is_featured is False

    nd = next(t for t in titles if t.title == "No Date Book")
    assert nd.release_date is None
    assert nd.is_date_exact is False


def test_lj_prepub_rejects_unexpected_headers():
    src = LJPrepubSource()
    try:
        src._parse_csv("A,B\n1,2\n")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "header" in str(e).lower()


from app.services.release_sources.base import normalize_author_name


def test_normalize_author_name():
    assert normalize_author_name("Smith, Jane") == "Jane Smith"
    assert normalize_author_name("Smith, Jane Q.") == "Jane Q. Smith"
    assert normalize_author_name("Madonna") == "Madonna"
    assert normalize_author_name("") is None
    assert normalize_author_name(None) is None
