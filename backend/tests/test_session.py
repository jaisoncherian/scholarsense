import os
import time

import numpy as np
import pandas as pd

from tests.conftest import confirm_target, current_session, make_students, upload


def test_replacing_dataset_resets_everything(predicted_client, store):
    sess = current_session(predicted_client, store)
    predicted_client.post("/api/analysis")
    predicted_client.get("/api/explanations/global")
    first_path = sess.file_path
    rid = int(sess.predictions["frame"]["row_id"].iloc[0])
    predicted_client.patch(f"/api/interventions/{rid}/review", json={"status": "Actioned"})
    assert sess.eda and sess.training and sess.predictions and sess.explanations and sess.reviews
    assert os.path.exists(first_path)

    rng = np.random.default_rng(9)
    other = pd.DataFrame({"x": rng.normal(0, 1, 50), "label": rng.choice(["p", "q"], 50)})
    resp = upload(predicted_client, other, "second.csv")
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["stage"] == "uploaded"
    assert body["dataset"]["filename"] == "second.csv" and body["dataset"]["rows"] == 50
    assert body["config"] is None and body["training"] is None and body["predictions"] is None
    assert [c["name"] for c in body["profile"]["columns"]] == ["x", "label"]

    same = current_session(predicted_client, store)
    assert same is sess
    for attr in ("eda", "training", "predictions", "config", "target_check", "indicator_mapping"):
        assert getattr(sess, attr) is None, attr
    assert sess.explanations == {} and sess.reviews == {}
    assert not os.path.exists(first_path)
    assert os.listdir(store.upload_dir) == [os.path.basename(sess.file_path)]
    for url in ("/api/analysis", "/api/models/metrics", "/api/predictions", "/api/interventions"):
        assert predicted_client.get(url).status_code in (404, 409), url


def test_reconfiguring_target_clears_downstream(predicted_client, store):
    sess = current_session(predicted_client, store)
    confirm_target(predicted_client, at_risk="Enrolled")
    assert sess.training is None and sess.predictions is None and sess.eda is None
    assert predicted_client.get("/api/dataset/summary").get_json()["stage"] == "configured"


def test_delete_session_removes_state_and_file(client, store):
    upload(client, make_students(60))
    sess = current_session(client, store)
    path = sess.file_path
    resp = client.delete("/api/session")
    assert resp.status_code == 200 and resp.get_json()["deleted"] is True
    assert not os.path.exists(path)
    assert sess.id not in store
    assert client.get("/api/dataset/summary").get_json() == {"stage": "empty"}


def test_ttl_cleanup_expires_idle_sessions(client, store):
    upload(client, make_students(60))
    sess = current_session(client, store)
    path = sess.file_path
    assert store.cleanup_expired(now=time.time() + 10) == 0
    assert store.cleanup_expired(now=time.time() + store.ttl_seconds + 5) == 1
    assert not os.path.exists(path)
    assert sess.df is None and sess.id not in store


def test_cleanup_all_on_shutdown(client, store):
    upload(client, make_students(60))
    path = current_session(client, store).file_path
    store.cleanup_all()
    assert not os.path.exists(path) and len(store) == 0


def test_unknown_session_id_is_not_adopted(client, store):
    client.set_cookie("ss_session", "f" * 32)
    upload(client, make_students(40))
    assert client.get_cookie("ss_session").value != "f" * 32
    assert ("f" * 32) not in store


def test_sessions_are_isolated(app, store):
    a, b = app.test_client(), app.test_client()
    upload(a, make_students(60))
    assert b.get("/api/dataset/summary").get_json() == {"stage": "empty"}
    assert len(store) == 1


def test_stage_progression(client):
    stages = [client.get("/api/dataset/summary").get_json()["stage"]]
    upload(client, make_students(100))
    stages.append(client.get("/api/dataset/summary").get_json()["stage"])
    confirm_target(client)
    stages.append(client.get("/api/dataset/summary").get_json()["stage"])
    client.post("/api/analysis")
    stages.append(client.get("/api/dataset/summary").get_json()["stage"])
    client.post("/api/models/train", json={})
    stages.append(client.get("/api/dataset/summary").get_json()["stage"])
    client.post("/api/predictions", json={})
    stages.append(client.get("/api/dataset/summary").get_json()["stage"])
    assert stages == ["empty", "uploaded", "configured", "analyzed", "trained", "predicted"]
