import numpy as np
from sklearn.inspection import permutation_importance as real_pi

import services.explainability as explainability
from tests.conftest import current_session


def test_global_importance_uses_held_out_original_columns(trained_client, store, monkeypatch):
    seen = {}

    def spy(estimator, X, y, **kwargs):
        seen["index"] = set(X.index)
        seen["columns"] = list(X.columns)
        seen["kwargs"] = kwargs
        return real_pi(estimator, X, y, **kwargs)

    monkeypatch.setattr(explainability, "permutation_importance", spy)
    resp = trained_client.get("/api/explanations/global?model=random_forest")
    assert resp.status_code == 200
    exp = resp.get_json()["explanation"]
    sess = current_session(trained_client, store)
    assert seen["index"] == set(sess.training["test_index"])  # held-out rows only
    assert seen["index"].isdisjoint(sess.training["train_index"])
    assert seen["columns"] == sess.training["X_test"].columns.tolist()  # raw columns, not one-hot
    assert seen["kwargs"]["n_repeats"] >= 5 and seen["kwargs"]["random_state"] == 42
    assert {f["feature"] for f in exp["features"]} == set(sess.training["features"])
    assert exp["evaluated_on"] == "held-out test set"
    assert "not causation" in exp["note"]
    assert all(f["std"] is not None for f in exp["features"])


def test_global_importance_at_risk_recall_scoring(trained_client):
    resp = trained_client.get("/api/explanations/global?model=logistic_regression&scoring=at_risk_recall")
    assert resp.status_code == 200
    assert "Dropout" in resp.get_json()["explanation"]["scoring_label"]
    assert trained_client.get("/api/explanations/global?scoring=bad").status_code == 400


def test_local_logistic_regression_contributions(trained_client, store):
    sess = current_session(trained_client, store)
    row_id = int(sess.training["test_index"][0])
    exp = trained_client.get(f"/api/explanations/local/{row_id}?model=logistic_regression").get_json()["explanation"]
    assert exp["split"] == "test" and exp["in_sample"] is False
    assert "log-odds" in exp["method"]
    assert exp["limitations"]
    assert {c["feature"] for c in exp["contributions"]} == set(sess.training["features"])
    # Contributions are model-derived: their sum equals the centred logit of the predicted class.
    pipe = sess.training["pipelines"]["logistic_regression"]
    from services.preprocessing import prepare_X, to_dense
    x = prepare_X(sess.df.loc[[row_id]], sess.training["schema"])
    z = to_dense(pipe.named_steps["preprocess"].transform(x))[0]
    k = list(pipe.classes_).index(exp["predicted_class"])
    w = pipe.named_steps["model"].coef_[k]
    expected = float(w @ (z - sess.training["lr_transformed_mean"]))
    total = sum(c["contribution"] for c in exp["contributions"])
    assert abs(total - expected) < 1e-3
    assert abs(sum(exp["probabilities"].values()) - 1) < 1e-3
    assert exp["summary"]


def test_local_random_forest_perturbation(trained_client, store):
    sess = current_session(trained_client, store)
    row_id = int(sess.training["train_index"][0])
    exp = trained_client.get(f"/api/explanations/local/{row_id}?model=random_forest").get_json()["explanation"]
    assert exp["split"] == "train" and exp["in_sample"] is True
    assert "perturbation" in exp["method"].lower()
    for c in exp["contributions"]:
        assert "reference" in c
        if c["value"] == c["reference"]:
            assert c["contribution"] == 0


def test_missing_values_are_not_explained(client, store):
    from tests.conftest import confirm_target, make_students, upload
    df = make_students(200)
    df.loc[5, "attendance_rate"] = np.nan
    upload(client, df)
    confirm_target(client)
    client.post("/api/models/train", json={})
    for model in ("logistic_regression", "random_forest"):
        exp = client.get(f"/api/explanations/local/5?model={model}").get_json()["explanation"]
        item = next(c for c in exp["contributions"] if c["feature"] == "attendance_rate")
        assert item["value_missing"] is True
        assert item["contribution"] is None and item["effect"] == "not_explained"
        assert "attendance_rate" in exp["missing_features"]
        assert not any("attendance_rate" in line for line in exp["summary"])


def test_local_unknown_row(trained_client):
    assert trained_client.get("/api/explanations/local/99999").status_code == 404
