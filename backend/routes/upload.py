"""Upload, dataset summary/preview, target + feature configuration, session deletion."""
import logging
import os
import time

from flask import Blueprint, g, request

from errors import ApiError
from routes.common import body_json, cfg, current_session, int_arg, ok, require_dataset, store
from services.data_validation import build_feature_config, profile_dataset, validate_target
from services.dataset_service import check_upload_type, parse_csv_file, sanitize_filename
from services.evaluation import MODEL_LABELS
from services.serialization import display_value

log = logging.getLogger("scholarsense")
bp = Blueprint("upload", __name__)


def build_summary(sess):
    if sess is None or sess.df is None:
        return {"stage": "empty"}
    summary = {
        "stage": sess.stage,
        "dataset": sess.dataset_info,
        "profile": sess.profile,
        "target_check": sess.target_check,
        "config": sess.config,
        "thresholds": sess.thresholds,
        "analysis_available": sess.eda is not None,
        "training": None,
        "predictions": None,
    }
    if sess.training is not None:
        t = sess.training
        summary["training"] = {
            "selected_model": t["selection"]["selected"],
            "selected_label": MODEL_LABELS.get(t["selection"]["selected"]),
            "models": list(t["pipelines"]),
            "failures": t["failures"],
            "at_risk_class": t["at_risk_class"],
            "trained_at": t["trained_at"],
        }
    if sess.predictions is not None:
        p = sess.predictions
        summary["predictions"] = {"model": p["model"], "model_label": MODEL_LABELS[p["model"]],
                                  "scope": p["scope"], "rows": int(len(p["frame"])), "generated_at": p["generated_at"]}
    return summary


@bp.post("/upload")
def upload():
    c = cfg()
    file = request.files.get("file")
    if file is None:
        raise ApiError(400, "missing_file", "Attach a CSV file in the 'file' form field.")
    raw = file.read(c.MAX_UPLOAD_BYTES + 1)
    if len(raw) > c.MAX_UPLOAD_BYTES:
        raise ApiError(413, "file_too_large", f"The uploaded file exceeds the {c.MAX_UPLOAD_MB} MB limit.",
                       {"max_mb": c.MAX_UPLOAD_MB})
    check_upload_type(file.filename, raw)

    sess = current_session(create=True)
    st = store()
    # Parse into a fresh temp file first: an invalid upload leaves the previous dataset untouched.
    path = st.new_upload_path()
    with open(path, "wb") as fh:
        fh.write(raw)
    try:
        df, meta = parse_csv_file(path, c.MAX_ROWS, c.MAX_COLUMNS)
        profile = profile_dataset(df, meta)
    except Exception:
        st._remove_file(path)
        raise

    with sess.lock:
        st.reset_dataset(sess)  # full reset of every dataset-specific artefact + old temp file
        sess.file_path = path
        sess.df = df
        sess.profile = profile
        sess.thresholds = {"low": c.RISK_LOW_THRESHOLD, "high": c.RISK_HIGH_THRESHOLD}
        sess.dataset_info = {
            "filename": sanitize_filename(file.filename),
            "size_bytes": len(raw),
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "encoding": meta["encoding"],
            "delimiter": meta["delimiter"],
            "uploaded_at": time.time(),
        }
    log.info("upload sid=%s shape=%s seconds=%s", sess.id[:8], df.shape, meta["parse_seconds"])
    return ok(build_summary(sess), 201)


@bp.get("/dataset/summary")
def summary():
    return ok(build_summary(current_session()))


@bp.get("/dataset/preview")
def preview():
    sess = require_dataset()
    n = int_arg("rows", cfg().PREVIEW_ROWS, 1, 100)
    head = sess.df.head(n)
    return ok({
        "columns": list(sess.df.columns),
        "rows": [[display_value(v) for v in row] for row in head.itertuples(index=False, name=None)],
        "row_ids": [int(i) for i in head.index],
        "total_rows": int(len(sess.df)),
    })


@bp.post("/dataset/target")
def configure_target():
    sess = require_dataset()
    body = body_json()
    target = body.get("target")
    dry_run = bool(body.get("dry_run", False))
    with sess.lock:
        info = validate_target(sess.df, sess.profile, target)
        id_column = body.get("id_column") or None
        features = build_feature_config(
            sess.profile, target, id_column=id_column,
            excluded=body.get("excluded_columns") or [],
            include_id_like=body.get("include_id_like") or [],
            timing_preset=body.get("timing_preset") or "all",
        )
        if dry_run:
            sess.target_check = {**info, "feature_preview": features}
            return ok({"confirmed": False, "target_info": info, "feature_config": features})

        at_risk = body.get("at_risk_class")
        if at_risk in (None, ""):
            raise ApiError(422, "at_risk_class_required", "Choose which class represents students at risk.",
                           {"classes": info["classes"], "suggested": info["suggested_at_risk_class"]})
        at_risk = str(at_risk)
        if at_risk not in info["classes"]:
            raise ApiError(422, "invalid_at_risk_class", "The at-risk class must be one of the target classes.",
                           {"classes": info["classes"]})
        # A new configuration invalidates everything computed from the previous one.
        sess.eda = None
        sess.training = None
        sess.predictions = None
        sess.explanations = {}
        sess.reviews = {}
        sess.indicator_mapping = None
        sess.target_check = {**info, "feature_preview": features}
        sess.config = {
            "target": target,
            "id_column": id_column,
            "at_risk_class": at_risk,
            "classes": info["classes"],
            "class_counts": info["class_counts"],
            "missing_target_rows": info["missing_target_rows"],
            "target_warnings": info["warnings"],
            "excluded_columns": list(body.get("excluded_columns") or []),
            "include_id_like": list(body.get("include_id_like") or []),
            **features,
            "confirmed_at": time.time(),
        }
    log.info("target confirmed sid=%s features=%d", sess.id[:8], len(features["features"]))
    return ok({"confirmed": True, "summary": build_summary(sess)})


@bp.delete("/session")
def delete_session():
    sess = current_session()
    if sess is not None:
        store().delete(sess.id)
    g.clear_session_cookie = True
    return ok({"deleted": sess is not None, "stage": "empty"})
