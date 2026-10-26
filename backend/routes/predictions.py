"""Scoring, querying and risk thresholds."""
import logging

from flask import Blueprint, request

from routes.common import (body_json, int_arg, ok, require_dataset, require_predictions, require_training,
                           resolve_model)
from services.evaluation import MODEL_LABELS
from services.predictions import (RISK_NOTE, SPLIT_NOTES, generate_predictions, query_predictions,
                                  validate_thresholds)

log = logging.getLogger("scholarsense")
bp = Blueprint("predictions", __name__)


def prediction_meta(sess, thresholds):
    p, t = sess.predictions, sess.training
    return {
        "model": p["model"], "model_label": MODEL_LABELS[p["model"]],
        "selected_model": t["selection"]["selected"],
        "scope": p["scope"], "classes": p["classes"],
        "at_risk_class": t["at_risk_class"],
        "thresholds": thresholds, "saved_thresholds": sess.thresholds,
        "features": t["features"], "timing_label": t["timing_label"], "early_prediction": t["early_prediction"],
        "id_column": sess.config.get("id_column"),
        "risk_note": RISK_NOTE, "split_notes": SPLIT_NOTES,
        "generated_at": p["generated_at"],
    }


def effective_thresholds(sess):
    low, high = request.args.get("low"), request.args.get("high")
    if low is None and high is None:
        return sess.thresholds
    return validate_thresholds(low if low is not None else sess.thresholds["low"],
                               high if high is not None else sess.thresholds["high"])


@bp.post("/predictions")
def create_predictions():
    sess = require_dataset()
    require_training(sess)
    body = body_json()
    model = resolve_model(sess, body.get("model"))
    scope = body.get("scope") or "test"
    with sess.lock:
        sess.predictions = generate_predictions(sess.df, sess.config, sess.training, model, scope)
        sess.reviews = {}
    log.info("predictions sid=%s model=%s rows=%d", sess.id[:8], model, len(sess.predictions["frame"]))
    result = query_predictions(sess.predictions, sess.thresholds, split="all", page_size=25)
    return ok({"stage": sess.stage, "meta": prediction_meta(sess, sess.thresholds), **result}, 201)


@bp.get("/predictions")
def list_predictions():
    sess = require_dataset()
    require_predictions(sess)
    thresholds = effective_thresholds(sess)
    result = query_predictions(
        sess.predictions, thresholds,
        split=request.args.get("split", "test"),
        predicted_class=request.args.get("predicted_class") or None,
        risk=request.args.get("risk") or None,
        q=request.args.get("q") or None,
        sort=request.args.get("sort", "risk_desc"),
        page=int_arg("page", 1, 1),
        page_size=int_arg("page_size", 25, 1, 200),
    )
    return ok({"stage": sess.stage, "meta": prediction_meta(sess, thresholds), **result})


@bp.put("/predictions/thresholds")
def set_thresholds():
    sess = require_dataset()
    body = body_json()
    with sess.lock:
        sess.thresholds = validate_thresholds(body.get("low"), body.get("high"))
    return ok({"thresholds": sess.thresholds})
