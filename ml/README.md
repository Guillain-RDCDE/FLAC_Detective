# FLAC Detective — ML pipeline

This directory holds the ML side of **Rule 12** — the one that asks "is
this FLAC actually a FLAC, or did someone transcode an MP3 and rename the
extension?" The model currently shipping (`cnn_v3.ts.pt`, in **v0.12.0**)
is a fine-tuned **EfficientNet-B0** sitting at **balanced accuracy 0.834**
— 80 % specificity, 86.9 % recall on transcoded, on a 9 786-sample
held-out test set.

Getting there took six attempts. Four of them crashed in four genuinely
different ways. This README is half pipeline reference, half postmortem —
because audio classification on imbalanced datasets is full of footguns,
and writing the lessons down saves the next person (you, in three
months) from stepping on the same mines.

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
| `train.py` | Train the EfficientNet-B0 classifier with Mixup + WeightedRandomSampler, save best checkpoint by `balanced_acc`. |
| `export_torchscript.py` | Trace the best checkpoint to TorchScript for runtime use. |
| `run_pipeline.sh` | Chain the four GPU-side stages (transcode → features → train → export). |

---

## The current production model — v3, shipped in v0.12.0

If you just want to know what the package ships with, this section is
enough. If you want to know *how* we got here and what went wrong on the
way, skip down to "Six attempts" — that's the fun part.

- **Architecture**: **EfficientNet-B0** pretrained on ImageNet. ~4 M
  parameters (vs 11 M for ResNet-18). First conv layer adapted from
  3-channel RGB to 1-channel mel by averaging the RGB filter weights.
  Final FC replaced with a binary head.
- **Input**: (1, 1, 128, 862) — a 10-second mel-spectrogram at 44.1 kHz,
  128 mel bins, 2048 FFT, hop 512.
- **Training data**: **5 964 authentic FLACs × 10 codec/bitrate transcodes
  + 5 964 authentics = 65 244 samples**. Stratified 70/15/15
  train/val/test split.
- **Optimisation**: AdamW (lr 3e-4, weight decay 1e-4), cosine annealing
  with 5-epoch linear warmup, `WeightedRandomSampler` to balance batches,
  plain CrossEntropyLoss, **Mixup** (α=0.2), SpecAugment (freq mask 15,
  time mask 20, 2 masks).
- **Selection criterion**: **`balanced_acc`** = mean of per-class recalls.
  Robust to imbalance, cannot be gamed by predicting only the majority class.
- **Feature loading**: **mmap-backed** `.npy` files (`features/mmap/X.npy`).
  The 27 GB tensor stays on disk; the DataLoader pages samples in as needed.
  Without this, training was OOM-killed on the Hetzner host shared with
  Whisper + other services.
- **Test metrics** (held-out 9 786 samples):

  | Metric                        | Value |
  |-------------------------------|-------|
  | accuracy                      | 86.3% |
  | balanced_acc                  | **0.834** |
  | precision (transcoded)        | 97.7% |
  | recall (transcoded)           | **86.9%** |
  | recall (authentic) = specificity | **80.0%** |
  | tp / fp / fn / tn             | 7730 / 178 / 1166 / 712 |

- **Runtime size**: 16 MB TorchScript, bundled in the wheel.

### Why v3 beats v2 — including on size

v3 has **less than half the parameters** of v2 and ships in **a third of
the wheel size**, while improving every metric. That's the rare
free-lunch territory: newer ImageNet backbone + more data + slightly
better optim, and the model both gets smarter *and* shrinks.

| Aspect              | v2 (v0.11)  | v3 (v0.12)        |
|---------------------|-------------|-------------------|
| Authentic FLACs     | 2 237       | **5 964**         |
| Codecs              | 7           | **10** (+ VBR, Vorbis) |
| Training samples    | 24 451      | **65 244**        |
| Architecture        | ResNet-18   | **EfficientNet-B0** |
| Parameters          | 11 M        | 4 M               |
| Data augmentation   | SpecAugment | **+ Mixup**       |
| LR schedule         | ReduceLROnPlateau | **Cosine + warmup** |
| Feature loading     | Full in-RAM | **mmap on disk**  |
| balanced_acc        | 0.811       | **0.834** (+0.023) |
| Recall transcoded   | 82.7 %      | **86.9 %** (+4.2 pp) |
| Bundled size        | 43 MB       | **16 MB** (-63 %) |

