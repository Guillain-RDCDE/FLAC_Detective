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
