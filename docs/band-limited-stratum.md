# The band-limited stratum does not exist in the free archives

*Guillain d'Erceville — 1 September 2026*

A transcode detector's most useful question is not "can it catch a 320 kbps MP3".
It is "what does it do to an honest recording that happens to look like one".
The population that answers it is **band-limited authentic material**: real
recordings whose content genuinely stops somewhere around 14–16 kHz, because of
the microphone, the tape, the transfer chain or the era — not because an encoder
threw the top octave away.

Every serious benchmark needs that stratum. We went looking for it in the free
archives, and it is not there.

## The count

Building a blind exchange set, we read 199 candidate archive items before
downloading anything, and measured 68 authentic sources end to end. **Exactly one
of the 68 measured as band-limited.** Every other transfer carried noise up to
Nyquist. That is not an accident of our filter: modern digitisation of old
material is done with modern converters, and what reaches the archive is a
full-band file containing old, dull audio — which is a completely different thing
from a band-limited file, and reads differently to every spectral instrument.

So the stratum has to be **constructed**, and once it is constructed it has to be
**declared**, because a set containing synthetic roll-off is no longer a set of
found objects. In our exchange set, 12 of 36 sources carry a declared six-section
two-pole roll-off at 14 kHz; `detect_cutoff` reads them at 15,250–15,500 Hz. The
counterpart wrote back that the disclosure was the condition on which the round
was worth running.

## What the stratum found, on our own engine

We took 44 authentic sources that our engine had already read as AUTHENTIC — none
of them in the shipped set — and applied that roll-off and nothing else. No
encoder, no re-quantisation, no resampling. The only change to each file was the
missing top octave.

**Fifteen of the 44 were convicted.** Twenty-two more were signalled. Band-limiting
an honest file made our detector call it a fake one time in three.

The mechanism was not the classifier and not a threshold that had drifted. Rule 15
looks for a dead side channel above ~10 kHz, which is what joint-stereo coupling
leaves behind, and it tested the mid and the side channel against the **same
absolute bar**. In real music the side channel already sits 10–20 dB below the mid
at the top of the band. A roll-off finishes the job, both channels fall under the
bar, and a stereo-image witness that has nothing to testify about testifies
anyway — supplying the second, "independent" evidence family that a conviction
requires.

The repair was not new code. The rule already carried a domain guard, with the
correct reasoning written in the comment beside it, set at 12 kHz — below the
region where the artefact lives. Raised to 17 kHz, inside the measured gap between
the lowest genuine arm (19,250 Hz) and the band-limited controls (median 15,500):

| | before | after |
|---|---|---|
| band-limited controls convicted | 15 / 44 | **4 / 44** |
| our own genuine files convicted | 1 / 36 | **0 / 36** |
| convictions lost across six codec arms | — | **0** |

Two more elaborate repairs were written, implemented and **refused by their own
pre-registered clause** before this one shipped: one rested on a diagnosis that
measurement contradicted, the other bought the artefact's removal at 0.10 of AUC
against a 0.03 budget.

## The part that is not fixed

The four survivors all carry the same pair of evidence families: `cnn` and
`spectral`. Rule 12 is a classifier over a mid/side mel-spectrogram. On a file
whose top octave has been removed, the dominant feature of that spectrogram is the
same roll-off the spectral rules read.

So the corroboration barrier — the mechanism that exists precisely to stop one
observation from convicting twice — **counts evidence families without asking
whether they looked at the same thing.** It was built by grouping rules once, at
design time, by what each rule measures in general. Whether two families are
independent *on a particular file*, under a particular condition, is a question it
has never asked.

That is general. It touches every pair of rules, not the one pair we can currently
price. We have registered the repair with its populations and its refusal clause
before measuring it, including the bound that makes it hard: a guard that collapses
`cnn` and `spectral` on a low cutoff cannot tell a band-limited authentic file from
an honest 128 kbps transcode, because both live around 15–16 kHz — and on the
low-rate transcode that pair is exactly how a *correct* conviction is made.

## Two things worth taking away

**If your benchmark comes from the free archives, it has a hole shaped like this.**
Not a small hole: a third of our false convictions lived in a population our corpus
could not contain. You will not find that stratum by sampling harder. You have to
build it and say so.

**"Two independent families agreed" is a claim about the file, not about the
rules.** Independence established at design time can dissolve on a particular
input, and a barrier that counts names rather than observations will not notice.
Ours did not.

---

*FLAC Detective is at <https://github.com/Guillain-RDCDE/FLAC_Detective>. The
measurements above are in `ml/exchange/`, each with its criteria and bounds
committed before the numbers that answer them.*
