# FLAC Detective — ML pipeline

This directory holds the ML side of **Rule 12** — the one that asks "is
this FLAC actually a FLAC, or did someone transcode an MP3 and rename the
extension?" The model currently shipping (`cnn_v4_stereo.ts.pt`, since
**v0.14.0**) is a fine-tuned **2-channel (mid+side) EfficientNet-B0** at
**balanced accuracy 0.905** — 95.1 % real-library specificity (with the
<7 kHz reliability gate), 94 % recall on transcoded. Earlier mono models
(`cnn_v2`/`cnn_v3`) are part of the story below, not what ships.

Getting there took six attempts (plus a stereo breakthrough and, in v1.2,
a scoring fix). Several crashed in genuinely different ways. This README is
half pipeline reference, half postmortem —
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
                                   models/cnn_v4_stereo/best.pt
                                          |
                                          v
                                   export_torchscript.py
                                          |
                              (download cnn_v4_stereo.ts.pt)
                                          |
                                          v
[Local]
   |
   v
src/flac_detective/models/cnn_v4_stereo.ts.pt
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
| `emit_probs.py` | Walk a labelled corpus through the **shipped** inference (`infer_file_probability`, multi-window + calibration) and write a `p_raw,label` CSV — the input for `calibrate_model.py`. |
| `calibrate_model.py` | Fit a monotonic Platt/isotonic mapping `p_raw → p_cal` (Newton-Raphson / PAVA, no sklearn) and write `cnn_v4_stereo.calibration.json`. Reports Brier/ECE before vs after. |
| `generate_transcodes_external.py` | Widen the zoo with **external** (non-ffmpeg) encoders — LAME, qaac, fdkaac, oggenc, opusenc, afconvert — for out-of-distribution data. Auto-skips encoders not on PATH. |
| `build_wild_testset.py` | Score a labelled **wild** corpus (real collected fakes + authentics) through the shipped inference; emit `path,label,source,p_raw,p_cal,rolloff,abstained`. |
| `measure_auc_drop.py` | Compare per-set ROC-AUC / balanced-acc / ECE across labelled prob CSVs and report the **AUC drop** from the in-distribution (ffmpeg) baseline to the wild/external sets. |

### v1.6 — calibration, multi-window, and the wild-generalisation harness

Three things landed on top of the v4 stereo model, none of them retraining it:

1. **Calibration (`calibrate_model.py` → `cnn_v4_stereo.calibration.json`).** The
   softmax `p` is over-confident; a Platt/isotonic mapping rescales it so a
   reported probability means what it says. Fit it on held-out data emitted by
   `emit_probs.py` (which uses the *production* inference path, so the fit matches
   what ships). Absent the JSON, calibration is the identity — safe by default.
2. **Multi-window inference.** The runtime now averages several windows per file
   instead of trusting one middle segment (the start-vs-middle fragility that
   bit the measurements in this README three times). `infer_file_probability()`
   in `ml_classifier.py` is the shared source of truth.