---

## Six attempts to train one model

Spoiler : il a fallu six itérations pour obtenir un modèle utile, dont
quatre qui se sont crashées de quatre façons différentes. Si vous lisez
ceci en cherchant à entraîner un classifieur audio binaire, lisez la
section ci-dessous **avant** d'écrire votre boucle d'entraînement — ça
vous économisera probablement trois soirées.

### Attempt #1 — "j'ai trop bien équilibré, le modèle dit toujours non"

Idée brillante du moment : combiner une **focal loss** avec poids par
classe (`alpha = [n/(2·c_auth), n/(2·c_trans)]`) **et** un
`WeightedRandomSampler` qui ré-équilibre déjà les batches. Logique du
type "deux fois plus c'est deux fois mieux".

Sauf que non. La rare classe (authentic) se retrouve sur-pondérée d'un
ordre de grandeur. Le modèle apprend en trois epochs la stratégie la
plus rentable : **dire "authentic" pour tout**. Recall sur la classe
transcoded : `0`. Joli.

> 💡 **Lesson** — Pour gérer l'imbalance, **une seule** technique à la
> fois. Soit on rééquilibre les batches via le sampler, soit on
> pondère la loss, mais pas les deux. Sinon on sur-corrige et le
> modèle apprend la fainéantise.

### Attempt #2 — "génial, val_f1 = 95 % !... ah non en fait"

OK, focal loss virée. On garde sampler + plain CrossEntropy. La courbe
de `val_f1` grimpe joliment à **0.95** dès l'epoch 4 et y reste.
Champagne... jusqu'à ce qu'on regarde le détail. Le modèle est
maintenant *l'opposé* de l'attempt #1 : il dit "transcoded" pour tout.
Le test confirme : `tn = 0`. Zéro authentique correctement classé sur
333.

Pourquoi `val_f1` est super alors ? Parce que F1 est calculé **sur la
classe transcoded uniquement**, et qu'avec un dataset 1:10, "tout
transcoded" donne mécaniquement recall=1 et précision ≈ 0.91. Le
training loop, fier de lui, a sauvegardé ce modèle dégénéré comme
"meilleur".

> 💡 **Lesson** — Sur un dataset déséquilibré, F1-on-class-1 est une
> métrique qui peut être *triée* en prédisant la classe majoritaire.
> Utilisez **balanced_accuracy** = moyenne des recalls par classe.
> Elle ne peut pas être truquée comme ça.

### Attempt #3 — "ça oscille, on dirait du yoyo"

Maintenant on sélectionne sur `balanced_acc`, on baisse le LR de
`1e-3` à `3e-4`, et on garde notre petit CNN custom (5 blocs conv,
~700 K paramètres). Lancement.

Epoch 1 : 0.55. Epoch 2 : 0.50. Epoch 3 : auth=100 % / trans=0 %. Epoch
4 : auth=0 % / trans=100 %. **Le modèle balance violemment entre les
deux extrêmes**, sans jamais converger. balanced_acc à 0.50 +/- du
bruit. Au bout de 15 epochs il est aussi perdu qu'au début.

> 💡 **Lesson** — Un CNN from-scratch de 700 K paramètres n'a ni la
> capacité ni le prior nécessaires pour trouver un signal subtil dans
> un dataset audio déséquilibré. **Transfer learning** : démarrer
> depuis des poids pré-entraînés (ImageNet → fine-tune). C'est la
> baseline standard pour une raison.

### Attempt #4 — "même problème, j'abandonne... wait, c'est pas l'archi"

On remplace le custom CNN par un **ResNet-18 pré-entraîné**. On adapte
la première conv (3-channel RGB → 1-channel mel) en moyennant les
poids RGB. balanced_acc en sortie : toujours autour de **0.50**, même
oscillation. Le modèle pré-entraîné le plus standard de la planète,
qui marche pour tout le monde, refuse d'apprendre sur nos features.

C'est là que j'ai retourné `extract_features.py` pour vraiment
comprendre ce qu'on entraînait. Et boum.

```python
SAMPLE_RATE = 22050   # downsample to halve compute
```

22 050 Hz. Nyquist = 11 025 Hz. **On supprime tout le contenu au-dessus
de 11 kHz avant même de calculer le mel-spectrogramme.**

