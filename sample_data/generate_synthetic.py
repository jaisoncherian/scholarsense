"""Generate a SYNTHETIC student dataset for trying ScholarSense.

Every value is randomly generated; no real student data is used. The file is
never loaded automatically; upload it yourself from the Dataset Upload page.

Usage:  python sample_data/generate_synthetic.py [rows] [seed]
"""
import os
import sys

import numpy as np
import pandas as pd


def generate(n=600, seed=7):
    rng = np.random.default_rng(seed)
    program = rng.choice(["Nursing", "Engineering", "Design", "Management", "Biology"], n)
    gender = rng.choice(["F", "M"], n)
    age = rng.integers(17, 45, n)
    scholarship = rng.binomial(1, 0.25, n)
    debtor = rng.binomial(1, 0.12, n)
    fees_up_to_date = 1 - rng.binomial(1, 0.12 + 0.3 * debtor, n)
    attendance = np.clip(rng.normal(85, 10, n), 30, 100).round(1)
    sem1_grade = np.clip(rng.normal(12.5, 2.5, n) + (attendance - 85) * 0.05, 0, 20).round(2)
    sem1_approved = np.clip(np.round(sem1_grade / 20 * 6 + rng.normal(0, 1, n)), 0, 6).astype(int)
    study_hours = np.clip(rng.normal(10, 4, n), 0, 30).round(1)

    # Latent risk drives the synthetic outcome.
    z = (-0.35 * (sem1_grade - 12.5) - 0.05 * (attendance - 85) + 1.2 * debtor + 1.0 * (1 - fees_up_to_date)
         - 0.6 * scholarship - 0.05 * (study_hours - 10) + 0.03 * (age - 22) + rng.normal(0, 0.8, n))
    sem2_grade = np.clip(sem1_grade - 0.8 * z + rng.normal(0, 1.2, n), 0, 20).round(2)
    sem2_approved = np.clip(np.round(sem2_grade / 20 * 6 + rng.normal(0, 1, n)), 0, 6).astype(int)
    outcome = np.where(z > 1.0, "Dropout", np.where(z > -0.2, "Enrolled", "Graduate"))

    df = pd.DataFrame({
        "student_id": [f"SYN-{i:05d}" for i in range(1, n + 1)],
        "program": program,
        "gender": gender,
        "age_at_enrollment": age,
        "scholarship_holder": scholarship,
        "debtor": debtor,
        "tuition_fees_up_to_date": fees_up_to_date,
        "attendance_rate": attendance,
        "sem1_grade": sem1_grade,
        "sem1_units_approved": sem1_approved,
        "study_hours_per_week": study_hours,
        "sem2_grade": sem2_grade,
        "sem2_units_approved": sem2_approved,
        "outcome": outcome,
    })
    # Sprinkle missing values so missing-value handling is visible.
    for col, frac in (("attendance_rate", 0.04), ("study_hours_per_week", 0.06), ("program", 0.02)):
        df.loc[rng.random(n) < frac, col] = np.nan
    return df


if __name__ == "__main__":
    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synthetic_students.csv")
    generate(rows, seed).to_csv(out, index=False)
    print(f"Wrote {rows} synthetic rows to {out}")
