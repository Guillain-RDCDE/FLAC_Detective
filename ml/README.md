# FLAC Detective — ML pipeline

Reproducible workflow that trains a binary classifier ("authentic FLAC" vs
"MP3-transcoded FLAC") and bundles it into the package as Rule 12. The
current production model (`cnn_v2.ts.pt`, shipped in v0.11.0) is a fine-tuned
ResNet-18 that reaches **balanced accuracy 0.81** and **specificity 80 %** on
a held-out test set.

This document records both the pipeline as it stands today **and** the four
training failures that led to the working configuration. Audio classification
on small imbalanced datasets is full of footguns — keeping the lessons
visible saves the next person (you, in three months) from re-stepping on the
same mines.

---

## Pipeline overview

```
[Local Windows]                       [Hetzner GPU]

D:\FLAC                                /root/flac-detective-ml/
   |                                       |
   v                                       v
build_dataset.py  --(manifest)--->  dataset/authentic/   <-- trim + upload
   |
   v
trim_for_upload.py (30 s per file)
   |
   v
ml/trimmed/  --(tar | ssh)-->  dataset/authentic/
                                          |
                                          v
                                   generate_transcodes.py
                                          |
                                          v
                                   dataset/transcoded/
                                   (10 codecs × N files)
                                          |
                                          v
                                   extract_features.py
                                          |
                                          v
                                   features/dataset.npz
                                          |
                                          v
                                   train.py
                                          |
                                          v
                                   models/cnn_v2/best.pt
                                          |
                                          v
                                   export_torchscript.py
                                          |
                                  (download cnn_v2.ts.pt)
                                          |
                                          v
[Local]
   |
   v
src/flac_detective/models/cnn_v2.ts.pt
   |
   v
Rule12MLClassifier (12th scoring rule)
```

---

## Files

| File | Purpose |
|---|---|
| `build_dataset.py` | Scan `D:/FLAC` for FLACs with strong authenticity proof (EAC / XLD / CUERipper logs, or Audiochecker `CDDA (100%)` verdicts). Emit a JSON manifest. |
| `trim_for_upload.py` | Extract a 30-second clip from the middle of each manifest file, re-encode at FLAC max-compression. Reduces upload size ~90 %. |
| `upload_to_hetzner.py` | Generate a file list for tar streaming to the training server. |
| `setup_hetzner.sh` | One-time provisioning on the GPU server (Python venv, PyTorch CUDA, librosa, torchvision). |
| `generate_transcodes.py` | For each authentic FLAC, produce 10 transcoded copies via ffmpeg: MP3 CBR 128/192/256/320, MP3 VBR V0/V2, AAC 192/256, Opus 128, Vorbis q5. Re-encode each back to FLAC ("fake FLAC"). |
| `extract_features.py` | Compute 128-mel-bin log-power spectrograms for a 10 s middle clip of every file. **Sample rate is 44 100 Hz** — see lessons below. |
| `train.py` | Train a ResNet-18 wrapper, save best checkpoint by `balanced_acc`. |
| `export_torchscript.py` | Trace the best checkpoint to TorchScript for runtime use. |
| `run_pipeline.sh` | Chain the four GPU-side stages (transcode → features → train → export). |

---

## The current production model (v2, shipped in v0.11.0)

- **Architecture**: ResNet-18 pretrained on ImageNet. First conv layer
  adapted from 3-channel RGB input to 1-channel mel input by averaging RGB
  weights. Final FC replaced with a binary head.
- **Input**: (1, 1, 128, 862) — a 10-second mel-spectrogram at 44.1 kHz,
  128 mel bins, 2048 FFT, hop 512.
- **Training data**: 2237 authentic FLACs × 10 codec/bitrate transcodes
  + 2237 authentics = 24 451 samples. Stratified 70/15/15 train/val/test.
- **Optimisation**: AdamW (lr 3e-4, weight decay 1e-4), `WeightedRandomSampler`
  to balance batches, plain CrossEntropyLoss, SpecAugment (freq mask 15,
  time mask 20, 2 masks).
- **Selection criterion**: **`balanced_acc`** = mean of per-class recalls.
  Robust to imbalance, cannot be gamed by predicting only the majority class.
- **Test metrics** (held-out 3667 samples):

  | Metric                        | Value |
  |-------------------------------|-------|
  | accuracy                      | 82.4% |
  | balanced_acc                  | 0.811 |
  | precision (transcoded)        | 97.6% |
  | recall (transcoded)           | 82.7% |
  | recall (authentic) = specificity | **80.0%** |
  | tp / fp / fn / tn             | 2756 / 68 / 578 / 265 |

- **Runtime size**: 43 MB TorchScript, bundled in the wheel.

