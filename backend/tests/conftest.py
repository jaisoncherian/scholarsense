"""Shared fixtures. All data is synthetic and generated in-process."""
import io

import numpy as np
import pandas as pd
import pytest

from app import create_app


def make_students(n=300, seed=0, classes=("Dropout", "Enrolled", "Graduate")):
    rng = np.random.default_rng(seed)
    grade = np.clip(rng.normal(12, 3, n), 0, 20).round(2)
    attendance = np.clip(rng.normal(80, 12, n), 20, 100).round(1)
    debtor = rng.binomial(1, 0.15, n)
    z = -0.5 * (grade - 12) - 0.06 * (attendance - 80) + 1.5 * debtor + rng.normal(0, 0.7, n)
    if len(classes) == 3:
        outcome = np.where(z > 0.9, classes[0], np.where(z > -0.5, classes[1], classes[2]))
    else:
        outcome = np.where(z > 0.3, classes[0], classes[1])
    return pd.DataFrame({
        "student_id": [f"S{i:04d}" for i in range(n)],
        "program": rng.choice(["Arts", "Science", "Business"], n),
        "gender": rng.choice(["F", "M"], n),
        "attendance_rate": attendance,
        "sem1_grade": grade,
        "sem2_grade": np.clip(grade - z + rng.normal(0, 1, n), 0, 20).round(2),
        "debtor": debtor,
        "outcome": outcome,
    })


def csv_bytes(df, sep=","):
    return df.to_csv(index=False, sep=sep).encode("utf-8")


@pytest.fixture
def app(tmp_path):
    application = create_app(UPLOAD_DIR=str(tmp_path / "uploads"), RF_N_JOBS=1)
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def store(app):
    return app.extensions["session_store"]


def upload(client, content, filename="students.csv"):
    if isinstance(content, pd.DataFrame):
        content = csv_bytes(content)
    return client.post("/api/upload", data={"file": (io.BytesIO(content), filename)},
                       content_type="multipart/form-data")


def confirm_target(client, target="outcome", at_risk="Dropout", **extra):
    body = {"target": target, "at_risk_class": at_risk, "id_column": "student_id", **extra}
    return client.post("/api/dataset/target", json=body)


def current_session(client, store):
    cookie = client.get_cookie("ss_session")
    return store.get(cookie.value) if cookie else None


@pytest.fixture
def trained_client(client):
    assert upload(client, make_students()).status_code == 201
    assert confirm_target(client).status_code == 200
    resp = client.post("/api/models/train", json={})
    assert resp.status_code == 200, resp.get_json()
    return client


@pytest.fixture
def predicted_client(trained_client):
    resp = trained_client.post("/api/predictions", json={"scope": "all"})
    assert resp.status_code == 201, resp.get_json()
    return trained_client
