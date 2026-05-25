#!/bin/bash
# Run-once setup for the FLAC Detective ML training environment on Hetzner.
# Idempotent: safe to re-run.
set -eu

PROJECT=/root/flac-detective-ml

echo "=== Create project layout ==="
mkdir -p "$PROJECT"/dataset/authentic
mkdir -p "$PROJECT"/dataset/transcoded
mkdir -p "$PROJECT"/features
mkdir -p "$PROJECT"/models
mkdir -p "$PROJECT"/scripts
ls -la "$PROJECT"

echo ""
echo "=== Create venv (Python 3.12) ==="
if [ ! -x "$PROJECT/venv/bin/python" ]; then
    python3.12 -m venv "$PROJECT/venv"
fi
"$PROJECT/venv/bin/python" --version

echo ""
echo "=== Upgrade pip / wheel ==="
"$PROJECT/venv/bin/pip" install --upgrade pip wheel --quiet

echo ""
echo "=== Install PyTorch (CUDA 12.1 build) — takes 2-4 min ==="
"$PROJECT/venv/bin/pip" install --index-url https://download.pytorch.org/whl/cu121 \
    torch torchaudio --quiet 2>&1 | tail -3

echo ""
echo "=== Install ML / audio deps ==="
"$PROJECT/venv/bin/pip" install --quiet \
    librosa scikit-learn soundfile mutagen numpy scipy \
    tqdm tensorboard 2>&1 | tail -3

echo ""
echo "=== Sanity checks ==="
"$PROJECT/venv/bin/python" -c "
import torch, torchaudio, librosa, sklearn, soundfile
print('torch       :', torch.__version__)
print('torchaudio  :', torchaudio.__version__)
print('librosa     :', librosa.__version__)
print('sklearn     :', sklearn.__version__)
print('soundfile   :', soundfile.__version__)
print('CUDA avail  :', torch.cuda.is_available())
print('CUDA device :', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')
print('Free VRAM   :', round(torch.cuda.mem_get_info()[0]/1024**3, 2), 'GB') if torch.cuda.is_available() else None
"
echo ""
echo "=== Done. Project ready at $PROJECT ==="
