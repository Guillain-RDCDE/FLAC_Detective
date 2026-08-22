r"""idem_phase_search.py — the idem read at the RIGHT grid phase (2026-08-21 22:25 finding: the fixed point is grid-locked).

FINDING (scratch, one file, two probes): R_b03_16k of the SAME decoded MP3 under the same probe reads 4.33 at sample offsets
0 / 576 / 1152 / 2304 and ~7.0 at ANY other offset — one sample off and the file "reads lawful". Period 576 (one MDCT granule),
tolerance zero. An ffmpeg decode of a TAGGED LAME file is at phase 0; an UNTRIMMED decode (headerless file, or any decoder that
does not strip the encoder delay — which is most of them) is at phase 529 (1105 = 576 + 529 samples of extra lead-in). A
trimmed/re-wrapped/DAW-edited wild file is at an unknown phase. Every fixture row we hold was measured at phase 0 = best case.

THIS TOOL: for a file and a probe, (1) reads the three canonical phases {0, 529, 47} cheaply, (2) optionally searches all 576
phases on a SHORT excerpt using d1 only (one probe encode per phase), then (3) reports the full R at the best phase beside the
phase-0 read. Use it to re-check any claim built on "X reads lawful-like under probe Y" — that sentence is only true if it
holds at the best phase.

  python idem_phase_search.py FILE --probe mp3_320 [--full] [--secs 30] [--search-secs 4]
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import idemlib as IL  # noqa: E402
from fhgacm_idem_row import idem_any, one_pass_any  # noqa: E402

CANON = [0, 529, 47]   # trimmed ffmpeg decode · untrimmed decode (1105 mod 576) · decoder-delay-only decode (576-529)


def d1_only(pcm, probe, scratch):
    p1 = one_pass_any(pcm, probe, scratch)
    d = IL.dist(IL.mono(pcm), IL.mono(p1))
    return d.get('b03_16k') if d else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--probe', default='mp3_320')
    ap.add_argument('--secs', type=int, default=30)
    ap.add_argument('--search-secs', type=int, default=4)
    ap.add_argument('--full', action='store_true', help='search all 576 phases on a short excerpt (d1 only), then full R at the best')
    ap.add_argument('--step', type=int, default=1)
    a = ap.parse_args()
    scratch = os.path.join(HERE, 'work', 'scratch', 'phase_%d' % os.getpid())
    os.makedirs(scratch, exist_ok=True)
    pcm = IL.excerpt_s16(a.file, secs=a.secs)
    print('file: %s  probe: %s  excerpt %ds' % (os.path.basename(a.file), a.probe, a.secs))
    reads = {}
    for k in CANON:
        r = idem_any(pcm[k * 4:], a.probe, scratch)
        reads[k] = r['R_b03_16k']
        print('  phase %3d  R=%.3f' % (k, reads[k]))
    best_k = min(reads, key=lambda k: reads[k])
    if a.full:
        short = pcm[: IL.SR * 4 * a.search_secs + 576 * 4 * 3]
        cand = {}
        for k in range(0, 576, a.step):
            v = d1_only(short[k * 4:], a.probe, scratch)
            if v is not None:
                cand[k] = v
        kbest = min(cand, key=lambda k: cand[k])
        print('  full search (%ds excerpt, d1 only, step %d): best phase %d  d1=%.4g  (phase-0 d1=%.4g)' % (a.search_secs, a.step, kbest, cand[kbest], cand.get(0, float('nan'))))
        r = idem_any(pcm[kbest * 4:], a.probe, scratch)
        reads[kbest] = r['R_b03_16k']
        print('  phase %3d  R=%.3f  (full R at the searched phase)' % (kbest, reads[kbest]))
        best_k = min(reads, key=lambda k: reads[k])
    print('BEST phase %d  R=%.3f   | phase-0 R=%.3f' % (best_k, reads[best_k], reads[0]))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
