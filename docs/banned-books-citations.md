# Banned Books Week booklist — source verification

This is the sourcing behind the "banned/challenged" notes shown to patrons on the Banned
Books Week reading list. The list is built from ten candidate classics already in the
catalog; each candidate was checked individually before being trusted, because a note on
this list is a factual claim published under the library's name.

**If you're maintaining a fork of this codebase:** the booklist feature seeds
`program_booklist.note` from the surviving entries below. If you add or swap titles, verify
them the same way before trusting a note text — banned-books trivia circulates widely online
and a large share of it does not survive checking against a primary source (see "Dropped
titles" below for concrete examples of claims that looked solid and weren't). Every row here
reflects a source that was actually opened and read, not a title or search-snippet
characterization.

Grades: `[P]` primary confirmed (the record itself, or a scholarly/news account citing it
specifically) · `[C]` circumstantial (credible secondary account, no underlying record in
hand) · `[X]` unverified — checked, and did not hold up. `[X]` rows do not get a booklist
entry; they're kept here so the same disproven claim doesn't get re-added by a future editor
without re-checking it.

## Citation table

| Title | Grade | What happened, one line | Source URL | Fetched |
|---|---|---|---|---|
| Adventures of Huckleberry Finn | `[P]` | Removed from required reading in Duluth, MN public schools, Feb. 2018, over racial slurs in the text (kept in school libraries for independent reading) | https://newscut.mprnews.org/2018/02/huck-finn-boo-tossed-off-duluth-schools-required-reading-list | 2026-08-04 |
| The Wonderful Wizard of Oz | `[C]` | Detroit Public Library director publicly called the Oz series valueless in 1957 and continued a decades-old non-purchase policy for children's collections; he himself called it "selection," not banning | https://en.wikipedia.org/wiki/Ralph_Ulveling | 2026-08-04 |
| Ulysses | `[P]` | US Customs seized the imported Paris edition in 1932; federal judge ruled it not obscene Dec. 6, 1933, lifting the US import ban (customs/obscenity case, not a library challenge) | https://www.courtlistener.com/opinion/2250768/united-states-v-one-book-called-ulysses/ | 2026-08-04 |
| Leaves of Grass | `[P]` | Boston's DA threatened the publisher with obscenity prosecution in March 1882 over specific poems; publisher dropped the book rather than fight it, Whitman refused to cut the poems and found a new publisher | https://whitmanarchive.org/item/encyclopedia_entry211 | 2026-08-04 |
| The Call of the Wild | `[X]` | not sustained — see below | — | 2026-08-04 |
| Alice's Adventures in Wonderland | `[X]` | not sustained — see below | — | 2026-08-04 |
| Frankenstein | `[X]` | not sustained — see below | — | 2026-08-04 |
| On the Origin of Species | `[X]` | not sustained — see below | — | 2026-08-04 |
| Uncle Tom's Cabin | `[P]` | Rev. Samuel Green, a free Black preacher in Dorchester County, MD, convicted April 1857 for possessing the book, sentenced to 10 years in the Maryland Penitentiary (criminal prosecution under antebellum MD law, not a library challenge) | https://stampedes.dickinson.edu/document/annapolis-md-gazette-sam-green-and-uncle-toms-cabin-september-2-1858 | 2026-08-04 |
| Moby Dick | `[X]` | not sustained — see below | — | 2026-08-04 |

## Notes to seed `program_booklist.note` (surviving titles only)

**Adventures of Huckleberry Finn** (432 chars, counted with `len()`)
```
Removed from required reading in Duluth, MN public schools, Feb. 2018, after long-standing complaints about racial slurs in the text. Curriculum director Michael Cary said other novels could meet the same standards without students feeling humiliated or marginalized; copies stayed in school libraries for independent reading. Source: https://newscut.mprnews.org/2018/02/huck-finn-boo-tossed-off-duluth-schools-required-reading-list
```

**The Wonderful Wizard of Oz** (360 chars, counted with `len()`)
```
Detroit Public Library director Ralph Ulveling told a 1957 state library conference the Oz series had "no value" and promoted "negativism," continuing a decades-old policy of not buying new copies for children's collections. He called it "selection," not banning, but the decision drew national controversy. Source: https://en.wikipedia.org/wiki/Ralph_Ulveling
```
*Correction from adversarial review:* an earlier draft of this note said the policy "held
until 1972." That date is real in the sense that it is repeated everywhere (wkfr.com,
openculture.com, and others all state it), but neither of those pages cites anything for it,
and it traces to no source I could open and verify — wkfr.com cites openculture.com, and
openculture.com cites nothing. Removed the date rather than publish an unsourced specific
claim. If a future editor finds a citable primary source for the end date (a 1972 press
account or a Detroit Public Library board record would do it), it can go back in.

