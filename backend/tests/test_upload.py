import io

import numpy as np
import pandas as pd

from app import create_app
from tests.conftest import csv_bytes, current_session, make_students, upload


def error_code(resp):
    body = resp.get_json()
    assert set(body["error"]) == {"code", "message", "details"}
    return body["error"]["code"]


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_fresh_session_is_empty(client):
    assert client.get("/api/dataset/summary").get_json() == {"stage": "empty"}
    assert client.get("/api/dataset/preview").status_code == 404


def test_valid_upload_profiles_dataset(client, store):
    df = make_students(120)
    resp = upload(client, df, "../../etc/my students.csv")
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["stage"] == "uploaded"
    assert body["dataset"]["rows"] == 120
    assert body["dataset"]["columns"] == len(df.columns)
    assert body["dataset"]["filename"] == "my students.csv"  # path stripped
    types = {c["name"]: c["type"] for c in body["profile"]["columns"]}
    assert types["student_id"] == "identifier"
    assert types["attendance_rate"] == "numeric"
    assert types["program"] == "categorical"
    assert types["debtor"] == "boolean"
    # Target is suggested, never auto-selected.
    assert body["profile"]["target_candidates"][0] == {"name": "outcome", "match": "exact"}
    assert body["config"] is None
    sess = current_session(client, store)
    assert sess.file_path and sess.file_path.endswith(".upload")
    assert "students" not in sess.file_path  # random server-side name


def test_preview_returns_first_20_rows(client):
    upload(client, make_students(50))
    body = client.get("/api/dataset/preview").get_json()
    assert len(body["rows"]) == 20
    assert body["rows"][0][0] == "S0000"
    assert body["total_rows"] == 50


def test_rejects_non_csv_extension(client):
    resp = upload(client, b"a,b\n1,2\n", "data.xlsx")
    assert resp.status_code == 415
    assert error_code(resp) == "unsupported_file_type"


def test_rejects_binary_content(client):
    resp = upload(client, b"PK\x03\x04binary\x00stuff", "data.csv")
    assert resp.status_code == 415
    assert error_code(resp) == "not_a_csv"


def test_rejects_missing_file(client):
    resp = client.post("/api/upload", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert error_code(resp) == "missing_file"


def test_rejects_oversized_upload(tmp_path):
    app = create_app(UPLOAD_DIR=str(tmp_path), MAX_UPLOAD_BYTES=2000, MAX_CONTENT_LENGTH=500_000)
    resp = upload(app.test_client(), csv_bytes(make_students(300)))
    assert resp.status_code == 413
    assert error_code(resp) == "file_too_large"


def test_rejects_body_over_content_length(tmp_path):
    app = create_app(UPLOAD_DIR=str(tmp_path), MAX_CONTENT_LENGTH=1000)
    resp = upload(app.test_client(), csv_bytes(make_students(300)))
    assert resp.status_code == 413
    assert error_code(resp) == "file_too_large"


def test_empty_and_header_only(client):
    resp = upload(client, b"")
    assert resp.status_code == 422 and error_code(resp) == "empty_file"
    resp = upload(client, b"a,b,c\n")
    assert resp.status_code == 422 and error_code(resp) == "header_only"


def test_malformed_csv(client):
    resp = upload(client, b"a,b\n1,2\n3,4,5,6\n7,8\n")
    assert resp.status_code == 422
    assert error_code(resp) == "malformed_csv"


def test_too_many_rows_and_columns(tmp_path):
    app = create_app(UPLOAD_DIR=str(tmp_path), MAX_ROWS=10, MAX_COLUMNS=3)
    c = app.test_client()
    assert error_code(upload(c, b"a,b\n" + b"1,2\n" * 11)) == "too_many_rows"
    assert error_code(upload(c, b"a,b,c,d\n1,2,3,4\n")) == "too_many_columns"


def test_bom_and_semicolon_with_decimal_comma(client):
    content = "﻿name;score;group\nA;3,5;x\nB;4,25;y\nC;1;x\n".encode("utf-8")
    body = upload(client, content).get_json()
    cols = {c["name"]: c for c in body["profile"]["columns"]}
    assert list(cols) == ["name", "score", "group"]  # BOM stripped from first header
    assert body["dataset"]["delimiter"] == "semicolon"
    assert cols["score"]["type"] == "numeric"


def test_tab_delimiter(client):
    body = upload(client, b"x\ty\n1\ta\n2\tb\n3\ta\n").get_json()
    assert body["dataset"]["delimiter"] == "tab"
    assert body["dataset"]["columns"] == 2


def test_missing_and_duplicate_detection(client):
    df = pd.DataFrame({"a": [1, 2, np.nan, 1, 5], "b": ["x", None, "y", "x", "z"], "c": [1, 1, 1, 1, 1]})
    body = upload(client, df).get_json()
    prof = body["profile"]
    cols = {c["name"]: c for c in prof["columns"]}
    assert cols["a"]["missing"] == 1 and cols["b"]["missing"] == 1
    assert prof["missing_cells"] == 2
    assert prof["duplicate_rows"] == 1
    assert cols["c"]["type"] == "constant"
    codes = {i["code"] for i in prof["issues"]}
    assert {"constant_columns", "duplicate_rows"} <= codes


def test_duplicate_and_blank_column_names(client):
    body = upload(client, b"a,a,,b\n1,2,3,4\n5,6,7,8\n").get_json()
    names = [c["name"] for c in body["profile"]["columns"]]
    assert names == ["a", "a (2)", "unnamed_3", "b"]
    codes = {i["code"] for i in body["profile"]["issues"]}
    assert {"duplicate_column_names", "blank_column_names"} <= codes


def test_high_cardinality_detection(client):
    n = 200
    df = pd.DataFrame({"city": [f"c{i % 120}" for i in range(n)], "y": ["a", "b"] * (n // 2)})
    body = upload(client, df).get_json()
    cols = {c["name"]: c for c in body["profile"]["columns"]}
    assert "high_cardinality" in cols["city"]["flags"]


def test_failed_upload_keeps_previous_dataset(client, store):
    upload(client, make_students(80))
    sess = current_session(client, store)
    old_path = sess.file_path
    assert upload(client, b"").status_code == 422
    assert sess.df is not None and len(sess.df) == 80
    assert sess.file_path == old_path
    # Only the original temp file remains on disk.
    import os
    assert os.listdir(store.upload_dir) == [os.path.basename(old_path)]


def test_security_headers_and_no_session_id_leak(client):
    resp = upload(client, make_students(40))
    cookie = resp.headers.get("Set-Cookie")
    assert "HttpOnly" in cookie
    assert "X-Session-Id" not in resp.headers
    assert resp.headers["Cache-Control"] == "no-store"