Mais la signature MP3 — *la falaise spectrale* qu'on essaie de
détecter — vit à **14-21 kHz** selon le bitrate. On était littéralement
en train d'apprendre à un modèle à distinguer des transcodes... avec un
filtre passe-bas qui effaçait exactement la signature des transcodes.
Le réseau n'oscillait pas par incompétence : il oscillait parce que
**le signal n'était pas dans les données**.

`SAMPLE_RATE = 44100`. Re-extract features. Attempt #5 atteint
balanced_acc 0.82 en **trois epochs**.

> 💡 **Lesson** — Quand un modèle solide refuse d'apprendre, le
> problème n'est probablement pas le modèle. Vérifiez que vos
> features contiennent réellement le signal que vous voulez apprendre.
> Faites un dump visuel d'un sample avant de blamer l'architecture.
>
> ⚠️ **Et si vous touchez à `extract_features.py` un jour : ne
> downsamplez jamais sous 44 100 Hz.** Tout le pipeline en dépend.

### Attempt #5 — ça marche enfin (v2, shipped in v0.11.0)

Même config que #4 mais avec le fix sample rate. 24 451 samples (2 237
authentiques × 7 codecs + originaux). Custom CNN ré-essayé, encore en
dessous, ResNet-18 pré-entraîné repris.

Convergence propre. balanced_acc atteint **0.811** à l'epoch 3, plateau
ensuite, early-stop à l'epoch 11. Specificité à 80 % (vs un déprimant
4.5 % pour le v1 broken qu'on avait shipped en v0.10). Le modèle voit
enfin la falaise MP3 et apprend à la nommer.

Shipped en **v0.11.0**.

> 💡 **Lesson** — Quand les quatre leçons précédentes sont appliquées
> ensemble (un seul mécanisme d'imbalance, métrique non-trichable,
> transfer learning, vraies features), un classifieur mel-spec CNN
> apprend la tâche. Pas miraculeux. Juste correct.

### Attempt #6 — "scalons" (v3, shipped in v0.12.0)

Trois changements par rapport à v2 :
1. **Plus de données** — 5 964 authentiques × 10 codecs = **65 244
   samples** (2.6× v2). On ajoute MP3 VBR V0/V2 et OGG Vorbis q5 au
   zoo des transcodes.
2. **Meilleure archi** — EfficientNet-B0 pré-entraîné (4 M params, vs
   11 M pour ResNet-18). Plus efficace par paramètre.
3. **Meilleure optim** — Mixup α=0.2, cosine annealing avec warmup
   linéaire, AdamW.

On lance.

**OOM kill au bout de trois minutes.** Le `.npz` compressé fait 27 GB
sur disque ; `np.load` le décompresse intégralement en RAM. Plus
PyTorch, plus les DataLoader workers, on dépasse 61 GB d'anonymous RSS
sur un host à 62 GB qui héberge aussi Whisper, LanguageTool, etc. Le
kernel nous descend.

Fix : convertir une fois en `.npy` plain (uncompressed, 32 GB sur
disque mais qui restent sur disque), charger avec
`np.load(..., mmap_mode='r')`, et déplacer la normalisation
per-sample dans `MelDataset.__getitem__` au lieu d'un pass upfront sur
tout le tensor. Peak RAM training tombe de 61 GB à ~5 GB. On relance.

Trains cleanly. balanced_acc atteint **0.834** à l'epoch 3, plateau,
early-stop à l'epoch 13. Modèle 16 MB en TorchScript. Shipped en
**v0.12.0**.

> 💡 **Lesson #1** — Sur un host partagé, **ne chargez pas un dataset
> qui dépasse ~50 % de la RAM**. Et souvenez-vous que `np.load` d'un
> `.npz` compressé matérialise *intégralement* chaque array — peu
> importe la taille apparente du fichier sur disque.
>
> 💡 **Lesson #2** — **Quand vous scalez la donnée, le bottleneck
> change.** v3 gagne 0.023 sur balanced_acc mais introduit un vrai
> problème infra (RAM) qui n'existait pas en v2. Benchmarkez d'abord
> sur la plus petite config qui démontre le problème, pas sur la plus
> ambitieuse.

### Take-aways si vous voulez entraîner un classifieur audio

Si après les six histoires ci-dessus vous voulez quand même essayer,
voilà la check-list condensée :

