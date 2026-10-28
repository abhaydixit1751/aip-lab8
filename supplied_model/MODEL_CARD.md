# Claims Triage Model — v3

**From:** Data Science team, Aurora Health
**To:** Platform Engineering
**Re:** Handover for production deployment

Hi team — handing this over as discussed. The model is trained and tested and we
are confident it is ready for production. Details below.

## Purpose

Predicts whether an incoming health claim will be **rejected**, so that likely
approvals can be auto-approved and the rest routed to assessors. Expected to
remove most of the manual review queue.

## Performance

Tested on the two most recent months held out from training:

| Metric | Score |
|---|---|
| Accuracy | **0.981** |
| AUC | **0.997** |

These are the best numbers we have seen on any claims model. The model is
extremely confident on almost every claim.

## Files

| File | What it is |
|---|---|
| `model.pkl` | The trained model |
| `train_model.py` | Training script (exported from the notebook) |
| `requirements.txt` | Dependencies |

To retrain: `pip install -r requirements.txt` then `python train_model.py`.

## Features

All 20 features in `train_model.py`. The strongest predictors, from the
notebook's feature-importance plot, are the assessor note length and the number
of claims in the last 90 days.

## Next steps

Please wrap it in an API and deploy. We are moving on to the fraud-ring project
next sprint, so reach out on the channel if anything comes up.

— DS team