3. **Out-of-ffmpeg generalisation.** The honest open question this README keeps
   circling — *does the model generalise past our own ffmpeg pipeline?* — now has
   a harness. `generate_transcodes_external.py` builds fakes with other encoders;
   `build_wild_testset.py` scores a corpus; `measure_auc_drop.py` quantifies the gap.

   **First measurement (2026-06-26, n=300 authentic sources):** fakes built with
   *standalone* encoders not in the training zoo — LAME (320/V0/V2), oggenc (Vorbis),
   opusenc (Opus) — scored through the shipped inference and compared to the ffmpeg
   in-distribution baseline:

   | set                                   | AUC   | bal acc | specificity |
   |---------------------------------------|-------|---------|-------------|
   | ffmpeg (in-distribution)              | 0.995 | 0.975   | 0.968       |
   | external encoders (LAME/oggenc/opusenc) | **0.986** | 0.945 | 0.923    |

   **AUC drop Δ 0.009 — negligible.** The model holds up against encoders it never
   trained on: it learned a genuine transcode fingerprint, not an ffmpeg-encoder
   tell, at least for these MP3/Vorbis/Opus families.

   **AAC encoder diversity (the codec that mattered most).** AAC was the historical
   hard case, so the obvious worry was a *different AAC encoder*. We added Fraunhofer
   **fdkaac** (genuinely distinct from ffmpeg's native `aac`) and compared, same 300
   sources, same 256k target:

   | set                          | AUC   | recall | specificity |
   |------------------------------|-------|--------|-------------|
   | ffmpeg-aac (in-distribution) | 0.952 | 0.805  | 0.923       |
   | fdkaac / Fraunhofer (OOD)    | **0.971** | 0.903 | 0.923    |

   **No drop — Δ −0.019, fdkaac is if anything *easier*.** The model generalises to a
   different AAC encoder. AAC's difficulty is the codec's near-transparency at 256k
   (both ~0.95–0.97), **not** the encoder's identity. The last encoder-diversity gap
   closes the same way the others did: no evidence of an ffmpeg-specific tell.
   (Apple's qaac / afconvert need macOS/Windows and stay untested, but they're the
   *same* AAC family fdkaac just validated.)

   **A first truly-wild specificity test.** Encoder diversity isn't the wild — so we
   also pulled **45 genuine lossless FLACs from the Internet Archive Live Music
   Archive** (`etree` taper recordings, freely distributable), files from outside our
   corpus in genres/mastering the model never saw, and ran the **full pipeline with
   `--deep`**. Every one *should* read AUTHENTIC:

   | verdict       | count |
   |---------------|-------|
   | AUTHENTIC     | 39    |
   | WARNING       | 5     |
   | SUSPICIOUS    | 1     |
   | FAKE_CERTAIN  | **0** |

   **86.7 % specificity, zero hard false condemnations**, and 0/45 false fake-hi-res
   flags. Honest framing: live *audience* recordings are adversarial for a
   cliff-based detector (board patches, mic-limited HF can look band-limited), and
   `--deep` is the most aggressive mode (Rule 12 + WARNING floor on every file) — the
   default scan would read higher. Reproduce with `ml/fetch_wild_authentic.py`
   (download) then `flac-detective <dir> --deep` (verdict per file). The harness now
   exists; a larger, genre-stratified wild set is the natural next expansion.

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

## The fifth attempt that worked — stereo (v0.14)

The section above ended on a confident note: the band-limited regime is a
near-fundamental limit, proven by exhaustion. That conclusion was wrong — or
rather, it was right about one thing and blind to another. It was right that
*no spectral signal* separates band-limited authentic from transcode. It was
blind because **everything we tried, including the model, listens in mono.**

### The crack in the wall

MP3 doesn't only low-pass. At typical bitrates it codes stereo jointly, and the
**side channel** (L−R) is quantised far more aggressively than the mid. That
leaves a fingerprint that has nothing to do with the spectral cliff — it's there
even when the cliff isn't, i.e. exactly in band-limited material. And the v3 CNN
never saw it: it runs on a **mono** mel-spectrogram. So did Rule 9. So did every
probe above. We'd spent four sections proving a mono representation can't do
something, and quietly assumed that meant it couldn't be done.

### The controlled probe

One experiment settles it cleanly (`ml/stereo_probe_features.py` +
`ml/stereo_probe_train.py`): take 250 band-limited authentics + their
transcodes, train the *same* compact CNN twice under GroupKFold by source — once
on the **mid** channel alone, once on **mid+side** — and read off the difference.

| codec   | mono (mid) AUC | stereo (mid+side) AUC | Δ from the side channel |
|---------|----------------|------------------------|--------------------------|
| mp3_128 | 0.55           | **0.73**               | **+0.18**                |
| mp3_320 | 0.51           | **0.71**               | **+0.20**                |

The mono model is a coin flip — it *reproduces v3's failure*. Adding the side
channel lifts it to ~0.72, **including at 320 kbps**, the case the hand-crafted
features had pronounced fundamentally undetectable. The bit-depth confound was
ruled out (all sources 16-bit, transcodes quantised to 16-bit), so this is the
genuine joint-stereo fingerprint, not a pipeline tell. The wall was never the
audio. It was the microphone we listened through.

### v4 — a two-channel model

We retrained EfficientNet-B0 with a 2-channel (mid, side) stem on the full
65 244-sample dataset (`ml/extract_features_stereo.py` writes the features
straight to a float16 memmap — a 2-channel float32 tensor is ~57 GB and would
OOM the `np.stack` the mono extractor does; both channels are 16-bit-quantised
first so the model can't cheat on bit depth). Held-out test balanced accuracy
**0.834 → 0.905**; specificity **0.80 → 0.869**; transcode recall
**0.869 → 0.941**.

The real audit (all 11 234 authentics, `ml/analyze_fp_v4.py`) tells the honest
story — false-positive rate by rolloff, v3 → v4:

| rolloff   | v3 FP % | v4 FP % |    Δ    |
|-----------|---------|---------|---------|
| < 4 kHz   | 57.2 %  | 25.6 %  | −31.6 pp |
| 4–7 kHz   | 30.2 %  | 11.4 %  | −18.8 pp |
| 7–10 kHz  | 14.3 %  | 8.0 %   | −6.3 pp  |
| 10–14 kHz | 8.2 %   | 6.7 %   | −1.5 pp  |
| ≥ 14 kHz  | 4.9 %   | 7.3 %   | +2.4 pp  |

Better in every regime except full-range (a small price), fixing 1 383 of v3's
false positives against 276 new ones. **The reliability gate is kept** — v4 is
much less blind below 7 kHz than v3, but abstaining there still gives the best
specificity and stays faithful to "protect authentic files first":

| Real-library specificity        |        |
|---------------------------------|--------|
| v3 baseline                     | 80.2 % |
| v3 + gate (v0.13)               | 92.8 % |
| v4, no gate                     | 90.0 % |
| **v4 + gate (v0.14, shipped)**  | **95.1 %** |

> 💡 **Lesson** — "proven by exhaustion" is only as good as the assumptions every
> attempt silently shares. Four independent probes failed the same way because
> they all made the same choice — mono — that nobody had written down as a choice.
> When everything fails identically, suspect the thing they have in common.

> 💡 **And one on method** — the first audit of v4 reported 87.6 % specificity.
> Wrong: the audit script read the *start* of each file while training and
> inference read the *middle*. A cross-check of the shipped inference against the
> audit code caught it; the corrected number is 90.0 %. Verify the inference path
> before you trust the metric — the same lesson that opened this whole story
> (the per-sample normalisation in Step 0), arriving one last time.

Reproduce it: `stereo_probe_features.py` / `stereo_probe_train.py` (the probe),
`extract_features_stereo.py` (2-channel features), `train.py --features <dir>`
(now channel-count aware), `analyze_fp_v4.py` (the v3-vs-v4 audit).

---

## Is the ML rule even worth it? — measured

Fair question, and we owe it a number rather than a vibe. Rule 12 costs a heavy
dependency (`torch`), so it has to earn its place. The honest test isn't "how
accurate is the CNN" — it's its **marginal** value: on a labelled set, run the
full 12-rule pipeline and the 11 heuristics alone, and count what Rule 12 changes
(`ml/measure_rule12_value.py` — Rule 12 runs last and only adds points, so the
11-rule verdict is exact by subtraction).

On a rolloff-stratified set (120 authentics + their MP3/AAC transcodes):

| Rule 12's effect | count |
|---|---|
| Transcodes the 11 rules **miss entirely**, rescued by R12 to an *actionable* verdict (SUSPICIOUS+) | **~0** — every rescue stops at WARNING |
| Already-suspect files **promoted** WARNING → SUSPICIOUS | **~59** |
| Authentics wrongly flagged by R12 that 11 rules passed | **1** (a soft WARNING) |

So Rule 12 is a **confidence sharpener, not a frontline detector**: it rarely
catches a fake the heuristics miss outright, but it reliably turns "borderline,
maybe legit" into "likely a transcode" on files the heuristics already doubted —
at near-zero false-positive cost. Useful, narrow, honest. The README says exactly
this now: *"an optional 12th rule that sharpens borderline verdicts."*

> 💡 **Lesson** — a model that *looks* impressive in isolation (held-out balanced
> accuracy 0.905) can still be a minor contributor *in the system* it ships inside.
> Always measure the marginal value over the cheap baseline, not the standalone metric.

### Where the whole tool is blind (own it)

The same measurement exposed a limit that is **not** Rule 12's fault and that no
part of the tool solves: **high-bitrate AAC, VBR (V0), and transcodes of already
band-limited material are near-undetectable** — the 11 rules catch 3–6 % of AAC
256k, and Rule 12 barely moves it. This is physics, not laziness: those encodes
remove almost nothing a spectrogram can see. FLAC Detective's real, well-supported
job is the **common case — low-bitrate MP3 transcodes** — which it nails. On
high-bitrate AAC/VBR, treat an AUTHENTIC verdict as *"no evidence of transcoding"*,
not a guarantee. (We checked whether this was a data gap rather than a hard limit: a `-vn` bug does make `generate_transcodes.py` drop AAC/Opus/Vorbis for FLACs with embedded cover art — but the *training* clips are 30 s excerpts with the art already stripped, so the v3/v4 set did include ~5 929 / 5 964 AAC transcodes. The model trained on AAC and still can't catch AAC-256, so this is the genuine near-transparency of the codec, not missing data. The `-vn` fix still matters for anyone transcoding cover-art FLACs directly — and a 60-second count on the training host killed a 4-hour retrain built on the wrong premise.)

> ⚠️ **Half of this section was wrong, and the next chapter says how.** "Rule 12
> barely moves it" measured the *verdict*, and conflated two different things: whether
> the **model** can see AAC/Opus/Vorbis (it can, on full-range audio) and whether the
> **scoring + fast path** let that ability reach a verdict (they didn't). The "blind"
> framing held only for the second. Read on.

---

## The sixth attempt — the blind spot that wasn't (v1.2, `--deep`)

The section above closes the v0.14 story confident that high-bitrate AAC/Opus/Vorbis
are a near-fundamental wall. Like the band-limited "wall" before it, that conclusion
was half-right and half a shared blind assumption. This chapter is how we found the
other half — and it's the most *product*-shaped R&D in the repo, because the fix turned
out to live in the scoring and the control flow, not the model.

### The crack: the stereo trick was never tried on the blind-spot codecs

The stereo side-channel insight that beat the band-limited wall (previous chapter) was
only ever tested against **MP3**. But AAC, Opus and Vorbis also code stereo aggressively
(M/S per scalefactor band, intensity stereo, PNS) — the same family of artefact. Nobody
had run the decisive mono-vs-stereo probe on them. So we did
(`ml/aac_stereo_probe_features.py` + `_train.py`): 180 **full-range** authentics + their
transcodes, a compact CNN trained once on mid, once on mid+side, GroupKFold by source.

| codec     | mono (mid) AUC | stereo (mid+side) AUC | Δ side |
|-----------|----------------|------------------------|--------|
| mp3_128 (control) | 0.88   | 0.88               | −0.00  |
| aac_256   | 0.51           | 0.53                   | +0.03  |
| opus_128  | 0.74           | **0.83**               | +0.09  |
| vorbis_q5 | 0.69           | **0.80**               | +0.11  |

Two readings. The mp3_128 control's Δ≈0 is *not* a broken harness — on full-range
material the MP3 cliff is in the mono spectrum already, so the side channel adds nothing
(it only mattered for *band-limited* MP3, the previous chapter's regime). And the side
channel clearly helps Opus/Vorbis. AAC-256 looked like a genuine wall at 0.53.

> 💡 **Lesson (again)** — a probe is only as good as its operating point. This one read
> the **start** of every track (offset 0), where many songs are a quiet intro and the
> side channel is nearly silent. The production model reads the **middle**. The same
> start-vs-middle bug that has bitten this project twice already was quietly deflating
> the AAC number. We didn't trust 0.53 — we measured the real model.

### Measuring the model we actually ship

`ml/measure_v4_per_codec.py` runs the **exact production inference**
(`ml_classifier._compute_mel`: middle segment, 16-bit quant, per-channel norm) and the
bundled `cnn_v4_stereo.ts.pt` over the same 180 full-range sources:

| codec     | shipped-v4 ROC-AUC | recall @ 0.5 |
|-----------|--------------------|--------------|
| mp3_128   | 0.991              | 98.3 %       |
| aac_192   | 0.990              | 99.4 %       |
| **aac_256** | **0.945**        | 82.2 %       |
| opus_128  | 0.986              | 99.4 %       |
| vorbis_q5 | 0.984              | 98.9 %       |

The "near-undetectable" AAC-256 scores **0.945** for the real model — far above both the
probe's 0.53 (start-offset) and the docs' pessimism. EfficientNet-B0 on 65 k samples
finds what a tiny CNN on 180 start-clips couldn't.

> 💡 **The control that makes it believable.** A 0.95 AUC is worthless if the model is
> keying on a *pipeline* artefact (resample, dither, re-encode) rather than the codec. So
> `ml/measure_v4_passthrough_control.py` runs the same machinery with a **lossless** FLAC
> round-trip through ffmpeg as the "transcode" — same container/resample ops, no lossy
> step. Result: AUC **0.500**, predictions identical to the authentics (mean p 0.109 vs
> 0.109). The model ignores the pipeline entirely; the per-codec numbers are real. *Verify
> the inference path before you trust the metric* — for the third time in this README.

### So why did v0.14 say "Rule 12 barely moves AAC"? Two reasons, both fixable

If the model is this good, why were AAC verdicts unmoved? `ml/measure_r12_verdict_fullrange.py`
runs the **full 12-rule pipeline** and separates verdict-without-R12 (by subtraction) from
verdict-with-R12. Two mechanisms, neither of them the model:

1. **The score cap lands one point short.** The verdict thresholds are AUTHENTIC ≤ 30,
   WARNING 31–54, SUSPICIOUS 55–85. A full-range AAC transcode earns ~0 from the
   heuristics, and Rule 12 is capped at **+30** — which lands *exactly* on 30, the top of
   AUTHENTIC. A maximally-confident CNN detection on a silent file literally could not
   reach even WARNING. Off by one point.
2. **The fast path skips Rule 12 entirely.** To keep big scans fast, the calculator
   short-circuits on files the heuristics clear (score < 10, no MP3) and returns *before*
   Rule 12 ever runs. That's exactly the silent-heuristic profile of a high-bitrate AAC
   fake — so on a default scan the CNN never even looks at them.

### The fix: a WARNING floor, and an opt-in that lets it fire

Two small, honest changes (v1.2):

- **High-confidence WARNING floor** (`ml_classifier._WARNING_FLOOR_P = 0.90`). When the
  CNN is highly confident (p ≥ 0.90) on a full-range file the heuristics left silent, lift
  the verdict just to **WARNING** — never SUSPICIOUS. The model says "look here", it does
  not call the file a fake. We calibrated the threshold (`ml/calibrate_r12_threshold.py`,
  240 files): the authentic false-positive floor is ~3 % even at p ≥ 0.95, so this is a
  real specificity↔recall trade, not a free lunch — which is why it stops at WARNING.

  | p ≥ | authentic FP | aac_256 recall | vorbis recall |
  |-----|--------------|----------------|----------------|
  | 0.90 | 3.8 %       | 71.7 %         | 94.6 %         |
  | 0.95 | 2.9 %       | 60.0 %         | 84.6 %         |

- **`--deep`** runs Rule 12 on every file, bypassing the fast-path short-circuit (and so
  letting the floor fire). The default stays fast; `--deep` is the thorough pass.

Proof it works, on the real pipeline (`measure_r12_verdict_fullrange.py` with deep mode,
full-range, 36 sources/codec, WARNING count before → after):

| codec     | WARNING before | WARNING after | authentic cost |
|-----------|----------------|---------------|----------------|
| aac_256   | 1              | **22**        |                |
| vorbis_q5 | 1              | **29**        |                |
| opus_128  | 1              | 21            |                |
| *authentic* |              |               | +2 WARNING, **0 SUSPICIOUS** |

> 💡 **Lesson — a model can be capable and still inert.** The v4 CNN had separated these
> codecs since v0.14; two lines of plumbing (a +30 cap, a fast-path `return`) kept that
> ability from ever reaching a verdict. When a feature "doesn't work", check whether the
> code even *runs* it on the inputs it's meant for before you blame the model. The science
> was done a release ago; v1.2 is entirely a scoring-and-control-flow fix.

Reproduce it: `aac_stereo_probe_features.py`/`_train.py` (the probe), `measure_v4_per_codec.py`
(shipped-model AUC), `measure_v4_passthrough_control.py` (the confound control),
`calibrate_r12_threshold.py` (the operating point), `measure_r12_verdict_fullrange.py`
(verdict effect; set `R12_DEEP=1` for deep mode).

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
scp GPU_HOST:/root/flac-detective-ml/models/cnn_v4_stereo.ts.pt src/flac_detective/models/
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

---

# v1.8 — The audit that killed a rule, and the rule that replaced it

This chapter starts with a message from a competitor and ends with the project's
first detector that works at 320 kbps. The order matters: the second only became
measurable once the first was done.

## 0. The message

Jamie Dodd, who builds **Provir**, sent over a head-to-head benchmark on a corpus
of his own — 29 lawful sources, 800 constructed transcodes, 12 codecs, sha256
frozen, both tools on byte-identical inputs. He led on the review tier (10 codecs
to 2 ties); FLAC Detective led about 4x on convictions (123 of 714 against 30).
He documented five limitations of his own benchmark unprompted, including "it is
my corpus" and "these are constructed transcodes, not wild files", and he put a
Wilson bound on his own 0/29 false-positive row rather than quoting it as zero.

The benchmark was not the useful part. This was:

> I imported your Rule 9A (pre-echo) and ran it standalone on 364 files — it fires
> on 98.2 % of genuine and 98.6 % of fakes, AUC 0.517. Genuine median actually came
> out higher than fake. [...] I think the axis is just dead, and I'd rather tell you
> than watch you carry it.

He was right.

## 1. Rule 9 was a coin flip, and we could have known

Reproduced immediately on `ml/texture_probe.csv` — 480 files, 120 band-limited
genuine plus 360 transcodes, a corpus disjoint from his:

| Rule 9 test | AUC | fires on genuine | fires on fakes |
|---|---|---|---|
| 9A pre-echo | **0.513** | 82.5 % | 84.7 % |
| 9B HF aliasing | 0.586 | 6 % | 9 % |
| 9C MP3 noise pattern | **0.497** | ~0 % | ~0 % |

Two independent corpora, 0.513 against his 0.517. And it was worse than he could
see from standalone: **all three** of Rule 9's tests were at or near chance, not
just 9A.

*Why* 9A failed is worth keeping, because the physics it was built on is real.
MDCT codecs genuinely produce pre-echo. The implementation looked for HF energy
(10-20 kHz) in the 20 ms before each transient and called it pre-echo if it
exceeded 3x the file's median HF energy. Three problems, each fatal:

1. **Real music does that anyway.** A drum attack is not a wall; it ramps. The
   "before the transient" window catches the beginning of the actual attack.
2. **The reference was too low.** A file median that includes silences and quiet
   passages makes "3x the median" a bar that any loud moment clears.
3. **The band is empty in the accused.** A lossy file is cut near 16 kHz — the
   evidence was being sought exactly where the encoder had erased everything.

So it fired on ~everything and separated nothing, while adding **+15 points to
any genuine file that passed its gate**. With `SCORE_WARNING = 31`, that is an
effective bar of 16 for those files.

Ninety per cent of this was already in this README. The `mp3_pattern` incident
(see "Dead end #2" above) recorded that Rule 9C's noise test was a degenerate
near-constant with a meaningless pooled AUC of 0.99. That finding was correct,
was written down, and **never crossed from the ML study into the scoring table**.
The lesson is not "measure your features". It is *measure the thing you ship*.

## 2. So we measured everything: `ml/rule_audit.py`

Two pieces of new infrastructure:

* **Per-rule score attribution** (`ScoringContext.rule_scores`). Every
  `add_score` is credited to the rule executing it, so a file's verdict can be
  broken down into what each rule actually contributed. Exposed as
  `score_breakdown` on the analyzer result.
* **A frozen audit corpus** (`ml/build_audit_corpus.py`): 80 certified-genuine
  sources — EAC/XLD/Audiochecker ripper log present, **one per album**, because
  ten tracks off one CD are not ten observations — round-tripped through 9
  codecs weighted toward the high-bitrate end. 800 files.

The first run, on the twelve rules as they stood:

```
rule                            auc  n_gen  n_fake  fire_gen  fire_fake  mean_gen  mean_fake
Rule1MP3Bitrate               0.580     80     720     0.037      0.197      1.88       9.86
Rule2Cutoff                   0.660     80     720     0.075      0.389      0.61       3.59
Rule3SourceVsContainer        0.577     80     720     0.037      0.192      1.88       9.58
Rule424BitSuspect             0.500     80     720     0.000      0.000      0.00       0.00
Rule5HighVariance             0.500     80     720     0.000      0.000      0.00       0.00
Rule6HighQualityProtection    0.500     80     720     0.000      0.000      0.00       0.00
Rule8NyquistException         0.700     80     720     0.800      0.421    -36.25     -18.54
Rule9CompressionArtifacts     0.486      2     140     1.000      0.957     15.00      14.50   DEAD
Rule10Consistency             0.476      2      85     0.000      0.047      0.00      -1.18
Rule11CassetteDetection       0.321      3     174     1.000      0.994     18.33      11.18
Rule12MLClassifier            0.787     77     578     0.000      0.574      0.00      15.85
```

Rule 9 confirmed dead in-pipeline. But the audit found something nobody was
looking for.

## 3. Rule 11 was pointing the wrong way

**AUC 0.321.** Below 0.5 is not noise — it is *inverted*. Rule 11 handed genuine
files +18.3 points on average and transcodes +11.2.

Reading the code with that number in hand, the bug is obvious and had been there
since the rule was written. Rule 11 detects cassette sources: tape hiss, wow and
flutter, natural roll-off. Its output is **evidence of being a genuine analog
transfer**. It was being added straight to the *transcode* score. A strong signal
(>= 30) then earned a -40 bonus, so a clear cassette netted out roughly even —
but a *moderate* cassette signal, say 25, got the penalty and no bonus. Sounding
like a cassette made you look like a fake.

Five of the 80 genuine files were flagged. Two were analog-sourced African
reissues that Rule 11 had personally pushed upward; one more was a WARNING
sitting at exactly 31, composed of Rule 9's free +15 and Rule 11's +5.

The fix: Rule 11 contributes **zero** points and records its evidence in
`context.cassette_score`, which the calculator reads to cancel Rule 1 and apply
the protection bonus. Its test 11C ("no MP3 pattern -> +15") went too — it keyed
off Rule 9C, so it was a constant wearing the costume of evidence; the cassette
gate dropped 30 -> 15 to compensate exactly, leaving every real test at its
original weight.

Two of the tests covering Rule 11 had been skipped for a year behind a
"TODO: rewrite mocks". They are rewritten, and one now pins the contract:
`test_rule_11_never_penalises_the_score`.

## 3b. And a third bug, from the same instrument

Once every rule's contribution was visible per file, this showed up:

```
AAC 320k     score=45  {'Rule8NyquistException': -50, 'Rule13MDCTAlignment': 45}
```

Minus fifty plus forty-five is minus five, not forty-five. `add_score` clamped the
running total at zero on **every** addition, and Rule 8 — which the pipeline
calculates *first*, by explicit design — contributes −50 to a genuine full-band
file. That −50 was erased the instant it was added, before anything could be
offset against it.

So every protection rule that happened to run before a penalty was inert. The
architecture said "protect authentic files first"; the arithmetic said otherwise.
The clamp now happens once, on the final score.

Worth noting how this was found: not by reading the code, and not by a failing
test. By building an instrument that shows what each rule contributed, then
looking at a number that didn't add up. Three bugs — a dead rule, an inverted
rule, and a destroyed protection — all invisible in a total, all obvious in a
breakdown.

## 4. The structural fix: you cannot ship an unmeasured rule

`tests/test_rule_audit_guard.py` runs in CI against the committed audit CSV — no
corpus needed — and fails if:

* a `ScoringRule` subclass exists in the code but not in the audit
  (**this is the one that matters**: add a rule, re-run the audit or CI stops you),
* any rule that fires on >= 10 % of files has |AUC - 0.5| < 0.05,
* any rule hands genuine files more than 2 points on average without discriminating.

Rule 9 would have failed all three on the day it was written.

## 5. Rule 13 — the 320 kbps wall, and a way through it

The section "Where the whole tool is blind (own it)" above is honest and was, for
its method, correct: everything the tool did looked above the cutoff, and at
256-320 kbps there is nothing up there. The audit put a number on it — **17.5 %
of 320 kbps AAC flagged at all** — and Jamie's benchmark independently measured
28 %.

Jamie also pointed at the way out: Derrien, JAES 67(3) 2019 — MDCT
quantisation-residual with an analytic null — plus the implementation trap that
cost him a day. **ffmpeg-family AAC uses a KBD window with alpha = 4 for long
blocks, not sine; with a sine analysis window the statistic reads at the floor.**

The mechanism (`src/flac_detective/analysis/new_scoring/mdct.py`): an MDCT codec
quantises coefficients, and quantisation sends many of them to exactly zero.
Those zeros survive decoding. Re-analyse with the *same* transform — same
2048-sample window, same KBD shape, same sample-exact alignment — and they
reappear as deep spectral holes; analyse at any other alignment and they smear
away. The statistic is not "how many holes" but **peak ratio**: hole density at
the best alignment over the median across unrelated alignments. Genuine audio has
no preferred alignment, so its curve is flat near 1.0. That is the analytic null.

Measured on the audit corpus (`ml/mdct_probe.py`):

| codec | n | median peak ratio | AUC |
|---|---|---|---|
| aac_ff128 | 80 | 19.57 | **0.998** |
| aac_ff256 | 80 | 21.51 | **0.990** |
| aac_ff320 | 80 | 13.60 | **0.993** |
| aacmf_256 | 80 | 2.66 | 0.791 |
| vorbis_q8 | 80 | 1.42 | 0.806 |
| opus_256 | 80 | 1.26 | 0.526 |
| mp3_V0 | 80 | 1.25 | 0.457 |
| mp3_320 | 80 | 1.24 | 0.438 |
| mp3_192 | 80 | 1.23 | 0.399 |
| **genuine** | **80** | **1.25** (p95 1.37, max 1.42) | — |

The separation is not marginal. No genuine file exceeded 1.42; ffmpeg AAC sits at
13-21 regardless of bitrate. 234 of the 240 ffmpeg-AAC files peaked at the *same*
offset (1020), which is the encoder delay showing through — a confirmation that
the statistic reads what it claims to read.

### What it does not do, stated as plainly as the wins

* **MP3 and Opus score at the null.** They do not use a 2048-sample MDCT long
  block, so this hypothesis does not fit them. That is fine — the cutoff rules
  already convict there — but Rule 13 is an *AAC* answer, not a universal one.
* **MediaFoundation AAC is only half-caught** (AUC 0.791, bimodal: p25 = 1.27,
  p50 = 2.66). A different AAC encoder makes different windowing decisions.
  Reading the ffmpeg numbers as "AAC is solved" would be over-reading; what is
  solved is *ffmpeg-family AAC*, and the MediaFoundation column is in the corpus
  precisely so that distinction cannot be quietly lost.
* **Very aggressive quantisation defeats it.** Above ~60 % zeroed coefficients
  the +/-16-bin median reference is itself zero and the statistic collapses. That
  means very low bitrates — where the spectral cliff is obvious anyway. Pinned by
  `test_extreme_zeroing_defeats_the_median_reference`.
* **This is still a constructed corpus.** Same limitation Jamie flags about his:
  clean source -> encoder -> FLAC, with no mastering stage after the codec.

### The fix that broke the fix

Removing the per-addition clamp (§3b) was correct, and it immediately cut 320 kbps
AAC detection from **97.5 % back down to 26.2 %**.

The cause is not a bug in either rule — it is the two rules disagreeing, and the
clamp having hidden the disagreement. Rule 8, the Nyquist exception, grants −50 to
a file whose spectrum runs to Nyquist, reasoning that a transcode would have left
a cliff. That reasoning is precisely what stops holding at 256–320 kbps. Rule 8
had been arguing "no cliff, therefore genuine" about the exact population Rule 13
exists to catch — and once the clamp stopped erasing it, it won: −50 + 55 = 5,
AUTHENTIC.

Rule 8 is an *absence of evidence* argument. Rule 13 produces direct positive
evidence: the encoder's own quantisation grid, at one sample-exact alignment, an
order of magnitude above the file's own baseline. So the resolution is precedence,
not a points arms race — when Rule 13 fires, Rule 8's protection is explicitly
withdrawn, with a reason string saying so. `TestRule8Precedence` pins both
directions: withdrawn when Rule 13 has evidence, untouched when it doesn't.

The general lesson is the one this whole chapter keeps repeating: **a rule that
never fires can hide a rule that is wrong.** Rule 8's protection had been dead
weight since the clamp was written, so nobody ever had to decide what it should
do when it disagreed with new evidence. Fixing an unrelated bug forced the
question.

### Cost

An exhaustive 24-frame scan of all 1024 offsets is ~24 s per file. The peak is
sharp enough that a 3-frame triage ranks the true alignment first on every AAC
transcode measured, so stage 1 triages cheaply and stage 2 re-measures only the
survivors plus a spread of baseline offsets: **~4 s per file**. Gated to
cutoff >= 18 kHz and files not already convicted, since below that the cheap
rules already have signal.

## 6. Where v1.8 lands, and the next thing the audit found

Same corpus, same 800 files, before and after:

| | before | after |
|---|---|---|
| genuine flagged (false positives) | 6.2 % | **3.8 %** |
| AAC 320 kbps (ffmpeg) flagged | 17.5 % | **97.5 %** |
| AAC 256 kbps (ffmpeg) flagged | 50.0 % | **98.8 %** |
| AAC 256 kbps (MediaFoundation) flagged | 70.0 % | **88.8 %** |
| all fakes flagged | 60.3 % | **76.0 %** |
| all fakes convicted | 19.9 % | 19.7 % |
| rules at chance while firing | 1 | **0** |

Rule 13 contributed to **0 of the 80 genuine files**. Convictions are flat, which
is the intended shape: Rule 13 is calibrated to reach SUSPICIOUS on its own and
no further.

### The wild check — Rule 13 on material from outside the library

The 880-file calibration set is all my own certified rips. Same mastering
conventions, same era mix, same ripper. So: 180 FLACs pulled from the Internet
Archive `etree` collection (74 distinct concerts, taper recordings licensed for
redistribution), run through the full pipeline. These are *deliberately* hostile —
audience recordings, room noise, wildly variable capture chains, nothing like a
CD master.

**Rule 13 scored zero points on all 178 usable files.** It ran on 162 of them and
abstained or returned below-threshold on every single one; the other 16 didn't
pass its cutoff gate.

Combined with the certified sweep, that is **0 of 1058 genuine files scored by
Rule 13 — Wilson-95 upper bound 0.36 %**.

The overall pipeline flagged 20 of 178 (11.2 %, Wilson-95 7.4–16.7 %), against a
historical 13.3 % on a 45-file pull. None of it is Rule 13's doing.

> A reporting bug is worth recording here, because it nearly buried the result.
> The first summary read "Rule 13 contributed to 162 files" — the check treated a
> contribution of integer `0` as "not empty" and counted every file the rule *ran*
> on. A clean 0/178 printed as its own opposite. Distinguish "did not run" from
> "ran and abstained", always.

### The next one, stated with its numbers rather than fixed in a hurry

Three genuine files are still convicted, all with the same signature:

```
FAKE_CERTAIN  score=102  {Rule1: 50, Rule2: 2,  Rule3: 50}
FAKE_CERTAIN  score=100  {Rule1: 50,            Rule3: 50}
FAKE_CERTAIN  score=111  {Rule1: 50, Rule2: 11, Rule3: 50}
```

Rules 1 and 3 fire together on 141 of the 800 files, and in **141 of those 141
cases they contribute the identical value**. That is not two pieces of evidence;
Rule 3 reads `mp3_bitrate_detected`, which Rule 1 produced. One inference is
convicting twice, and 100 points clears the 86-point conviction bar by itself.

The tempting fix is wrong. Simulated on this corpus, discounting Rule 3 whenever
Rule 1 has already fired takes genuine convictions from **3/80 to 0/80** — and
takes fake convictions from **142/720 to 4/720**. The conviction tier *is* that
pair. The 86-point threshold was implicitly calibrated around a 100-point
double-count, so removing the double-count means recalibrating the threshold,
which needs its own measurement rather than a one-line change made at the end of
a long day.

Logged here with the numbers so the next person starts from evidence instead of
from the same temptation.

The wild run then made the case stronger, not weaker. Its two false convictions
(both tracks of one audience recording, `lf2025-05-28`) have the identical
signature:

```
FAKE_CERTAIN  score=106  {Rule1: 50, Rule2: 6, Rule3: 50}
FAKE_CERTAIN  score=105  {Rule1: 50, Rule2: 5, Rule3: 50}
```

So across two independent corpora — 258 genuine files, 80 certified CD rips and
178 wild taper recordings — this tool has produced **five false convictions, and
all five are Rule 1 + Rule 3 contributing +50 each**. That is not a scattering of
edge cases. It is one mechanism, and it is the only mechanism currently capable of
falsely convicting anyone.

---

# v1.9 — Conviction needs two independent sources

v1.8's harness measured each rule alone. Jamie Dodd pointed at the layer above:
**nothing was measuring rule combinations.** A score is a sum, and a sum cannot
say whether it came from one thing repeated or several things agreeing.

The audit data already contained both cases.

**One thing repeated.** All three false convictions on the 80 certified-genuine
files, and all 26 convictions on the 320 kbps MP3 arm, were Rules 1 and 3 at +50
each. Rule 3 compares the bitrate Rule 1 inferred; Rule 4 gates on the same
inference. One measurement wearing several hats, clearing 86 unaided.

**Several things agreeing, and losing.** 90 files carried agreement between Rule
12 (learned mel-spectrogram model) and Rule 13 (MDCT frame alignment), and **54
of them sat at exactly 85** against that same bar.

So conviction moved from a score threshold to a corroboration gate: two
independent evidence families required (`spectral`, `container`, `silence`,
`cnn`, `mdct`), with protection rules and the segment-consistency rule excluded
by construction.

## The trap inside the fix

The pipeline used to stop as soon as the score passed 86 — before Rules 12 and 13
ran. Under a corroboration gate that is self-defeating: the early exit
*guarantees* a single family, so the gate would have been measuring the
short-circuit rather than the evidence. Early exits now require corroboration
too. That is why the MP3 arm barely moved (32.5 % → 31.2 % convicted) instead of
collapsing to 2 % as a naive simulation predicted: those files now reach the
rules that can corroborate them.

## Choosing the corroborated bar — and why the certified corpus would have got it wrong

With two families required, what points bar should a conviction need? Simulated on
the 80 certified-genuine files, the answer looked obvious: **zero** of them ever
reached two families, so any bar was safe, and the lowest bar caught the most
fakes (196 of 720 at a bar of 31).

Then the same question was put to 178 wild Internet Archive recordings.

**Eighteen of them reach two families.** Audience recordings with a low rolloff
give `spectral` points, and the CNN fires on the same material. Their scores:

```
  0, 0, 0, 0, 10, 18, 31, 31, 31, 31, 32, 32, 32, 32, 33, 33, 38, 41
```

| corroborated bar | false convictions, 178 wild genuine files |
|---|---|
| 31 | **12 (6.7 %)** |
| 40 | 1 |
| 45 | 0 |
| **55 (shipped)** | **0**, with 14 points of margin |

The bar that the certified corpus called free would have convicted one wild file
in fifteen. Same lesson the whole exchange keeps returning to: a corpus of one
provenance cannot price a population of another, and the only defence is to go
and measure the other one.

## Result

Same 800 files, v1.8 → v1.9:

| | v1.8 | v1.9 |
|---|---|---|
| fakes convicted | 142 | **177** |
| genuine convicted (audit corpus) | 3 | **0** |
| genuine convicted (wild, 178 files) | 2 | **0** |
| convictions resting on one family | 142 | **0** |
| AAC 256k (ffmpeg) convicted | 2.5 % | **58.8 %** |
| flag rates, both classes | — | unchanged |

Across both corpora, **0 false convictions in 258 genuine files** (Wilson-95
upper bound 1.47 %), against 5 before. Every surviving conviction carries two
families: 90 `cnn+spectral`, 82 `cnn+mdct`, 5 all three.

## Cost

Scans are slower. The cheapest fast path in the pipeline — "score is already 86,
stop" — is gone for uncorroborated files, which is precisely the population that
needed the expensive rules in order to be judged fairly.


---

# v1.10 — What the blind exchange found, and what Rule 3 had been doing all along

v1.9 shipped with "0 false convictions in 258 genuine files". Jamie Dodd then
built a **599-file hash-keyed exchange set** — his sources, his labels, scored by
both tools without either seeing the other's answers — and the very first
genuine file it disagreed on broke that record.

## 1. The gate counted a witness that was barely speaking

A genuine 2003 audience recording, convicted FAKE_CERTAIN:

```
score=128  {spectral: 112, cnn: 16}   ->  two families  ->  FAKE_CERTAIN
```

The gate asked "how many families?" and got "two". It never asked how much the
second one actually said. 16 points of CNN — a reading the CNN itself would not
have acted on — was legitimising 112 points of doubled spectral evidence.

`MIN_FAMILY_CONTRIBUTION = 20` fixes it. The same file now reads:

```
score=78   {spectral: 78}             ->  one family   ->  SUSPICIOUS
```

The threshold is not tuned to this file. It is set just above the band where a
family's contribution is a single low-confidence rule firing at its floor.

## 2. Rule 3 never once fired alone — measured, across 978 files

The v1.8 audit flagged Rules 1 and 3 as redundant and the v1.9 gate neutralised
them as a *pair*. What nobody had checked is whether Rule 3 ever contributed
anything on its own. Counted across the 800-file audit corpus plus the 178-file
wild scan:

| | count |
|---|---|
| Rule 3 fired | 143 |
| ...alongside Rule 1 | **143** |
| ...alone | **0** |

Not "mostly redundant". Redundant, every single time, in 978 files. Deleted in
v1.10 along with its constant and its tests.

Removing it costs six convictions across 800 files (177 -> 171) and improves the
flag rate (76.0 % -> 78.8 %). The convictions it cost were ones where its echo of
Rule 1 was carrying a weak family over the corroborated bar.

## 3. Rule 13 tries two windows now

ffmpeg AAC uses a KBD (alpha = 4) window; Vorbis uses
`sin(pi/2 * sin^2(pi/N * (n+0.5)))`. Same 2048-sample long block, different
shape. v1.9 tested only the first, which is why the Vorbis arm read AUC 0.806
while the AAC arms read 0.99. v1.10 tries both and takes the stronger reading.

| arm | v1.9 AUC (KBD only) | v1.10 AUC (KBD + Vorbis) |
|---|---|---|
| vorbis_q8 | 0.806 | **0.955** |

The cost is one number: across the same 80 certified-genuine files the maximum
moved from 1.42 to **1.427** (median 1.25 -> 1.28, p95 1.37 -> 1.39), against a
review bar of 2.0. Genuine audio has no preferred alignment under
*either* window, so a second hypothesis is close to free — which is exactly what
makes the statistic worth having.

**Opus stays out of reach, and this is physics, not a missing feature.** CELT
transforms at 48 kHz whatever the input, so a 44.1 kHz source is resampled in and
back out, and resampling destroys the sample-exact alignment. Measured on the
opus_256 arm: **1.26, against a genuine baseline of 1.29.** There is no threshold
between those two numbers. Recorded here so nobody spends a week looking for one.

## 4. The lesson, for the third time: independence must be measured

Rules 1 + 3 were assumed independent. The `cnn` and `spectral` families were
assumed independent. Both assumptions were wrong, and both were only found by
counting co-fires. `tests/test_rule_audit_guard.py` now fails the build when any
two families co-fire beyond `MAX_INDEPENDENCE_LIFT`, so the fourth instance gets
caught by CI rather than by a competitor.

## Result

Same 800 files, v1.9 -> v1.10:

| | v1.9 | v1.10 |
|---|---|---|
| fakes flagged | 76.0 % | **78.8 %** |
| genuine flagged | 3.8 % | 3.8 % |
| genuine convicted | 0 | **0** |
| fakes convicted | 177 | 171 |
| convictions on one family | 0 | 0 |

On the blind exchange set, all 599 files re-scored against Jamie's labels
(`ml/fd110_on_exchange.csv`; hashes in `ml/exchange/MANIFEST.sha256`):

| arm | n | convicted | flagged |
|---|---|---|---|
| **genuine** | 59 | **0** | 2 (3.4 %) |
| `aac_ff128` | 59 | 18 | 31 (52.5 %) |
| `aac_ff256` | 59 | 18 | **59 (100 %)** |
| `aac_ff320` | 59 | 10 | **59 (100 %)** |
| `aacmf_256` | 58 | 20 | 24 (41.4 %) |
| `mp3_192` | 59 | 22 | 29 (49.2 %) |
| `mp3_320` | 59 | 15 | 20 (33.9 %) |
| `mp3_V0` | 59 | 4 | 8 (13.6 %) |
| `opus_256` | 59 | 5 | 14 (23.7 %) |
| `vorbis_q8` | 59 | 32 | 42 (71.2 %) |

*Corrected 2026-08-18. The set's 599 files are **589 distinct files**: ten
byte-identical pairs, which are one entire source group — all ten arms — present
twice under two names. Two archive.org items held the same taper's same track
(`…-matrix-…` and `…-matrix2-…`) and the corpus dedup keyed on the item
identifier rather than on the audio. Rates above are over distinct content; the
originally published table used n=60 per arm and double-counted that recording in
every arm, including genuine. Nothing material moved — the largest shift is
`mp3_V0` convictions, 8.3 % → 6.8 % — and 0/59 genuine reads as "up to 6.1 %"
(Wilson-95) against the 6.0 % published on n=60. Found by Jamie Dodd, by sorting
our own shipped manifest.*

The prediction published to Provir *before* scoring — "aac_ff256 >= 90 %
flagged, high confidence" — landed at 100 %. The Vorbis prediction — "small
gain, < 15 pp, medium confidence" — was too pessimistic; the second window
hypothesis is what moved it.

0/60 reads as "up to 6 %" at Wilson-95, not "zero".


## A fifth lesson, learned from the other side of the exchange

On 2026-08-17 Jamie found that his arm-2 spec no longer matched the SHA-256 he
had published with it. He could not show what had changed, because the pre-edit
file had never been committed — the copy we were holding was briefly the only
authoritative version of the thing he had sealed. He then found his own sent
attachment still in the thread, and the diff turned out to be one token:

```
- ... the PROJECT ffmpeg (D:\Projects\VerifID\ffmpeg.exe, sha256 already in ...
+ ... the PROJECT ffmpeg (D:\Projects\Provir\ffmpeg.exe,  sha256 already in ...
```

A project-wide rename had gone through 377 files and reached the sealed spec.
Nothing scoreable moved; the changed token is a directory name inside a
parenthetical describing a binary that the same sentence identifies by hash.

Two failure modes worth stealing, because this project had both:

* **A bulk rename is a content edit to every sealed document it touches.** A
  find-replace does not know which of its targets were evidence.
* **Publishing a hash is worth nothing if you don't commit the bytes in the same
  action.** His chain survived on a retention policy, not a provenance chain.

Checked here immediately, and the second one applied: `MANIFEST.sha256` for our
own 599-file exchange side was sitting in the **gitignored** `Temp/` directory
next to the 3 GB of audio it describes. Any cleanup would have destroyed the only
record of what we sealed. Full re-verification against the frozen audio came back
**599 checked, 0 missing, 0 divergent**, and the manifest is now committed at
`ml/exchange/MANIFEST.sha256` with its own self-hash recorded next to it.

The answer key stays out, as it always has (`*-LABELS.json` in `.gitignore`).
The manifest is precisely the artefact that lets the other side verify integrity
*without* the key.


---

# Eligibility, not the observed rate — and what it says about our own corpora

Jamie Dodd's second lesson from Provir's corroboration bug, and the best
methodological idea to come out of the exchange:

> You have one false conviction because you ran one corpus. I stopped counting
> the convictions I'd made and started counting the files that were *eligible* to
> receive one.

Measured here over the same 258 genuine files the "0 false convictions" claim was
made across — 80 certified CD rips plus 178 wild taper recordings
(`ml/eligibility_258.csv`).

## The exposure

| | count |
|---|---|
| genuine files analysed | 258 |
| **convicted** (the observed rate) | **0** |
| clear the 55-point bar with one qualifying family | **2** (0.78 %) |
| ...of those, second family already partly formed | **0** — both need a whole family |
| carry *any* second positive family | **18** (7.0 %) |
| ...of those 18, second family below the 20-point floor | **18, all of them** |
| strongest runner-up family on any genuine file | **12 points** (floor is 20) |

So the tightest margin measured anywhere on 258 genuine files is **8 points**, and
nothing is sitting at 19. The two files that clear the points bar need an entire
second evidence family, not a nudge.

## The uncomfortable part

Re-running both gates over the same corpus:

| rule | genuine convicted, n=258 |
|---|---|
| v1.9 (any positive family counts) | **0** |
| v1.10 (family must contribute ≥ 20) | **0** |

**Our own corpora could not have found the bug.** The false conviction that
produced `MIN_FAMILY_CONTRIBUTION` is invisible here — under the *old* rule these
258 files still convict nobody. 18 of them carried the two-family pattern that
licensed it, and not one of those 18 also cleared 55 points. The engine was not
safer on this material; the material simply never lined up.

That is Jamie's point stated as a measurement rather than as advice. An observed
false-conviction count is a property of the corpus you happen to own, and no
amount of re-running it will surface what it cannot contain. The 8-point margin
above is worth more than the two zeros in that table, because it is the only one
of the three numbers that describes the *engine* rather than the record
collection.

It is also the argument for blind exchange, made against our own interest: the
defect was found by material we did not choose, could not have chosen, and did
not see the labels for.


---

# Paired discrimination: does a transcode beat the file it came from?

Every AUC in this README pools all fakes against all genuine files. That answers
"can the engine separate this population from that one", which is not the question
a user has. A statistic tracking *material* rather than *processing* — loud versus
quiet, dense versus sparse — could post a fine pooled AUC while being unable to
tell one recording from its own transcode. Nothing here had ever checked.

The test arrived sideways, from Jamie Dodd using the corpus's cluster structure for
something else. He derived bounds on his own accuracy without an answer key from
"exactly one file in ten is genuine": a cluster cannot hold two genuine files, so
two clear verdicts in one cluster means a transcode was called clean. The audit
corpus has the identical shape — 80 sources times 10 arms — and the same grouping
supports a stricter test than the bounds he needed it for.

`ml/paired_discrimination.py`, run on the v1.10 audit scores:

| arm | beats its own genuine | tied | loses | win rate |
|---|---|---|---|---|
| `aac_ff256` | 79 | 1 | 0 | **98.8 %** |
| `aac_ff128` | 78 | 0 | 2 | 97.5 % |
| `aac_ff320` | 78 | 2 | 0 | 97.5 % |
| `vorbis_q8` | 74 | 6 | 0 | 92.5 % |
| `aacmf_256` | 73 | 5 | 2 | 91.2 % |
| `opus_256` | 73 | 5 | 2 | 91.2 % |
| `mp3_192` | 72 | 6 | 2 | 90.0 % |
| `mp3_320` | 58 | 22 | 0 | 72.5 % |
| `mp3_V0` | 49 | 29 | 2 | 61.3 % |

**The discrimination is real, not a material effect.** Every arm's paired win rate
tracks its pooled AUC, and ranking *failures* — a genuine recording scoring above
its own transcode — never exceed 2 files in 80 on any arm. That is the reassuring
result, and it had been assumed rather than measured for the life of the project.

**The failures and the silences are different things, and only pooling hid it.**
`mp3_V0` reads 0.788 pooled and 61.3 % paired, which looks like a collapse until
the columns are separated: 29 of its 80 are *ties*, not losses. A tie is the engine
scoring a transcode and its source identically — almost always zero and zero. That
is a blind spot, not an error, and it points somewhere specific: V0 and 320 kbps
MP3 are where the engine most often has nothing to say about either file, rather
than where it says the wrong thing. Rule 13 does not fit MP3 geometry and the
cutoff rules find nothing at those rates, so both files come back silent.

Worth running against any future rule before its pooled AUC is believed.

## Also checked, and clean

The exchange set's duplicate-source defect raised the obvious question about our
own corpora, since the calibration corpus is sampled from the same library and the
same identifier-based dedup habits. Checked: **0 byte-identical pairs among the 877
re-certification files**, and 80 distinct sources in the audit corpus.

The check is cheap and has no false negatives — identical audio produces identical
statistics, so any duplicate pair must appear as a repeated `(ratio_kbd,
ratio_vorbis)` signature. Seven signature collisions turned up; hashing all
fourteen files showed every one to be a coincidence of a statistic that takes
discrete values, not duplicated content. The published calibration stands.


---

# MP3 geometry: a negative result, and what it cost to make it a real one

The paired-discrimination table localised a blind spot rather than an error: on
`mp3_V0`, 29 of 80 transcodes score *identically* to the file they came from, and
on `mp3_320`, 22 of 80. Tied at zero and zero. The documented reason for never
pursuing MP3 with Rule 13 — "the cutoff rules already convict there" — is
measurably false at those bitrates.

And unlike Opus there is no physical barrier. Opus is unreachable because CELT
transforms at 48 kHz whatever you feed it, so the sample-exact alignment dies in
resampling. **MP3 does not resample.** The alignment survives; it lives at a
different period — a 576-sample granule and a 1152-sample frame, not 2048.

So: is Rule 13 simply looking on the wrong grid? `ml/mp3_geometry_probe.py`.

## The answer is no, and it is now unambiguous

| arm | mp3_frame_1152 | mp3_granule_576 | aac_2048 |
|---|---|---|---|
| genuine (median) | 1.696 | 1.917 | 1.524 |
| `aac_ff256` | 1.680 (AUC 0.52) | 1.917 (0.45) | **18.29 (1.00)** |
| `mp3_192` | 1.750 (0.79) | 2.000 (0.51) | 1.535 (0.52) |
| `mp3_320` | 1.667 (0.54) | 1.917 (0.42) | 1.524 (0.57) |
| `mp3_V0` | 1.708 (0.61) | 1.917 (0.50) | 1.533 (0.50) |

A plain MDCT at MP3's own period reads MP3 at the null. The `mp3_192` cell at 0.79
was the one thing that might have been signal, so it was chased down with a
bitrate gradient on a single material set (`--gradient`): encode the same ten
sources at 64 / 96 / 128 / 192 / 320 kbps and read all five at 1152/576.

```
 bitrate    median     AUC
     64k     1.676    0.41
     96k     1.702    0.57
    128k     1.745    0.62
    192k     1.735    0.67
    320k     1.717    0.58
```

Flat. At 64 kbps MP3 zeroes a large fraction of the spectrum, and the basis still
reads 0.41. There is no gradient, so the 0.79 was sampling noise on n=25, and the
conclusion is not "too few zeros to see" but **the plain-MDCT basis cannot see MP3
quantisation at all**, however much of it there is.

That is a stronger and more useful negative than the one the corpus run alone
would have supported. MP3's zeros live in a hybrid domain — a 32-band polyphase
filterbank *followed* by an 18-point MDCT — and the synthesis bank smears them
across 512 taps on the way out. A plain time-domain MDCT at the same period does
not project onto that, and matching only the period is not enough.

**What is left open, and why it is not being built.** The real MPEG-1 Layer III
analysis filterbank remains the only way in, and this result does not rule it out
— it rules out the cheap approximation of it. But the case for spending a week on
the filterbank is now purely theoretical: nothing measured says the structure is
recoverable, only that it must exist somewhere. This project's own rule is not to
spend a week on a hunch, so it is recorded here instead, the way Opus was.

## Two controls, and only one of them was enough

The probe carries a synthetic control — audio with holes imposed on a known grid —
and it passed cleanly, firing 40x at the matching geometry and 1.4x at the others.

It passed while the probe was still wrong. The first corpus run read `aac_ff256`
at **AUC 0.52** where this project's shipped rule reads 0.99, because the probe
analysed everything with a sine window and ffmpeg's AAC uses KBD (α=4) — the exact
trap that cost Jamie Dodd a day and that produced Rule 13 in the first place. The
synthetic control could not catch it: holes imposed with a sine window are of
course found with a sine window. **A probe that only validates against material it
made itself validates its own assumptions.**

With the window fixed per geometry, the same control material reads
`aac_ff256` at median 18.29 and AUC 1.00 against a documented 21.5 and 0.99 — and
the MP3 nulls become interpretable, because the instrument has now reproduced an
answer the project already knew. That check is wired into the probe's own output
(`CONTROL_MIN_AUC`), so a future run refuses to be read if it cannot reproduce it.


---

# Scoring Provir's blind return, and what its evidence column gave away

Jamie Dodd's 599 verdicts, frozen and hash-published before our labels existed
(`ml/exchange/provir_return_2026-08.csv`, 103 convicted / 450 flagged / 46 clear).

## His pre-registered bounds, scored

He derived these from the corpus's counting structure alone — exactly one file in
ten is genuine, so a cluster cannot hold two genuine files nor ten transcodes —
without any answer key, and published them before asking to be scored.

| bound | claimed | actual | |
|---|---|---|---|
| false convictions | 0 – 9 | **0** | holds |
| genuine cleared | ≤ 43 / 60 | **43** | holds, exactly |
| genuine not cleared | ≥ 17 | **17** | holds, exactly |
| transcodes called clean | ≥ 3 | **3** | holds, exactly |
| transcodes flagged or convicted | 91.5 – 99.4 % | **99.443 %** | holds, exactly |

Every bound holds, and four of the five sit precisely on their limit. That is not
luck: it means the counting constraint was **tight**, and that every one of his 46
clear verdicts that *could* have been a genuine file, was one. The argument
extracted essentially all the information available without the key.

Zero false convictions among 103. His own null model — an engine with no
within-cluster discrimination at all — expected 2.8.

## Head to head, 589 distinct files

| | Provir | FLAC Detective v1.10 |
|---|---|---|
| genuine cleared | 43/59 (73 %) | **52/59 (88 %)** |
| **false convictions** | **0** | **0** |
| transcodes not cleared | **527/530 (99.4 %)** | 432/530 (81.5 %) |
| transcodes convicted | 103/530 (19.4 %) | **144/530 (27.2 %)** |

Neither dominates, and the shape of the difference is the interesting part. He
detects far more broadly and pays for it on genuine material; we clear real
recordings more often and convict harder when we do commit. Per arm, he is at
97–100 % everywhere. We match him at 100 % on `aac_ff256` and `aac_ff320` and fall
behind on `opus_256` (49 %), `aacmf_256` (74 %), `mp3_320` (75 %), `mp3_V0` (78 %).

## Opus is not a hole in the map, and his own return says so

He proposed last week that Opus is a cell where both families fail for independent
reasons — his edge tell fires on only 6 of 64 Opus files, ours dies to resampling —
and offered it as a genuinely open hole.

His return contradicts him. He does not merely flag 100 % of the Opus arm; he does
it on evidence that has nothing to do with the flag he was looking at, and nothing
to do with the sample-rate leak documented in `ml/exchange/README.md`:

| his flag, on `opus_256` | fires | on genuine |
|---|---|---|
| `HF_SEAM` | **100 %** | 8 % |
| his MP3 conjunction | 98 % | 0 % |
| `STEREO_AAC_DOUBT` | 95 % | 13 % |
| `OPUS_EDGE_FIRE` (the one he was watching) | 30 % | 0 % |

Not one of the 60 rests on the weak flags alone. So Opus is readable, decisively,
by an observable neither of us was discussing — and our own "Opus is out of reach"
remains true only of *Rule 13's alignment statistic*, not of the problem.

## What that says to build next

`HF_SEAM` fires on 100 % of Opus and 97 % of `mp3_320` against 8 % of genuine —
the two arms where our engine is weakest, from a statistic that does not depend on
frame alignment at all and therefore survives resampling. That is a far better
evidenced next step than the MP3 filterbank, which this project has just measured
into a dead end.

`AAC_LATTICE` is the other one worth noting: 78 % on `aacmf_256` and `aac_ff320`,
**0 % everywhere else**. Clean and specific, and it is the residual-against-the-
reconstructed-transform he offered to explain.


---

# Four chantiers, 2026-08-18: one win, one honest failure, two foundations

## 1. The HF seam — FAILED its pre-registered bar, twice

Provir's `HF_SEAM` fires on 100 % of the Opus arm and 97 % of `mp3_320` against 8 %
of genuine files — precisely where this engine is weakest. The bar was set before
measuring: beat our current rates on those two arms at under 10 % genuine fire.

**Hypothesis 1 — a step in the time-averaged spectral envelope, below the cutoff.**
`ml/hf_seam_probe.py`. Both controls pass: an imposed 6 dB seam reads 41.2 against
5.97 for smooth noise and is located to within 12 Hz, and band-limited material
reads 5.3–5.6, i.e. the statistic ignores the cliff and is not Rule 2 in disguise.
On real transcodes it is flat: **AUC 0.47–0.50 on every arm**, fire rates identical
to genuine.

**Hypothesis 2 — the band edge jitters frame to frame.** Better, still short:
`mp3_V0` AUC 0.80, `aacmf_256` 0.73 — our two weakest arms after Opus — but only
13 % fire on Opus and 3 % on `mp3_320`. Nowhere near the bar.

**Conclusion, stated plainly: we do not know what `HF_SEAM` measures, and guessing
is not converging.** The instrument works — its controls say so — so these are
nulls about our hypotheses, not about the probe. Asking is one message and he has
never refused. Recorded rather than quietly dropped, because the band-edge jitter
result is a real lead on `mp3_V0`, the arm where paired discrimination is worst.

## 2. The lattice — WORKS, and beats holes where holes are weakest

`ml/lattice_residual_probe.py`. Read the grid rather than its zeros: AAC quantises
in a companded domain, so surviving coefficients cluster near multiples of a step
even when nothing was zeroed. Measured as a Rayleigh periodicity statistic per
(frame, band), normalised by the analytic null.

| arm | median | AUC | fires (bar = genuine p90) |
|---|---|---|---|
| genuine | 1.035 | — | 13 % |
| `aac_ff256` | 2.067 | **0.98** | 93 % |
| `aacmf_256` | 1.295 | **0.83** | 73 % |
| `opus_256` | 1.032 | 0.48 | 20 % |

**0.83 on MediaFoundation against the hole statistic's 0.791** — a different
observable doing better on the encoder where holes are weak. And it needs no zeros,
which is why it is the candidate for CoreAudio.

**Two things had to be right, and both were wrong first.** The control caught both:

* **Group before measuring.** AAC carries a scalefactor per band per frame, so each
  (frame, band) sits on its own grid; pooling a file's coefficients superimposes
  dozens of spacings and erases every one. Pooled, the control read 1.7 on audio
  quantised onto an exact lattice.
* **Align before reading — and this is a finding, not a detail.** On a known grid,
  read at the imposing offset the statistic goes 1.03 → 1.61 → 2.62 → 2.85 as the
  grid coarsens; read 511 samples off it stays at **1.03 for every one of them**.

So a lattice reader needs alignment exactly as a hole counter does: both recover
coefficient *values*, and values only exist at the encoder's offset. **The lattice
family therefore cannot rescue Opus either** — resampling destroys the alignment —
which the corpus confirms at AUC 0.48, and which Provir's own `AAC_LATTICE` confirms
from the other side by firing on 0 % of the Opus arm.

That closes a question rather than leaving it open: Opus is not a gap in *this*
family of observables, it is outside the family altogether.

### And on CoreAudio, the encoder it was built for

Measured on the free macOS runner, n=60, both observables read at one alignment:

| arm | holes AUC | lattice AUC |
|---|---|---|
| CoreAudio 128k | 0.782 | **0.829** |
| CoreAudio 256k | 0.650 | **0.662** |
| CoreAudio 320k | 0.562 | **0.586** |

The lattice beats holes at every bitrate, and that is the honest end of the good
news. The medians barely move — 1.033 genuine against 1.035–1.046 CoreAudio — so
this is separation in AUC without a usable operating point: no threshold catches
CoreAudio 256/320 without taking genuine files with it.

**Where the lattice actually pays is MediaFoundation**, at AUC 0.83 and a 73 % fire
rate against a 13 % genuine cost. Provir's own `AAC_LATTICE` fires on 78 % of that
same arm, so this puts us at rough parity on the encoder where we were behind.
CoreAudio at high bitrate remains open for both families.

## 3. Exchange set v2 — the leak is fixed at the source

`ml/build_audit_corpus.py` now forces the **source sample rate** back on the decode
leg. Verified: a 44.1 kHz source round-tripped through Opus returns at 44.1 kHz,
where it previously returned at 48 kHz and gave the arm away without decoding a
sample. The same leg fixes the milder MP3-from-96 kHz case.

It is also the more realistic round-trip rather than a concession: someone passing
a transcode off as lossless delivers it at the rate the album is supposed to have.

With the three freeze guards already in place — duplicate digests, sample-rate
distribution, short arms — a v2 set can be built clean. It is not rebuilt here:
that is a decision for when there is something to send, and the 2026-08 set must
stay as shipped because verdicts have been exchanged against its exact ids.

## 4. Wild fakes — the ledger, not the corpus

`ml/wild_fake_ledger.py`. The hard part was never collection, it is **ground
truth**, so the tool does not try to decide it. It records, keyed by content hash:
where a file came from, every verdict this engine has produced for it and at which
version, and the human adjudication with **the basis it rests on** — tracker staff,
provenance pair, uploader admission, or listening. Those are not the same evidence,
and a corpus that cannot say which one it had cannot be audited later.

Two refusals are built in. A `fake` label without a basis is rejected. And the
engine's own verdict is recorded but can never become the label — a corpus labelled
by the detector under test measures only its own self-consistency.

`status` reports performance **over adjudicated files only**, and says so when the
count is too small to quote. This is the chantier that decides whether any of the
rest matters, and it is the one that needs a human with a tracker account and ears.


---

# The third family, found. And a run-length idea that was not there.

## HF_SEAM, implemented to Provir's specification — and it works

Jamie Dodd gave the algorithm after both of our guesses failed, and the reason
they failed is the interesting part: **the seam is not in the level, it is in the
temporal variability of each bin.**

    v[i]  = std over TIME of log1p(magnitude) in bin i,  10 kHz .. 22.05 kHz
    drop  = (mean(v[i-4:i]) - mean(v[i:i+4])) / mean(v[i-4:i])   for i above 12 kHz
    score = the largest drop                                      (bounded 0..1)

Genuine high frequencies are *restless* — cymbals, sibilants, bow noise, room. A
regenerated or noise-filled band is stationary: it sits at a level and stays
there. The seam is the frequency where restlessness stops. A time-averaged
envelope integrates precisely that away, which is why our first attempt read the
null, and the collapse happens across a band rather than at a boundary, which is
why watching the edge position missed it too.

Measured here, 40 files per arm:

| arm | median | AUC | fires at genuine p90 |
|---|---|---|---|
| genuine | 0.416 | — | 10 % |
| `mp3_320` | 0.635 | **0.89** | 70 % |
| `opus_256` | 0.569 | **0.84** | 40 % |
| `mp3_V0` | 0.582 | 0.81 | 38 % |
| `aacmf_256` | 0.456 | 0.61 | 22 % |
| `vorbis_q8` | 0.432 | 0.58 | 20 % |
| `aac_ff320` | 0.400 | 0.47 | 10 % |

**AUC 0.84 on Opus and 0.89 on mp3_320** — the two arms where the hole family and
the lattice family were both measured dead. That is the third family, confirmed on
our own corpus: it never asks *where* the energy is, only whether it stops moving,
which is why it survives a codec whose entire high band is parametric and why it
is deaf to grid alignment.

**It is a measurement, not a rule, and it is not shipped as one.** Three reasons,
all his:

* It has been measurement-only in Provir since 2026-07-21 — no penalty, no verdict.
* It has a *named* false-positive mode: **production**. Heavy HF limiting, dense
  synthetic pads and some mastering chains flatten temporal variance with no codec
  involved. An early attempt to let it corroborate sent a verified-genuine 2006
  record to UPSCALE at 0.81.
* So "100 % on Opus" is recall on a measurement. It says where to look. It cannot
  convict, and our 10 % on genuine is that same production population.

Note also `aac_ff320` at 0.47: the arm Rule 13 reads at AUC 0.99 is invisible here.
The families are complementary rather than ranked, which is the argument for having
both.

## Dead-run structure — a clean negative, in two domains

From the flag values in the guard file Jamie sent — `DEAD_STRUCTURE_MAXRUN_233`,
`MEANRUN_10.49` — the mechanism looked inferable: not how many bins are dead but
how many die *consecutively*. Against his blind return that flag fires on 70 % of
`mp3_V0`, 69 % of `aacmf_256` and 65 % of `mp3_320` at **2 % on genuine**, which is
exactly our weakest three arms.

`ml/dead_run_probe.py`. The control passes decisively — the same number of dead
bins arranged as 8 long runs reads max-run 160, and as 240 short notches reads 4 —
so the instrument distinguishes arrangement from count, which is the whole claim.

On real material it finds nothing:

* **STFT domain, 2–16 kHz:** every arm at max-run 0.000, AUC 0.49–0.60. The depth
  distributions of genuine and transcoded material are identical to the first
  decimal.
* **MDCT domain at the encoder's own alignment**, where Rule 13's actual zeros
  live: max-run 1.0 on every arm, AUC 0.50–0.54. Holes are isolated bins, never
  runs.

Our high-bitrate transcodes simply do not abandon bands between 2 and 16 kHz —
they abandon *above* the cutoff, which is the cliff Rule 2 already owns and which
this deliberately excludes.

**One finding worth keeping regardless**, because it explains why this is a
distinct observable rather than density repackaged: Rule 13's 33-bin local median
reference is *structurally blind* to a dead band wider than its own window — the
window falls inside the hole, the reference collapses to the dead level, and every
bin inside reads as alive. Detecting runs needs a wide window and a high
percentile; detecting density needs a narrow median. The two want incompatible
references, so neither can be recovered from the other.

## Independence, re-examined after Provir ran our guard on their bench

`MAX_INDEPENDENCE_LIFT` rediscovered three of their aliases unprompted, one at
lift 19.6. It also taught us something back, at the cost of an hour of Jamie's
time: **lift fires on two different things and only one is a bug.** Six of his nine
flagged pairs were real aliases; three were legitimate audio correlation — early
mono recordings are also band-limited, so a mono detector and a rolloff detector
co-fire at 3.1–3.3 on the same 78rpm-era material. Two real physics looking at the
same records, which is what corroboration is *for*.

Our own bench, measured over the 800-file audit corpus: `cnn+spectral` 1.19,
`cnn+mdct` 0.72, `mdct+spectral` 0.25. Nothing near his 19.6, and `mdct` is
anti-correlated with both — it fires on material the others miss, which is the
shape an independent family should have. The guard's failure message now states
the two readings and refuses to pick one for you.

## A structural test, because input tables cannot see uncalled code

Provir's eighth corroboration bug survived its own repair: the fix went into a
predicate that the convicting path never called, and twenty-five green unit cases
sat over it the whole time. `tests/test_verdict_reachability.py` reads this
engine's AST and fails if `FAKE_CERTAIN` is produced anywhere outside
`determine_verdict`, plus a second test that the gate still consults the families
at all. Verified to bite: adding a decoy producer elsewhere in the package fails
the test by name and line.


---

# Reachability: the second half of the uncalled-function lesson

`tests/test_verdict_reachability.py` began as one test — is there a second origin
for a conviction? — because Jamie Dodd's eighth corroboration bug was a repair that
went into a predicate the convicting path never called. That is the first half.

The second half he stated separately and it is the one that generalises:

> Reachability is by enclosing function, not by line order.

Gating his inline conviction site handed the gate five fresh non-witnesses that had
been appended between the old call sites and the new one, including a rung's own
"I applied and declined to fire" telemetry sitting two lines above a predicate that
then read it as evidence. And he nearly barred four flags of the same apparent
species that turned out to be emitted by a function running *after* every gate,
where an exclusion is what he calls dressing.

This engine has the identical shape. `_apply_scoring_rules` evaluates the
corroboration gate twice, and each evaluation sees a different set of families
because the rules that could corroborate run further down:

| gate | families that can have contributed |
|---|---|
| short-circuit 1 | `spectral`, `container` |
| short-circuit 3 | `spectral`, `container`, `silence`, `mdct` |

`cnn` can never corroborate at either. That is deliberate — and it is exactly why
the early exits had to start requiring corroboration in v1.9, or they would have
been measuring themselves. What is not acceptable is for it to change silently:
moving one rule above a gate, or one gate below a rule, alters which families can
corroborate without a single edit to the gate's own code.

## The test reproduced the bug three times before catching it

Writing it was the useful part, because each attempt failed in the exact shape he
warned about, and none of the three would have been visible in a table of inputs:

1. **A helper written above its call site.** `Rule13MDCTAlignment` is instantiated
   at line 118 inside `_run_rule_13`, which is called at line 337. A line-order
   scan put `mdct` before short-circuit 1, where it cannot possibly have run.
2. **A terminal branch written above a gate it returns before reaching.** The
   "heuristics silent" path runs Rules 12 and 13 and then returns; by line number
   those sit above short-circuit 3, by execution they never arrive there.
3. **That branch nested one level deeper than the fix looked.** The whole pipeline
   body lives inside a `try/finally`, so a walker that did not descend into `Try`
   collected the function wholesale — terminal branches included — and reported
   `cnn` as reachable at a gate it cannot reach.

The final version resolves rules to the line where their *enclosing function is
called*, and refuses to descend into any branch ending in `return` or `raise`. Both
tests were verified to bite: declaring a family that is not reachable fails by
line, and declaring a family in `evidence.py` that no reachable rule produces fails
as its mirror — because a family that can never arrive inflates the apparent
independence of the gate while contributing nothing.