1. **Une seule technique d'imbalance** à la fois.
2. **Métrique non-triquable** pour la sélection (balanced_acc, pas
   F1-on-class-1).
3. **Transfer learning** (ResNet-18 ou EfficientNet-B0 pré-entraîné),
   pas de CNN custom from-scratch sauf si vous savez exactement
   pourquoi.
4. **Vérifiez que vos features contiennent le signal.** Faites un
   `librosa.display.specshow` d'un échantillon authentique et d'un
   échantillon transcodé. Si vous ne voyez pas la différence à l'œil,
   le réseau ne la verra pas non plus.
5. **Sur host partagé : mmap.** Pas de `.npz` qui se décompresse en RAM.
6. **Scale up incrémentalement.** Validez sur N=1000 avant de lancer
   sur N=65000.

Les six attempts ci-dessus correspondent chacun à une violation d'un
des six points. Voilà, vous êtes prévenus.

---

## The reliability gate, and the four dead ends before it (v0.13)

v3 shipped with a balanced accuracy of 0.834 and **specificity stuck at 80 %** —
one authentic FLAC in five was being flagged as a transcode. This section is the
story of chasing that 20 %: a full empirical audit, four different fixes that
*didn't* work (each instructive), and the small one that did. It's the most
R&D-heavy thing in this repo, and the most honest, because most of it is failure.

Every number below is reproducible from the scripts listed at the end.

### Step 0 — Where exactly does it fail?

Instead of guessing, we ran v3 over **all 11 234 certified-authentic FLACs** in
the reference library and bucketed the false-positive rate by the file's 95 %
spectral rolloff (`ml/analyze_false_positives.py`). The result was not subtle:

| 95% spectral rolloff | false-positive rate | n      |
|----------------------|---------------------|--------|
| **< 4 kHz**          | **57.2 %**          | 944    |
| 4–7 kHz              | 30.2 %              | 2 895  |
| 7–10 kHz             | 14.3 %              | 3 649  |
| 10–14 kHz            | 8.2 %               | 3 297  |
| ≥ 14 kHz             | 4.9 %               | 449    |

The errors are almost entirely **band-limited material** — and it clusters by
exactly the genres you'd predict: baroque (Couperin, Schütz), solo piano, 1920s
blues, kora, and the Dust-to-Digital archival label (774 files, 40 % FP). The
sanity check that the audit was even valid: overall FP rate came out 19.8 %,
i.e. specificity 80.2 %, matching the held-out test set's 80.0 % to a fifth of a
point. Same pipeline, same model.

### Why band-limited material is the hard case (the physics)

A transcode detector keys on the **brickwall** an MP3 encoder leaves behind: a
sharp spectral cliff at 16–20.5 kHz where the lossy codec discarded everything
above its bitrate-dependent cutoff. But if a recording *already* rolls off below
~7 kHz — because that's all the musicians, the room, and the 1928 microphone put
there — then an MP3 transcode removes **almost nothing**. There is no cliff to
find, because there was nothing above the cliff to begin with. The authentic and
the fake are nearly identical to any detector that works on the spectrum.

That reframes the question from "why is the model bad here?" to "is the
information even present?" The next four sections are four attempts to find it.

### Dead end #1 — Just raise the decision threshold

The cheapest idea: Rule 12 flags at p ≥ 0.5; raise the bar. We measured the cost
on a 988-file paired set of authentics + their transcodes (`ml/build_gate_testset.py`,
`ml/analyze_gate.py`):

| threshold | transcode recall | balanced acc |
|-----------|------------------|--------------|
| 0.50      | 90.6 %           | 70.6 %       |
| 0.60      | 80.0 %           | 71.0 %       |
| 0.70      | 71.3 %           | 72.7 %       |
| 0.80      | 60.3 %           | 71.5 %       |

Balanced accuracy is **flat** (~71 %) across the whole range. Raising the
threshold doesn't find a free lunch — it trades transcode recall for specificity
roughly 1:1. Defensible as a *policy* if false alarms annoy you more than misses,
but it's not an improvement. Next.

### Dead end #2 — An abstention gate on cheap signals (and a debunked "eureka")