---

## Lessons from four failed attempts

The path to v2 was not direct. Each failure taught a specific lesson.

### Attempt #1 — model collapses to "always predict authentic"

**What was tried**: Focal loss with per-class `alpha = [n/(2·c_authentic),
n/(2·c_transcoded)]` *on top of* a `WeightedRandomSampler` that already
rebalances training batches.

**What happened**: The double class-balancing massively up-weighted the
rare class. The cheapest way to minimise the loss became "always predict
authentic". Test recall on transcoded files collapsed to **0**.

**Lesson**: Pick **one** mechanism to handle class imbalance, not two.
Either the sampler **or** the loss weighting, not both.

### Attempt #2 — model collapses to "always predict transcoded"

**What was tried**: Dropped the focal loss. Kept `WeightedRandomSampler` +
plain CrossEntropyLoss. Selected the best checkpoint on validation F1
(computed on the transcoded class).

**What happened**: With a 1:10 authentic:transcoded test ratio, F1-on-class-1
naturally peaks at "always predict transcoded" (recall=1, precision ≈ 0.91,
F1 ≈ 0.95). The training loop happily saved that degenerate model as
"best".

**Lesson**: **F1 on a single class is not a robust selection metric on
imbalanced data.** Use balanced accuracy = mean of per-class recalls.

### Attempt #3 — oscillation, no convergence

**What was tried**: Switched the selection metric to `balanced_acc`, lowered
LR from 1e-3 to 3e-4, used the original custom CNN architecture (5 conv
blocks + GAP + FC, ~700 K parameters).

**What happened**: The val metric oscillated wildly between
"all-authentic" (recall_auth=1.0, recall_trans=0.0) and "all-transcoded"
(opposite) every other epoch. balanced_acc stayed at 0.50.

**Lesson**: A 700 K-parameter from-scratch CNN does not have enough
capacity, or enough prior, to find the discriminative signal in a small
imbalanced audio dataset. Use **transfer learning** — start from
ImageNet-pretrained weights and fine-tune.

### Attempt #4 — pretrained ResNet, still 0.50

**What was tried**: Replaced the custom CNN with a ResNet-18 pretrained
on ImageNet. Adapted the first conv layer to accept 1-channel input by
averaging the RGB filters. balanced_acc selection, lr 3e-4.

**What happened**: The model still oscillated near balanced_acc 0.50 in
the first few epochs.

**Lesson, finally — the root cause**: `extract_features.py` was
**resampling audio to 22 050 Hz before computing the mel-spectrogram**.
That means Nyquist = 11 025 Hz, so anything above 11 kHz was erased.

But the MP3 transcoding signature is **a sharp roll-off ("the cliff") at
14–21 kHz** depending on bitrate. By downsampling first, we were
deleting the exact signal the model was supposed to learn. The
classifier wasn't oscillating because of LR or architecture — it was
oscillating because **the features did not contain the discriminative
information**.

Changed `SAMPLE_RATE` to **44 100 Hz** and re-extracted. Attempt #5
reached balanced_acc 0.82 in three epochs.

> ⚠️ **If you ever touch the feature extraction, do not downsample below
> 44.1 kHz.** The whole pipeline depends on the high-frequency content
> being preserved.

---

## Reproducing v2 from scratch

```bash
# Local — Windows machine with a FLAC library at D:/FLAC
python ml/build_dataset.py --root D:/FLAC --output ml/authentic.json --max-per-label 30
python ml/trim_for_upload.py --manifest ml/authentic.json --workers 16

# Stream to the GPU server
tar -C ml/trimmed -cf - . | ssh GPU_HOST "cd /root/flac-detective-ml/dataset/authentic && tar -xf -"

# On the GPU server
ssh GPU_HOST
cd /root/flac-detective-ml
bash setup_hetzner.sh      # one-time
bash run_pipeline.sh       # ~2 hours end to end

# Pull the trained TorchScript back
scp GPU_HOST:/root/flac-detective-ml/models/cnn_v2.ts.pt src/flac_detective/models/
```

All scripts seed with 42 and write configs alongside outputs. The full
pipeline is meant to be re-runnable end-to-end from a fresh checkout.

---

## Hardware target

Hetzner GPU server: RTX 4000 SFF Ada Gen (20 GB VRAM). Training capped at
50 % of VRAM via `torch.cuda.set_per_process_memory_fraction(0.5)` so it
coexists with a concurrent Whisper inference service on the same host.
End-to-end pipeline (transcode + features + train + export) is ~2 h wall
time for ~2 200 authentic files.

The model itself is CPU-friendly at inference: a single mel-spec forward
pass on a recent laptop is under 200 ms.
