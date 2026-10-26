import numpy as np
import pandas as pd
import pytest

from config import Config
from services.evaluation import select_model
from services.preprocessing import build_preprocessor, prepare_X
from tests.conftest import confirm_target, current_session, make_students, upload


def test_preprocessing_handles_missing_and_unseen_categories():
    schema = {"numeric": ["n"], "categorical": ["c"], "max_categories": 50}
    train = pd.DataFrame({"n": [1.0, np.nan, 3.0, 4.0], "c": ["a", "b", None, "a"]})
    pre = build_preprocessor(schema, scale_numeric=True)
    Z = pre.fit_transform(prepare_X(train, schema))
    assert not np.isnan(np.asarray(Z.todense() if hasattr(Z, "todense") else Z)).any()
    test = prepare_X(pd.DataFrame({"n": [np.nan], "c": ["never-seen"]}), schema)
    out = pre.transform(test)
    assert out.shape[1] == Z.shape[1]


def test_training_produces_real_multiclass_metrics(trained_client, store):
    body = trained_client.get("/api/models/metrics").get_json()
    assert body["stage"] == "trained"
    m = body["metrics"]
    assert set(m["models"]) == {"logistic_regression", "random_forest"}
    assert m["classes"] == ["Dropout", "Enrolled", "Graduate"]
    assert m["n_train"] + m["n_test"] == 300
    assert m["n_test"] == 60
    for model in m["models"].values():
        assert len(model["per_class"]) == 3
        cm = model["confusion_matrix"]["matrix"]
        assert np.array(cm).sum() == 60
        assert model["confusion_matrix"]["labels"] == m["classes"]
        assert 0 <= model["macro_f1"] <= 1
        assert "Macro" in model["averaging"]
        assert model["at_risk"]["class"] == "Dropout"
        assert "macro avg" in model["classification_report"]
    assert "outcome" not in m["features"] and "student_id" not in m["features"]
    assert m["timing_label"]


def test_same_split_and_no_test_leakage(trained_client, store):
    sess = current_session(trained_client, store)
    t = sess.training
    assert set(t["train_index"]).isdisjoint(t["test_index"])
    # Both pipelines carry their preprocessing and were fitted on the same training rows.
    for pipe in t["pipelines"].values():
        assert list(pipe.named_steps) == ["preprocess", "model"]
    lr_pre = t["pipelines"]["logistic_regression"].named_steps["preprocess"]
    rf_pre = t["pipelines"]["random_forest"].named_steps["preprocess"]
    imputer_lr = lr_pre.named_transformers_["num"].named_steps["imputer"]
    imputer_rf = rf_pre.named_transformers_["num"].named_steps["imputer"]
    expected = t["X_train"][["attendance_rate", "sem1_grade", "sem2_grade", "debtor"]].median().values
    assert np.allclose(imputer_lr.statistics_, expected)
    assert np.allclose(imputer_rf.statistics_, expected)
    assert "outcome" not in t["X_train"].columns and "student_id" not in t["X_train"].columns


def test_stratified_split_preserves_class_ratio(trained_client):
    m = trained_client.get("/api/models/metrics").get_json()["metrics"]
    assert m["stratified"] is True
    total = {k: m["class_counts_train"][k] + m["class_counts_test"][k] for k in m["classes"]}
    for k in m["classes"]:
        assert abs(m["class_counts_test"][k] / 60 - total[k] / 300) < 0.02


def test_binary_training_and_class_weight_option(client):
    upload(client, make_students(200, classes=("AtRisk", "OnTrack")))
    confirm_target(client, at_risk="AtRisk")
    resp = client.post("/api/models/train", json={"test_size": 0.25, "lr_class_weight": "none",
                                                   "rf_class_weight": "balanced", "rf_n_estimators": 50})
    assert resp.status_code == 200
    m = resp.get_json()["metrics"]
    assert m["n_test"] == 50
    assert m["params"]["rf_n_estimators_used"] == 50
    assert m["params"]["lr_class_weight"] == "none"


def test_invalid_training_params(client):
    upload(client, make_students(100))
    confirm_target(client)
    assert client.post("/api/models/train", json={"test_size": 0.9}).status_code == 400
    assert client.post("/api/models/train", json={"rf_n_estimators": 1000}).status_code == 400
    assert client.post("/api/models/train", json={"lr_class_weight": "x"}).status_code == 400


def test_too_few_rows(client):
    upload(client, make_students(25))
    confirm_target(client)
    resp = client.post("/api/models/train", json={})
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "too_few_rows"


def test_rows_with_missing_target_dropped_and_reported(client):
    df = make_students(50)
    df.loc[:21, "outcome"] = None  # leaves 28 labelled rows
    df.loc[22:, "outcome"] = ["Dropout", "Enrolled"] * 14
    upload(client, df)
    assert confirm_target(client).status_code == 200
    resp = client.post("/api/models/train", json={})
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "too_few_rows"
    assert resp.get_json()["error"]["details"]["dropped_missing_target"] == 22


def test_rare_class_error_at_training(client, store):
    df = make_students(60)
    upload(client, df)
    confirm_target(client)
    # Simulate a class that became rare after configuration (e.g. edited config).
    sess = current_session(client, store)
    sess.df.loc[0, "outcome"] = "Transferred"
    resp = client.post("/api/models/train", json={})
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "rare_class"


def _m(recall, f1, acc):
    return {"at_risk": {"recall": recall, "precision": 0.5}, "macro_f1": f1, "accuracy": acc, "weighted_f1": f1}


@pytest.mark.parametrize("lr,rf,expected,step", [
    (_m(0.80, 0.50, 0.50), _m(0.70, 0.90, 0.90), "logistic_regression", 0),   # recall decides
    (_m(0.70, 0.90, 0.90), _m(0.80, 0.50, 0.50), "random_forest", 0),
    (_m(0.800, 0.60, 0.90), _m(0.805, 0.70, 0.50), "random_forest", 1),      # recall tie -> macro-F1
    (_m(0.80, 0.700, 0.70), _m(0.80, 0.705, 0.80), "random_forest", 2),      # F1 tie -> accuracy
    (_m(0.80, 0.70, 0.80), _m(0.80, 0.70, 0.80), "logistic_regression", 3),  # full tie -> LR
])
def test_model_selection_logic(lr, rf, expected, step):
    result = select_model({"logistic_regression": lr, "random_forest": rf}, "Dropout", Config.SELECTION_TOLERANCE)
    assert result["selected"] == expected
    assert len(result["steps"]) == step + 1
    assert "recall" in result["criteria"]


def test_selection_with_one_failed_model():
    result = select_model({"random_forest": _m(0.5, 0.5, 0.5)}, "Dropout")
    assert result["selected"] == "random_forest"


def test_selection_matches_reported_metrics(trained_client):
    m = trained_client.get("/api/models/metrics").get_json()["metrics"]
    recomputed = select_model({k: v for k, v in m["models"].items()}, "Dropout", Config.SELECTION_TOLERANCE)
    assert m["selection"]["selected"] == recomputed["selected"]


def test_one_model_failure_returns_other(client, monkeypatch):
    from sklearn.ensemble import RandomForestClassifier

    def boom(self, *a, **k):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(RandomForestClassifier, "fit", boom)
    upload(client, make_students(100))
    confirm_target(client)
    resp = client.post("/api/models/train", json={})
    assert resp.status_code == 200
    m = resp.get_json()["metrics"]
    assert list(m["models"]) == ["logistic_regression"]
    assert "synthetic failure" in m["failures"]["random_forest"]
    assert m["selection"]["selected"] == "logistic_regression"
