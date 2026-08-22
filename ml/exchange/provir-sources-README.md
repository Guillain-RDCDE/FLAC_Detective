# Sweep sources - the fixture format for returned cells

src_elec.wav / src_class.wav / src_pop95.wav - 60 s each, 16-bit 44.1 kHz stereo, plain RIFF (no LIST chunk).
These are the three sources behind every cell in our emitter register (3 sources x 3 rates per emitter).

To return a column for an encoder we do not hold: encode each source at 128, 192 and 320 kbps CBR
(and any VBR setting you want, labelled by its nominal rate), name the outputs
  <source>_<rate>.<ext>   e.g. elec_128.m4a, class_192.m4a, pop95_320.m4a
and drop them in a folder named for the encoder + build (e.g. fdkaac_1.0.0_debian/) beside this README.
State the exact command line and the binary identity (version, sha256) in a NOTE.txt in that folder.
A rate is taken only when all three sources are present; every returned file is decoded, rate-checked and
measured by the same instrument as our own cells.
