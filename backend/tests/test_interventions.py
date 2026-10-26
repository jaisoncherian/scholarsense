import numpy as np
import pandas as pd

from services.recommendations import detect_indicators, is_demographic
from tests.conftest import confirm_target, make_students, upload


def _run(client, df, at_risk="Dropout"):
    assert upload(client, df).status_code == 201
    assert confirm_target(client, at_risk=at_risk).status_code == 200
    assert client.post("/api/models/train", json={}).status_code == 200
    assert client.post("/api/predictions", json={"scope": "all"}).status_code == 201
    return client.get("/api/interventions?page_size=100").get_json()


def test_rules_fire_on_observed_evidence(client):
    body = _run(client, make_students(200))
    assert body["disclaimer"] == "Suggestions for staff review, not automated decisions."
    cats = {i["column"]: i["category"] for i in body["indicators"]}
    assert cats["sem1_grade"] == "performance"
    assert cats["attendance_rate"] == "attendance"
    assert cats["debtor"] == "financial"
    assert "gender" not in cats
    rules = {r["id"]: r["available"] for r in body["rules"]}
    assert all(rules.values())
    assert body["summary"]["students_with_suggestions"] > 0
    q1 = np.percentile(make_students(200)["sem1_grade"], 25)
    for rec in body["records"]:
        assert rec["model_output"]["label"].startswith("Model output")
        assert rec["review"]["status"] == "Not reviewed"
        for ev in rec["evidence"]:
            assert ev["comparison"]
            if ev["column"] == "sem1_grade":
                assert float(ev["value"]) < q1
        if len(rec["indicator_areas"]) >= 2:
            assert any(s["rule_id"] == "advisor_review" for s in rec["suggestions"])


def test_rules_hidden_when_columns_absent(client):
    rng = np.random.default_rng(4)
    n = 120
    df = pd.DataFrame({"student_id": [f"X{i}" for i in range(n)], "hours": rng.normal(10, 3, n),
                       "club": rng.choice(["a", "b"], n), "gender": rng.choice(["F", "M"], n),
                       "age": rng.integers(17, 40, n), "outcome": rng.choice(["Dropout", "Graduate"], n)})
    body = _run(client, df)
    assert body["indicators"] == []
    assert not any(r["available"] for r in body["rules"])
    assert all(r["reason"] for r in body["rules"])
    assert body["records"] == []


def test_only_performance_rule_when_only_grades_exist(client):
    df = make_students(150).drop(columns=["attendance_rate", "debtor"])
    body = _run(client, df)
    rules = {r["id"]: r["available"] for r in body["rules"]}
    assert rules == {"academic_support": True, "attendance_conversation": False,
                     "financial_aid_referral": False, "advisor_review": False}
    for rec in body["records"]:
        assert [s["rule_id"] for s in rec["suggestions"]] == ["academic_support"]


def test_demographic_columns_never_trigger():
    assert is_demographic("gender") and is_demographic("Age at enrollment") and is_demographic("Nacionality")
    assert not is_demographic("average_grade") and not is_demographic("percentage_score")
    df = pd.DataFrame({"age_grade_score": [1, 2, 3, 4], "gender_score": [1, 2, 3, 4], "y": ["a", "b", "a", "b"]})
    profile = {"columns": [{"name": c, "type": "numeric"} for c in df.columns]}
    assert detect_indicators(df, {"target": "y", "id_column": None}, profile) == []


def test_review_status_and_detail(predicted_client):
    body = predicted_client.get("/api/interventions").get_json()
    rid = body["records"][0]["row_id"]
    resp = predicted_client.patch(f"/api/interventions/{rid}/review", json={"status": "In review", "note": "call"})
    assert resp.status_code == 200
    detail = predicted_client.get(f"/api/interventions/{rid}").get_json()["record"]
    assert detail["review"]["status"] == "In review"
    filtered = predicted_client.get("/api/interventions?status=In%20review").get_json()
    assert [r["row_id"] for r in filtered["records"]] == [rid]
    bad = predicted_client.patch(f"/api/interventions/{rid}/review", json={"status": "Expelled"})
    assert bad.status_code == 400
    assert predicted_client.patch("/api/interventions/99999/review", json={"status": "Actioned"}).status_code == 404


def test_user_mapping_overrides_and_rejects_demographics(predicted_client):
    resp = predicted_client.put("/api/interventions/mapping", json={"indicators": [
        {"column": "sem2_grade", "category": "performance", "direction": "low", "threshold": 5}]})
    assert resp.status_code == 200
    body = predicted_client.get("/api/interventions?page_size=100").get_json()
    assert body["mapping_mode"] == "user"
    for rec in body["records"]:
        assert all(e["column"] == "sem2_grade" and float(e["value"]) < 5 for e in rec["evidence"])
        assert "staff-set threshold of 5" in rec["evidence"][0]["comparison"]
    bad = predicted_client.put("/api/interventions/mapping", json={"indicators": [
        {"column": "gender", "category": "performance", "direction": "low"}]})
    assert bad.status_code == 422 and bad.get_json()["error"]["code"] == "demographic_column"
    reset = predicted_client.put("/api/interventions/mapping", json={"reset": True}).get_json()
    assert reset["mode"] == "auto"


def test_export_interventions(predicted_client):
    text = predicted_client.get("/api/export?type=interventions").get_data(as_text=True)
    rows = pd.read_csv(__import__("io").StringIO(text))
    assert {"identifier", "suggestion", "evidence", "review_status", "model_risk_score"} <= set(rows.columns)
    assert (rows["note"] == "Suggestion for staff review, not an automated decision.").all()


def test_columns_excluded_for_timing_are_not_auto_evidence(client):
    upload(client, make_students(150))
    confirm_target(client, timing_preset="exclude_later")
    client.post("/api/models/train", json={})
    client.post("/api/predictions", json={"scope": "all"})
    body = client.get("/api/interventions").get_json()
    columns = {i["column"] for i in body["indicators"]}
    assert "sem2_grade" not in columns and "sem1_grade" in columns
