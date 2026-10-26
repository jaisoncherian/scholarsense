import csv
import io

import pandas as pd

from routes.export import neutralize
from services.predictions import risk_category
from tests.conftest import confirm_target, make_students, upload


def test_predictions_require_training(client):
    upload(client, make_students(60))
    confirm_target(client)
    assert client.post("/api/predictions", json={}).status_code == 409
    assert client.get("/api/predictions").status_code == 409


def test_default_scope_scores_test_rows_only(trained_client):
    resp = trained_client.post("/api/predictions", json={})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["stage"] == "predicted"
    assert body["meta"]["scope"] == "test"
    assert body["split_counts"] == {"test": 60, "train": 0, "unlabeled": 0}


def test_prediction_shape_and_probabilities(predicted_client):
    body = predicted_client.get("/api/predictions?split=all&page_size=200").get_json()
    assert body["total"] == 300
    assert body["split_counts"] == {"test": 60, "train": 240, "unlabeled": 0}
    meta = body["meta"]
    assert meta["at_risk_class"] == "Dropout"
    assert "not a calibrated" in meta["risk_note"]
    assert meta["features"] and "outcome" not in meta["features"]
    for row in body["rows"]:
        probs = row["probabilities"]
        assert set(probs) == {"Dropout", "Enrolled", "Graduate"}
        assert abs(sum(probs.values()) - 1) < 1e-3
        assert row["risk_score"] == probs["Dropout"]
        assert row["predicted_class"] == max(probs, key=probs.get)
        assert row["split"] in ("train", "test")
        assert row["identifier"].startswith("S")


def test_default_table_filter_is_test_split(predicted_client):
    body = predicted_client.get("/api/predictions").get_json()
    assert body["total"] == 60
    assert all(r["split"] == "test" for r in body["rows"])
    scores = [r["risk_score"] for r in body["rows"]]
    assert scores == sorted(scores, reverse=True)


def test_risk_thresholds():
    assert risk_category(0.1, 0.33, 0.66) == "Low"
    assert risk_category(0.33, 0.33, 0.66) == "Medium"
    assert risk_category(0.659, 0.33, 0.66) == "Medium"
    assert risk_category(0.66, 0.33, 0.66) == "High"


def test_thresholds_reapplied_server_side(predicted_client):
    loose = predicted_client.get("/api/predictions?split=all&low=0.01&high=0.02").get_json()
    strict = predicted_client.get("/api/predictions?split=all&low=0.98&high=0.99").get_json()
    assert loose["meta"]["thresholds"] == {"low": 0.01, "high": 0.02}
    assert strict["summary"]["by_risk_category"]["High"] < loose["summary"]["by_risk_category"]["High"]
    assert sum(strict["summary"]["by_risk_category"].values()) == 300
    bad = predicted_client.get("/api/predictions?low=0.7&high=0.2")
    assert bad.status_code == 422
    resp = predicted_client.put("/api/predictions/thresholds", json={"low": 0.2, "high": 0.5})
    assert resp.get_json()["thresholds"] == {"low": 0.2, "high": 0.5}
    body = predicted_client.get("/api/predictions?split=all&page_size=200").get_json()
    for r in body["rows"]:
        assert r["risk_category"] == risk_category(r["risk_score"], 0.2, 0.5)


def test_filters_search_and_pagination(predicted_client):
    all_rows = predicted_client.get("/api/predictions?split=all&page_size=200&page=1").get_json()
    assert all_rows["pages"] == 2
    cls = all_rows["rows"][0]["predicted_class"]
    filtered = predicted_client.get(f"/api/predictions?split=all&predicted_class={cls}").get_json()
    assert all(r["predicted_class"] == cls for r in filtered["rows"])
    assert filtered["total"] == all_rows["summary"]["by_predicted_class"][cls]
    high = predicted_client.get("/api/predictions?split=all&risk=High").get_json()
    assert all(r["risk_category"] == "High" for r in high["rows"])
    search = predicted_client.get("/api/predictions?split=all&q=s001").get_json()
    assert {r["identifier"] for r in search["rows"]} == {f"S001{i}" for i in range(10)}
    assert predicted_client.get("/api/predictions?risk=Extreme").status_code == 400


def test_export_predictions_csv(predicted_client):
    resp = predicted_client.get("/api/export?type=predictions")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers["Content-Disposition"]
    rows = list(csv.DictReader(io.StringIO(resp.get_data(as_text=True))))
    assert len(rows) == 300
    assert {"identifier", "split", "predicted_class", "probability_Dropout", "risk_score", "risk_category"} <= set(rows[0])
    total = sum(float(rows[0][f"probability_{c}"]) for c in ("Dropout", "Enrolled", "Graduate"))
    assert abs(total - 1) < 1e-3
    assert predicted_client.get("/api/export?type=bogus").status_code == 400


def test_csv_injection_neutralized(client):
    assert neutralize("=SUM(A1)") == "'=SUM(A1)"
    assert neutralize("+1") == "'+1"
    assert neutralize("-2") == "'-2"
    assert neutralize("@cmd") == "'@cmd"
    assert neutralize("safe") == "safe"
    assert neutralize(0.5) == 0.5

    df = make_students(100)
    df["student_id"] = [f"=HYPERLINK(\"x{i}\")" if i < 5 else f"S{i}" for i in range(100)]
    upload(client, df)
    confirm_target(client)
    client.post("/api/models/train", json={})
    client.post("/api/predictions", json={"scope": "all"})
    text = client.get("/api/export?type=predictions").get_data(as_text=True)
    parsed = pd.read_csv(io.StringIO(text))
    dangerous = parsed["identifier"][parsed["identifier"].str.contains("HYPERLINK")]
    assert len(dangerous) == 5
    assert all(v.startswith("'=") for v in dangerous)
