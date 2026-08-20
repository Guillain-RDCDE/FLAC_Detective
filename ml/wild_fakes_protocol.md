# Using Provir's 53 wild files — as a test of our taxonomy, not as seed rows

Jamie Dodd has offered the 53 wild files behind Provir's only real-world row. They
are owner-ruled, and the basis is **listening plus purchase provenance**, not his
engine's output.

His framing is better than the obvious one and is adopted here:

> I think they are worth more to you as a scoring set against your basis taxonomy
> than as seed rows.

## Why not simply ingest them

Absorbing 53 adjudicated files would give this project a wild row it did not earn,
resting on someone else's ears and someone else's records. The number would be
real and the provenance would be borrowed, and the first person to ask "who
decided?" would get an answer that is not ours.

Worse, it would waste them. We have exactly one thing they can test that nothing
else can.

## What they actually test

`ml/wild_fake_ledger.py` accepts four bases and refuses a `fake` label without
one:

| basis | what it claims |
|---|---|
| `tracker_staff` | a private tracker's staff adjudicated it a transcode |
| `provenance_pair` | a verified-lossless copy of the same master exists and differs |
| `uploader_admission` | the uploader or distributor acknowledged the source |
| `listening` | adjudicated by ear, by someone competent |

That taxonomy has never met real material. It was written from first principles in
an afternoon, and the honest question about it is whether four categories are
enough, whether they are separable in practice, and whether `listening` is doing
too much work.

His 53 are the first set that can answer that, because they arrive with a basis
already attached — and it is a *compound* one. "Listening plus purchase
provenance" does not fit cleanly in either `listening` or `provenance_pair`, which
is itself the first finding: the taxonomy may need bases to be a set rather than a
single value.

## The procedure

1. Ingest with `add`, recording his description verbatim as the source.
2. Adjudicate each with the basis **he** states, not with ours re-derived — the
   point is to test whether our vocabulary can express his.
3. Record every basis that will not fit. Those are the taxonomy's defects.
4. Only then look at what the engine says about them, and report it over the
   adjudicated set as `status` does — with the count, and with the reminder that a
   borrowed corpus measures borrowed ground truth.

## What this does not do

It does not close the wild-fakes gap. This project still has **zero** files it
adjudicated itself, and a scoring set obtained from the other party to a
comparison cannot be the evidence that the comparison was fair. The gap closes
when someone here rules on material this project found.

---

## STAMPED 2026-08-20 — the 53 arrived, and the test above ran on paper

The delivery was a **feature ledger with no audio and no byte-binding**
(archived in `ml/exchange/`), so step 1 of the procedure above could not run at
all — and the taxonomy test happened anyway, at the schema level. Three defects
found and repaired, pinned by `tests/test_wild_fake_ledger.py`: no
`owner_attestation` basis (his strongest tier had no name here), no way to
record a ruling made **by extension** (his CD3: 5 examined, 19 ruled →
`--scope group` + mandatory note), and no way to record a selection **pipeline**
(metric-shortlisted then eye-ruled → `+`-chained selections). The prediction in
this document — "the taxonomy may need bases to be a set" — was directionally
right and landed on the *selection* field first.

The wild-fakes gap is exactly as open as before, which is why the section below
now exists.

## The c411 pipeline — closing the gap with rows we rule on ourselves

The target is **30 referee-grade rows**, not 30 files, per the ledger's own
warning. The source is the private tracker where this project holds an account,
because its moderation produces exactly the evidence class we lack:
staff-adjudicated transcode reports (`tracker_staff`, referee-grade), attached
to files that were really distributed as lossless.

Per file, manual by design (no scraping — collection is a person reading a
moderation thread, and the tracker's terms stay respected):

1. Find a staff adjudication: a "trumped for transcode" verdict or a moderation
   thread ruling a torrent lossy-sourced. **The thread found us, or a systematic
   sweep of the moderation log found it — never a spectrogram browse.** Record
   which, honestly: `--selection reported` (someone else flagged it) or
   `--selection systematic` (every entry of a defined moderation-log window).
2. Save the adjudication evidence — permalink plus a screenshot of the staff
   verdict — under `Temp/wild_evidence/<sha-prefix>/` (gitignored: the evidence
   contains usernames and tracker identifiers that are not ours to publish; the
   committed ledger carries the hash and the basis, never the screenshot).
3. Register and adjudicate:

       python ml/wild_fake_ledger.py add <file> --source "c411 <permalink> <date>"
       python ml/wild_fake_ledger.py adjudicate <sha> --label fake \
           --basis tracker_staff --selection reported --scope file \
           --note "<permalink>"

4. Wild GENUINE controls enter by the same door, from the same place: rips with
   clean ripper logs and AccurateRip verification on the same tracker,
   `--label genuine --basis provenance_pair --selection systematic`. A wild row
   without wild controls prices recall and hides the false-alarm side, which is
   the asymmetry Provir just withdrew a number over.
5. `status` before quoting anything: it prints the referee/selection
   cross-tabulation unasked, and under 30 fakes it says so.

What the engine says about these files is recorded by `add` and never becomes
the label — the oldest way to produce a confident wrong number stays closed.
