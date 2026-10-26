import numpy as np
import pandas as pd

from tests.conftest import confirm_target, make_students, upload


def err(resp):
    return resp.get_json()["error"]


def test_missing_target_column(client):
    upload(client, make_students(60))
    resp = client.post("/api/dataset/target", json={"target": "nope", "dry_run": True})
    assert resp.status_code == 422 and err(resp)["code"] == "unknown_column"


def test_constant_target_rejected(client):
    df = make_students(60)
    df["const"] = "same"
    upload(client, df)
    resp = client.post("/api/dataset/target", json={"target": "const", "dry_run": True})
    assert resp.status_code == 422 and err(resp)["code"] == "single_class"


def test_single_class_after_missing(client):
    df = make_students(60)
    df["one"] = ["A"] * 59 + [None]
    upload(client, df)
    resp = client.post("/api/dataset/target", json={"target": "one", "dry_run": True})
    assert resp.status_code == 422 and err(resp)["code"] == "single_class"


def test_id_like_target_rejected(client):
    upload(client, make_students(60))
    resp = client.post("/api/dataset/target", json={"target": "student_id", "dry_run": True})
    assert resp.status_code == 422 and err(resp)["code"] == "target_id_like"


def test_rare_class_rejected_and_small_class_warned(client):
    df = make_students(60)
    df["y"] = ["a"] * 50 + ["b"] * 9 + ["c"]
    df["z"] = ["a"] * 50 + ["b"] * 7 + ["c"] * 3
    upload(client, df)
    resp = client.post("/api/dataset/target", json={"target": "y", "dry_run": True})
    assert resp.status_code == 422 and err(resp)["code"] == "rare_class"
    resp = client.post("/api/dataset/target", json={"target": "z", "dry_run": True})
    assert resp.status_code == 200
    warnings = resp.get_json()["target_info"]["warnings"]
    assert any(w["code"] == "small_class" for w in warnings)


def test_mostly_missing_target(client):
    df = make_students(60)
    df["sparse"] = ["a", "b"] * 10 + [None] * 40
    upload(client, df)
    resp = client.post("/api/dataset/target", json={"target": "sparse", "dry_run": True})
    assert resp.status_code == 422 and err(resp)["code"] == "target_mostly_missing"


def test_numeric_target_labels(client):
    df = make_students(60)
    df["flag"] = np.where(df["outcome"] == "Dropout", 1.0, 0.0)
    upload(client, df)
    info = client.post("/api/dataset/target", json={"target": "flag", "dry_run": True}).get_json()["target_info"]
    assert info["classes"] == ["0", "1"]


def test_dry_run_does_not_confirm(client):
    upload(client, make_students(60))
    resp = client.post("/api/dataset/target", json={"target": "outcome", "dry_run": True})
    body = resp.get_json()
    assert body["confirmed"] is False
    assert body["target_info"]["suggested_at_risk_class"] == "Dropout"
    assert client.get("/api/dataset/summary").get_json()["config"] is None
    assert client.post("/api/models/train", json={}).status_code == 409


def test_at_risk_class_required(client):
    upload(client, make_students(60))
    resp = client.post("/api/dataset/target", json={"target": "outcome"})
    assert resp.status_code == 422 and err(resp)["code"] == "at_risk_class_required"
    resp = client.post("/api/dataset/target", json={"target": "outcome", "at_risk_class": "Nope"})
    assert resp.status_code == 422 and err(resp)["code"] == "invalid_at_risk_class"


def test_feature_config_excludes_target_and_id(client):
    upload(client, make_students(60))
    body = confirm_target(client).get_json()
    cfg = body["summary"]["config"]
    assert body["summary"]["stage"] == "configured"
    assert "outcome" not in cfg["features"]
    assert "student_id" not in cfg["features"]
    reasons = {e["column"]: e["reason"] for e in cfg["exclusions"]}
    assert reasons["outcome"] == "target" and reasons["student_id"] == "student_identifier"


def test_id_like_excluded_by_default_and_override_warns(client):
    df = make_students(60)
    df["record_code"] = [f"R{i}" for i in range(60)]
    upload(client, df)
    cfg = confirm_target(client).get_json()["summary"]["config"]
    assert "record_code" not in cfg["features"]
    cfg = confirm_target(client, include_id_like=["record_code"]).get_json()["summary"]["config"]
    assert "record_code" in cfg["features"]
    assert any(w["code"] == "id_like_included" for w in cfg["warnings"])


def test_later_term_columns_flagged_and_timing_preset(client):
    upload(client, make_students(60))
    cfg = confirm_target(client).get_json()["summary"]["config"]
    assert cfg["later_term_columns"] == ["sem2_grade"]
    assert "sem2_grade" in cfg["features"]
    assert cfg["early_prediction"] is False
    assert any(w["code"] == "later_term_included" for w in cfg["warnings"])

    cfg = confirm_target(client, timing_preset="exclude_later").get_json()["summary"]["config"]
    assert "sem2_grade" not in cfg["features"]
    assert cfg["early_prediction"] is True
    assert "later-term" in cfg["timing_label"]


def test_user_exclusions_and_no_features(client):
    df = pd.DataFrame({"sid": [f"s{i}" for i in range(40)], "x": [i % 7 for i in range(40)], "y": ["a", "b"] * 20})
    upload(client, df)
    cfg = client.post("/api/dataset/target", json={"target": "y", "at_risk_class": "a"}).get_json()["summary"]["config"]
    assert cfg["features"] == ["x"]
    resp = client.post("/api/dataset/target", json={"target": "y", "at_risk_class": "a", "excluded_columns": ["x"]})
    assert resp.status_code == 422 and err(resp)["code"] == "no_features"


def test_demographic_feature_warning(client):
    upload(client, make_students(60))
    cfg = confirm_target(client).get_json()["summary"]["config"]
    warning = next(w for w in cfg["warnings"] if w["code"] == "demographic_features")
    assert warning["columns"] == ["gender"]