*Checked and ruled out as a stronger source:* Mozert v. Hawkins County Board of Education,
827 F.2d 1058 (6th Cir. 1987) is a real, published circuit opinion about parents challenging
a public-school reading series on religious grounds, and would have been a much stronger
[P] source than the Detroit story if it named Oz. It doesn't. Opened the full opinion text
directly (via a Leagle.com-hosted PDF) and searched it: no mention of "Oz," "Wizard of Oz,"
or "Baum" anywhere in the document. The objected-to material the Mozert plaintiffs actually
named is Macbeth, The Lottery, and several fairy tales (Cinderella, Snow White, Rumpelstiltskin,
Goldilocks, Thumbelina) plus stories involving magic and witchcraft — not Oz. Kept the Detroit
story; this search does not need to be re-run.

**Ulysses** (398 chars, counted with `len()`)
```
US Customs seized the Paris edition of Ulysses when Random House imported it in 1932 to force a test case against the US import ban. Federal judge John M. Woolsey ruled Dec. 6, 1933 that the novel was not obscene, lifting the ban. A customs seizure and federal obscenity ruling, not a library challenge. Source: https://www.courtlistener.com/opinion/2250768/united-states-v-one-book-called-ulysses/
```
*Sourcing gap, closed:* a first pass cited Wikipedia's account of the case because the
opinion itself, on Justia, 403'd on a plain HTTP fetch. Justia never did open. Instead opened
the opinion via CourtListener (courtlistener.com/opinion/2250768), which required a real
browser render, not a plain fetch — the same CourtListener URL blank-403'd on a first plain
fetch attempt and only returned content through a browser tool. Read the full "Combined
Opinion by Woolsey" text directly: District Court, S.D. New York, decided Dec. 6, 1933,
5 F. Supp. 182. Confirmed verbatim: "The motion for a decree dismissing the libel herein is
granted, and, consequently, of course, the government's motion for a decree of forfeiture and
destruction is denied," and "'Ulysses' may, therefore, be admitted into the United States."
Grade and source URL above now point at the primary record itself, opened and read in full.

**Leaves of Grass** (353 chars, counted with `len()`)
```
Boston District Attorney Oliver Stevens threatened publisher James Osgood with obscenity prosecution in March 1882 over specific poems in Leaves of Grass. Whitman refused to cut them; Osgood dropped the book under the threat, and Whitman had it reprinted by a Philadelphia publisher instead. Source: https://whitmanarchive.org/item/encyclopedia_entry211
```
*Sourcing gap, closed:* a first pass cited a University of Toronto exhibit because the
Whitman Archive's own encyclopedia entry 403'd (Cloudflare challenge page) on a plain HTTP
fetch. A browser-rendered fetch got through and returned the actual entry: "Stevens, Oliver
(b. 1825)" from *Walt Whitman: An Encyclopedia* (ed. Cummings & LeMaster, Garland Publishing,
1998), by Joseph P. Hammond — a citable scholarly reference work, not a student exhibit.
It confirms the March 1, 1882 letter, DA Oliver Stevens, pressure from State AG George Marston
and Anthony Comstock, and Osgood declining to fight the threat. One detail differs between the
two sources: the Toronto exhibit lists "I Sing the Body Electric" and "Spontaneous Me" among
the targeted poems; the Whitman Archive entry instead names "A Woman Waits for Me," "To a
Common Prostitute," and "The Dalliance of the Eagles." The note above doesn't name specific
poems, so this discrepancy doesn't affect it, but it's flagged here rather than silently
dropped. Source URL above now points at the primary encyclopedia entry, opened and read in full.

