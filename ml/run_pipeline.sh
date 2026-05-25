#!/bin/bash
# End-to-end ML pipeline runner. Execute on Hetzner inside /root/flac-detective-ml/
# after the authentic FLAC dataset has been uploaded into dataset/authentic/.
#
# Each stage is idempotent and re-runnable. If a stage was already completed,
# its outputs are detected and the next stage runs.
#
# Usage:
#   tmux new -s flac-ml
#   cd /root/flac-detective-ml
#   bash run_pipeline.sh 2>&1 | tee pipeline.log
#   # Ctrl-b d to detach; come back later with `tmux attach -t flac-ml`
set -euo pipefail

PROJECT=/root/flac-detective-ml
cd "$PROJECT"

PY="$PROJECT/venv/bin/python"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ---------------------------------------------------------------------------
log "Stage 1/4 — Generate transcodes (MP3, AAC, Opus -> fake FLAC)"
# ---------------------------------------------------------------------------
if [ "$(find dataset/transcoded -name '*.flac' 2>/dev/null | wc -l)" -lt 100 ]; then
    "$PY" generate_transcodes.py \
        --input  dataset/authentic \
        --output dataset/transcoded \
        --workers 16
else
    log "Skipping: dataset/transcoded already contains $(find dataset/transcoded -name '*.flac' | wc -l) files"
fi
log "  authentic: $(find dataset/authentic -name '*.flac' | wc -l)"
log "  transcoded: $(find dataset/transcoded -name '*.flac' | wc -l)"

# ---------------------------------------------------------------------------
log "Stage 2/4 — Extract mel-spectrograms"
# ---------------------------------------------------------------------------
if [ ! -f features/dataset.npz ]; then
    "$PY" extract_features.py \
        --input dataset \
        --output features/dataset.npz \
        --workers 12
else
    log "Skipping: features/dataset.npz exists ($(du -h features/dataset.npz | cut -f1))"
fi

# ---------------------------------------------------------------------------
log "Stage 3/4 — Train CNN classifier"
# ---------------------------------------------------------------------------
if [ ! -f models/cnn_v1/best.pt ]; then
    "$PY" train.py \
        --features features/dataset.npz \
        --output models/cnn_v1 \
        --epochs 25 \
        --batch-size 32 \
        --mem-fraction 0.5
else
    log "Skipping: models/cnn_v1/best.pt exists"
fi

# ---------------------------------------------------------------------------
log "Stage 4/4 — Export TorchScript"
# ---------------------------------------------------------------------------
if [ ! -f models/cnn_v1.ts.pt ]; then
    "$PY" export_torchscript.py \
        --checkpoint models/cnn_v1/best.pt \
        --output     models/cnn_v1.ts.pt
else
    log "Skipping: models/cnn_v1.ts.pt exists"
fi

log "Pipeline complete."
log "Final artefacts:"
log "  $(ls -la models/cnn_v1/best.pt)"
log "  $(ls -la models/cnn_v1.ts.pt)"
log ""
log "Next step (from your local machine):"
log "  scp -i ~/.ssh/secours_madactylo_2026-05-11 \\"
log "      root@144.76.203.6:/root/flac-detective-ml/models/cnn_v1.ts.pt \\"
log "      src/flac_detective/models/cnn_v1.ts.pt"
