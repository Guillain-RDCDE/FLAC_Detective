Provir -> Guillain, 2026-09-02

fd-exchange-v3-setB-2026-08-31.zip
  Set B as described on 31 August: 35 sources x 8 classes = 280 files, 60-second excerpts,
  44.1 kHz / 16-bit WAV. Zip is STORE mode (no compression), so the bytes inside are exactly
  the bytes MANIFEST.sha256 describes. Manifest self-hash b0bb5410cde39caa3ac33ecd0254275a1ff750accd3364b98d5072607946eaea
  (the one you already hold). Verify: awk '{print $1 " " $2}' MANIFEST.sha256 | sha256sum -c
  Zip sha256 in SHA256SUMS.txt.

setA_r2_verdicts.csv.sha256 / .ots
  The missing link you rebuilt: the hash file the .ots seals (bare hex + CRLF), and the proof.