**Uncle Tom's Cabin** (393 chars, counted with `len()`)
```
Rev. Samuel Green, a free Black preacher in Dorchester County, MD, was convicted at the April 1857 term for possessing a copy of Uncle Tom's Cabin and sentenced to 10 years in the Maryland Penitentiary. A criminal prosecution under antebellum MD law, not a library challenge. Source: https://stampedes.dickinson.edu/document/annapolis-md-gazette-sam-green-and-uncle-toms-cabin-september-2-1858
```

## Dropped titles and why

**The Call of the Wild — `[X]`.** The most commonly repeated claim (burned in the 1933 Nazi
book burnings) is directly contradicted by the US Holocaust Memorial Museum's own Jack London
page, opened and read in full: "The Nazis burned this and other socialist-leaning works in
1933, but did not, however, ban London's adventure stories" — Call of the Wild is an adventure
story; the works actually burned were his explicitly political novels (The Iron Heel, Martin
Eden, The Star Rover). A second claim (Italy and Yugoslavia banned it in 1929 as "too radical")
traces through a chain of listicles back to a vague, uncited reference to "the University of
Pennsylvania." I checked the actual UPenn "Banned Books Online" exhibit directly — it has no
entry for The Call of the Wild and does not support the claim. Source: https://encyclopedia.ushmm.org/content/en/article/jack-london (opened, contradicts the claim)

**Alice's Adventures in Wonderland — `[X]`.** The widely repeated "banned in Hunan Province,
China, 1931" story does not hold up. The library blog that carries it (J. Willard Marriott
Library) supplies no citation for the claim and had to silently correct the province name after
a reader flagged it as historically nonexistent. A more detailed piece I opened traces the
actual 1931 document by General/Governor Ho Chien — an essay on school curricula that never
names Alice at all — and notes Alice had a Chinese translation and even a fan-written Chinese
sequel circulating at the time the "ban" supposedly took effect. No primary record of an actual
prohibition was found. Source: https://still-she-haunts-me-phantomwise.tumblr.com/post/50384306263/was-alice-in-wonderland-really-banned-in-china (opened, debunks the claim)

**Frankenstein — `[X]`.** No specific, verifiable incident found. A claim that it was banned in
apartheid South Africa in 1955 and a claim that Souderton, PA schools dropped it as "smut"
both appear only in secondhand listicles (Quora, Prezi, undergrad library blog posts) with no
primary record locatable. PEN America's Halloween-themed banned-books piece, which looked like
the best lead, returned a 403 and could not be opened, so it is not used as support.

**On the Origin of Species — `[X]`.** This title has a strong general reputation as "one of the
most banned books ever," and that reputation does not hold up under checking. The recurring
"Tennessee banned it 1925–1967" claim conflates two different things: the 1925 Butler Act banned *teaching* evolution in public schools, not the book itself
— and Tennessee's own state-mandated biology textbook of the era (Hunter's *A Civic Biology*)
actually taught evolution, undercutting the idea that the book was suppressed. A claim that
Trinity College, Cambridge excluded the book from its library (dates given inconsistently as
1859 or 1895 across sources) could not be corroborated anywhere in the academic literature on
Whewell or Trinity College Library that I searched. Claims of 1935 Yugoslavia / 1937 Greece bans
appear only as bare, uncited assertions repeated across secondary listicles (including ALA's own
OIF blog, which gives no location or citation beyond "banned in 1895"). No specific,
primary-backed incident survived.

**Moby Dick — `[X]`.** Same pattern as Origin of Species: a strong general "banned classic"
reputation that does not survive checking. The specific claim in circulation — that Moby-Dick was one of 32 books the Lindale, TX school board
banned from Advanced Placement English in 1996 — could not be confirmed. The one contemporary
news account I could actually open and read (a Sept. 1997 Virginia Pilot piece via the VT news
archive) names The Scarlet Letter specifically as the book pulled from Lindale's AP reading list,
and separately lists Moby-Dick among generally "challenged" classics nationally — without tying
it to Lindale or any other specific place and year. Every source claiming otherwise is a listicle
without its own citation. Source checked: https://scholar.lib.vt.edu/VA-news/VA-Pilot/issues/1997/vp970921/09110869.htm (opened, does not support the Moby-Dick/Lindale pairing)
