import numpy as np
import pandas as pd

from tests.conftest import confirm_target, make_students, upload


def test_analysis_requires_confirmed_target(client):
    upload(client, make_students(60))
    assert client.post("/api/analysis").status_code == 409


def test_analysis_values_come_from_file(client):
    df = make_students(150, seed=3)
    df.loc[:9, "attendance_rate"] = np.nan
    upload(client, df)
    confirm_target(client)
    resp = client.post("/api/analysis")
    assert resp.status_code == 200
    eda = resp.get_json()["analysis"]
    assert resp.get_json()["stage"] == "analyzed"
    assert eda["overview"]["rows"] == 150
    dist = {c["class"]: c["count"] for c in eda["target_distribution"]["classes"]}
    assert dist == df["outcome"].value_counts().to_dict()
    stats = {s["column"]: s for s in eda["numeric_stats"]}
    assert stats["sem1_grade"]["mean"] == round(df["sem1_grade"].mean(), 4)
    assert stats["attendance_rate"]["missing"] == 10
    assert eda["missing"]["columns"][0] == {"column": "attendance_rate", "missing": 10, "pct": round(10 / 150 * 100, 2)}
    cats = {c["column"]: c for c in eda["categorical_counts"]}
    assert sum(v["count"] for v in cats["program"]["values"]) == 150
    # Identifier and target are excluded from analysis columns.
    assert "student_id" not in stats and "outcome" not in cats
    assert eda["correlation"]["available"] is True
    assert "student_id" not in eda["correlation"]["columns"]
    assert "debtor" not in eda["correlation"]["columns"]  # binary columns excluded
    assert eda["academic"]["available"] is True
    assert eda["feature_vs_target"]["available"] is True
    # GET returns the stored analysis after refresh.
    assert client.get("/api/analysis").get_json()["analysis"] == eda


def test_unavailable_charts_explain_why(client):
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"colour": rng.choice(["r", "g", "b"], 80), "size": rng.normal(0, 1, 80),
                       "y": rng.choice(["yes", "no"], 80)})
    upload(client, df)
    client.post("/api/dataset/target", json={"target": "y", "at_risk_class": "yes"})
    eda = client.post("/api/analysis").get_json()["analysis"]
    assert eda["correlation"]["available"] is False
    assert "at least 2" in eda["correlation"]["reason"]
    assert eda["academic"]["available"] is False
    assert eda["missing_chart"]["available"] is False


def test_top_n_categories_fold_into_other(client):
    rng = np.random.default_rng(2)
    df = pd.DataFrame({"cat": [f"v{i % 15}" for i in range(300)], "x": rng.normal(0, 1, 300),
                       "y": rng.choice(["a", "b"], 300)})
    upload(client, df)
    client.post("/api/dataset/target", json={"target": "y", "at_risk_class": "a"})
    eda = client.post("/api/analysis").get_json()["analysis"]
    values = eda["categorical_counts"][0]["values"]
    assert len(values) == 11 and values[-1]["value"] == "Other"
    assert sum(v["count"] for v in values) == 300
