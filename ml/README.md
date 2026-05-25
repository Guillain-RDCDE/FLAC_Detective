# FLAC Detective — ML pipeline

Workflow for training a CNN classifier ("authentic FLAC" vs "MP3-transcoded FLAC")
that gets integrated as Rule 12 in the scoring pipeline.

## Pipeline overview

```
[Local Windows]                       [Hetzner GPU]
                                       
D:\FLAC                                /root/flac-detective-ml/
   |                                       |
   v                                       v
build_dataset.py  --(manifest)--->  dataset/authentic/   <-- rsync upload
                                          |
                                          v
                                   generate_transcodes.py
                                          |
                                          v
                                   dataset/transcoded/
                                          |
                                          v
                                   extract_features.py
                                          |
                                          v
                                   features/{mel_spec.npy, labels.npy}
                                          |
                                          v
                                   train.py  --(checkpoints)--> models/
                                          |
                                          v
                                   export_torchscript.py
                                          |
                                  (download model_v1.pt)
                                          |
                                          v
[Local]                                                                
   |
   v
src/flac_detective/models/cnn_v1.pt
   |
   v
Rule12MLClassifier  (new scoring rule)
```

## Files

- `build_dataset.py` — Scans `D:\FLAC`, identifies certified-authentic FLACs via
  ripping logs (EAC / XLD / CUERipper) or Audiochecker verdicts (`CDDA (100%)`),
  outputs a JSON manifest of file paths.
- `generate_transcodes.py` — On Hetzner: for each authentic FLAC, generates
  MP3 (128/192/256/320 kbps), AAC (192/256), Opus (128) transcodes, then
  re-encodes each back to FLAC. Output: `dataset/transcoded/<bitrate>/<file>.flac`.
- `extract_features.py` — Computes mel-spectrograms (128 mel bins, ~10s segments)
  for each file in `dataset/`, stores as `.npy` arrays for fast batched loading.
- `train.py` — Trains a small CNN (ResNet-18 or EfficientNet-B0) on the
  binary classification task. Saves checkpoints to `models/`.
- `export_torchscript.py` — Loads the best checkpoint, exports to TorchScript
  (`.pt`) for runtime use without PyTorch's full Python dependency tree.

## Reproducibility

All scripts seed with 42, write configs alongside outputs, and log to stdout.
The full pipeline is meant to be re-runnable end-to-end from a fresh checkout.

## Hardware target

Hetzner GPU server: RTX 4000 SFF Ada Gen (20 GB VRAM). Training budget capped
at 10 GB VRAM to coexist with concurrent Whisper inference (other service on
the same host).
