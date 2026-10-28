# Claims triage model -- training script
# Exported from notebooks/claims_v3_FINAL.ipynb
#
# Run:  python train_model.py
# Produces model.pkl in this folder.

import pandas as pd
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score

# load data
df = pd.read_parquet("../data/claims/claims.parquet")

# use the first year for training, keep recent months for testing
train = df[df["month_index"] <= 11]
test = df[df["month_index"].between(12, 13)]

features = [
    "plan", "sum_insured", "eldest_age", "declared_ped", "policy_tenure_months",
    "language", "city_tier", "channel", "diagnosis_group", "admission_type",
    "hospital_network", "claim_route", "claim_amount", "claim_to_si_ratio",
    "length_of_stay_days", "room_rent_ratio", "documents_complete",
    "notified_on_time", "claims_in_last_90d", "assessor_note_length",
]
cat_cols = ["plan", "language", "channel", "diagnosis_group",
            "admission_type", "hospital_network", "claim_route"]


def prep(d):
    X = d[features].copy()
    for c in cat_cols:
        X[c] = X[c].astype("category")
    for c in ["declared_ped", "documents_complete", "notified_on_time"]:
        X[c] = X[c].astype(int)
    return X


X_train, y_train = prep(train), train["rejected"]
X_test, y_test = prep(test), test["rejected"]

model = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08,
                                       categorical_features="from_dtype")
model.fit(X_train, y_train)

preds = model.predict(X_test)
probs = model.predict_proba(X_test)[:, 1]
print("accuracy:", round(accuracy_score(y_test, preds), 4))
print("auc:     ", round(roc_auc_score(y_test, probs), 4))

joblib.dump(model, "model.pkl")
print("saved model.pkl")