If the model can't be trusted on band-limited files, maybe a cheap heuristic can
tell us *when* to ignore it. We tested whether any signal — spectral cutoff,
compression ratio, container bitrate — separates the flagged authentics (false
positives) from genuine transcodes. Best Youden's J across all of them: **0.11**
(0 is random). They don't separate, because — see the physics above — there's
nothing to separate.

This step also produced the most useful mistake of the whole project. One
feature (`mp3_pattern`, Rule 9's noise-pattern test) showed a **population AUC of
0.99**. Champagne. Until the GroupKFold classifier that included it scored 0.6,
not 0.99. Looking at the raw values: the feature was `0` for 118 of 120 files in
*every* group — a near-constant, and the 0.99 was an artefact of computing AUC on
a degenerate binary. **Cross-validation discipline caught a false discovery that
a single pooled metric would have shipped.** Keep that one in your pocket.

### Dead end #3 — Texture *inside* the occupied band, and the stereo channel

Here's a structural discovery worth its own line: **all three of Rule 9's tests
(pre-echo, HF aliasing, MP3 noise pattern) operate in the 10–20 kHz band.** So
does the CNN's effective attention, and so does every cutoff rule. The entire
arsenal looks *above* 10 kHz — exactly where band-limited material is empty. Nobody
was looking *inside* the occupied band, or at the **stereo** image.

So we did (`ml/texture_probe.py`). MP3 joint-stereo quantises the side channel
(L−R) aggressively, and zeroes MDCT coefficients below the masking threshold even
within the occupied band. We measured side/mid energy, L/R correlation, in-band
spectral flatness, spectral "holes", terracing — on 120 band-limited sources and
their transcodes, analysed **paired** (each transcode vs its own original, which
controls for the source).

The signals are **real but weak**. Paired sign-consistency is striking
(`flatness_inband` shifts the same direction in 96 % of pairs; `lr_corr` in 94 %),
which proves the fingerprint exists — but the magnitudes are tiny against the
variance between different pieces of music, so no feature separates a *single*
file. A RandomForest over all of them, cross-validated by source:

| codec   | detectability (AUC) |
|---------|---------------------|
| mp3_128 | **0.68**            |
| mp3_v0  | 0.65                |
| mp3_320 | **0.53** (≈ random) |

Recoverable-ish for low-bitrate fakes; **fundamentally undetectable at 320 kbps**.
And the averaged spectra throw away time — maybe the signal is in the dynamics.

### Dead end #4 — Temporal modulation at the MP3 frame rate

The most elegant idea, saved for last. An MP3 encoder re-quantises every
**1152-sample frame (38.28 Hz)** and **576-sample granule (76.56 Hz)**, which
should stamp a periodic modulation onto the energy envelope — a fingerprint that
time-averaging destroys and a fine-resolution probe could recover
(`ml/texture_temporal_probe.py`, hop=128 so both rates are resolved).

It isn't there. Population AUC for the modulation features: **0.50, everywhere.**
The granule/frame periodicity is either not energy-modulated by LAME for this
material, or it drowns in the music's own envelope dynamics over a 20 s window.
The full temporal classifier (AUC 0.635 at 128 kbps) did *worse* than the averaged
texture features. The theoretically strongest signal turned out to be the weakest.

### The conclusion that the four dead ends earn

Cutoff, compression ratio, stereo, in-band texture, temporal modulation, all of
Rule 9 — **every cheap signal fails on band-limited material, because the
information genuinely is not in the file.** That's not a defeat; it's a *result*.
It means the right engineering move isn't to keep guessing — it's to **stop
guessing in the regime where guessing can't win**, and the gate below is the
optimal policy given a limit we've now proven by exhaustion.

### The fix that shipped — a reliability gate

We measured the CNN's precision per rolloff bucket (in a balanced 50/50 setting):

| 95% rolloff | Rule 12 precision |
|-------------|-------------------|
| < 4 kHz     | **58.9 %** (coin flip) |
| 4–7 kHz     | 74.6 %            |
| 7–10 kHz    | 87.2 %            |
| 10–14 kHz   | 91.9 %            |
| ≥ 14 kHz    | 95.0 %            |

Rule 12 is only trustworthy above ~7 kHz. So as of v0.13, **it abstains
(contributes 0 and defers to the heuristic rules) when the file's 95 % rolloff is
below 7 kHz.** The rolloff is computed from the same audio decode already used for
the mel-spectrogram, so there's no extra I/O (`ml_classifier._compute_mel` now
returns `(mel, rolloff)`). Effect on the real authentic library:

| gate (abstain below) | specificity | what's given up |
|----------------------|-------------|------------------|
| (none, v3 baseline)  | 80.2 %      | —                |
| < 4 kHz              | 85.0 %      | detection at 59 % precision |
| **< 7 kHz (shipped)**| **92.8 %**  | + the 4–7 kHz band (75 % precision) |
| < 10 kHz             | 97.4 %      | + a band where real signal lives |

**Specificity 80 % → 93 %, for a dozen lines and no GPU.** The only detection
surrendered is in a regime where Rule 12 was a coin flip — and where a transcode
is also the *least* harmful (a 320 kbps MP3 of a source that ends at 5 kHz is
sonically transparent; you've lost nothing audible). Heuristic Rules 1–11 are
untouched and still run on every file. Pinned by `tests/test_rule12_gate.py`.

> 💡 **Lesson** — When a model fails, audit *where* before you change *what*. The
> failure here was concentrated and physical, not diffuse. And once four
> independent attacks all bounce off the same wall, the wall is real: the
> engineering win was to recognise the limit and route around it, not to keep
> throwing model capacity at information that isn't in the signal.

### Reproducing this investigation

| Script | Produces |
|---|---|
| `analyze_false_positives.py` | `fp_analysis_v3.csv` — per-file p, rolloff, HF ratio over the whole authentic library; the FP-by-rolloff audit. |
| `build_gate_testset.py` | `gate_testset.csv` — 988 paired authentic+transcode files with model probability and heuristic signals. |
| `analyze_gate.py` | The threshold-cost table and the (failed) cheap-signal abstention gate. |
| `texture_probe.py` / `analyze_texture.py` | In-band + stereo texture features; the paired / AUC / GroupKFold analysis (dead end #3). |
| `texture_temporal_probe.py` / `analyze_temporal.py` | Frame-rate modulation + temporal-variance features (dead end #4). |
| `build_dataset_v4.py` | `authentic_sampled_v4.json` — a rolloff-stratified v4 training manifest (8 627 files) for the data-side follow-up. |

All seed with 42 and run on CPU. The heavy steps (transcoding + feature
extraction) are parallelised; on a 4-core box the full audit is ~35 min, each
texture probe ~30–45 min.

---

## Reproducing the pipeline from scratch

You'll need three things: a directory of FLACs with verifiable provenance
(EAC, XLD or CUERipper logs, or Audiochecker `CDDA (100%)` verdicts), an
SSH key into a GPU box, and a couple of hours of patience.

```bash
# Local — Windows machine with a FLAC library at D:/FLAC
python ml/build_dataset.py --root D:/FLAC --output ml/authentic.json --max-per-label 30
python ml/trim_for_upload.py --manifest ml/authentic.json --workers 16

# Stream to the GPU server — tar over SSH, no intermediate staging
tar -C ml/trimmed -cf - . | ssh GPU_HOST "cd /root/flac-detective-ml/dataset/authentic && tar -xf -"

# On the GPU server
ssh GPU_HOST
cd /root/flac-detective-ml
bash setup_hetzner.sh      # one-time provisioning (PyTorch, librosa, etc.)
bash run_pipeline.sh       # ~2 h end-to-end for ~2 200 files

# Pull the trained TorchScript back
scp GPU_HOST:/root/flac-detective-ml/models/cnn_v3.ts.pt src/flac_detective/models/
```

Everything seeds with 42 and writes its config next to its outputs. The
pipeline is meant to be re-runnable end-to-end from a fresh checkout — if
a stage fails halfway through, you can re-launch from that stage without
redoing the previous ones.

---

## Hardware target

The whole pipeline lives on a shared Hetzner box — RTX 4000 SFF Ada Gen
(20 GB VRAM), 62 GB RAM, with a Whisper transcription service and a few
other things already running in production on it. Training caps GPU
usage at **50 % of VRAM** via
`torch.cuda.set_per_process_memory_fraction(0.5)` so it doesn't elbow
Whisper off the GPU mid-inference. End-to-end pipeline (transcode +
features + train + export) is about 2 h of wall time for ~2 200
authentic files.

At inference, the model is happily CPU-friendly: a single mel-spec
forward pass on a recent laptop is under 200 ms. No GPU needed once it
ships into the wheel.
