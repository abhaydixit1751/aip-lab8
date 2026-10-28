# Aurora Health — Claims Dataset

Synthetic, deterministic, and realistic enough to be dangerous. Every claim
belongs to the same fictional insurer as the Module 1 policy corpus: the same
plans, sum-insured bands, waiting periods and network rules.

| File | Rows | What it is |
|---|---|---|
| `claims.parquet` | 45,365 | Every claim filed Jan 2024 – Dec 2025 on a sample of 24,000 policies, as extracted by the nightly batch job on 31 Dec 2025 |
| `policies.parquet` | 24,000 | The policy master for the sample, one row per policy |

## Columns — `claims.parquet`

| Column | Type | Meaning |
|---|---|---|
| `claim_id` | str | Unique, assigned in filing order |
| `policy_id` | str | Joins to `policies.parquet` and to Module 1's `AUR-` policy numbers |
| `claim_date` | date | Date the claim was filed |
| `month_index` | int | 0 = Jan 2024 … 23 = Dec 2025 |
| `plan` | str | bronze · silver · gold · platinum |
| `sum_insured` | int | INR |
| `eldest_age` | int | Age of the eldest insured member |
| `declared_ped` | bool | A pre-existing disease was declared at proposal |
| `policy_tenure_months` | float | Continuous cover at the claim date |
| `language` | str | `en` or `hi-en` — language of the claim submission |
| `city_tier` | int | 1, 2 or 3 |
| `channel` | str | app · branch · email · agent |
| `diagnosis_text` | str | Free-text diagnosis as submitted |
| `diagnosis_group` | str | Diagnosis code assigned by the intake pipeline from `diagnosis_text` |
| `admission_type` | str | planned · emergency |
| `hospital_network` | str | network · non_network · excluded_provider |
| `claim_route` | str | cashless · reimbursement |
| `claim_amount` | float | INR claimed |
| `claim_to_si_ratio` | float | `claim_amount / sum_insured` |
| `length_of_stay_days` | int | Days admitted |
| `room_rent_ratio` | float | Room rent charged ÷ the plan's room-rent limit |
| `documents_complete` | bool | All required documents received |
| `notified_on_time` | bool | Aurora notified within the policy's deadline |
| `claims_in_last_90d` | int | Claims on the same policy in the last 90 days, from the batch job |
| `assessor_note_length` | int | Characters in the assessor's case note |
| **`rejected`** | bool | **The label.** Final decision on the claim |
| `approved_amount` | float | INR paid; 0 if rejected |

## Business context you will need

- Aurora as a whole processes about **2,000 claims a day**. This extract is a
  sample of its book by policy (about 62 claims a day): every claim of each
  sampled policy is present, so per-policy history is complete. Rupee figures
  for Aurora are scaled to 2,000 a day.
- A claims assessor costs about **₹500** per manual review.
- A claim that should have been rejected but is paid out costs Aurora the
  amount paid.
- The model's job is triage: decide which claims can be **auto-approved** and
  which must go to an assessor.

## Conventions

- Train on months 0–11. Months 12–13 are the holdout. Months 12–23 are
  "production" and are replayed as live traffic in Lab 13.
- Do not read months 14–23 before Lab 13. It would be like reading next
  quarter's newspaper.

## What this card does not tell you

Everything you need to decide whether to trust this data. That is your job, and
it starts in Lab 8.
