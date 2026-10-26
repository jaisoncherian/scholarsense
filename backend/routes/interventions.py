"""Rule-based support suggestions, indicator mapping and review status."""
import pandas as pd
from flask import Blueprint, request

from errors import ApiError
from routes.common import body_json, int_arg, ok, require_dataset, require_predictions
from services.predictions import RISK_CATEGORIES, with_categories
from services.recommendations import (CATEGORIES, DIRECTIONS, DISCLAIMER, REVIEW_STATUSES, _binary_truthy,
                                      _excluded_columns, build_interventions, detect_indicators, is_demographic,
                                      make_review, rule_availability, validate_mapping)

bp = Blueprint("interventions", __name__)


def effective_indicators(sess):
    if sess.indicator_mapping is not None:
        return sess.indicator_mapping
    return detect_indicators(sess.df, sess.config, sess.profile)


def scored_rows(sess):
    return with_categories(sess.predictions["frame"], sess.thresholds)


def all_records(sess):
    return build_interventions(sess.df, effective_indicators(sess), scored_rows(sess), sess.reviews)


@bp.get("/interventions")
def list_interventions():
    sess = require_dataset()
    require_predictions(sess)
    indicators = effective_indicators(sess)
    records = all_records(sess)
    status_counts = {s: 0 for s in REVIEW_STATUSES}
    rule_counts = {}
    for r in records:
        status_counts[r["review"]["status"]] += 1
        for s in r["suggestions"]:
            rule_counts[s["rule_id"]] = rule_counts.get(s["rule_id"], 0) + 1

    split = request.args.get("split", "all")
    risk = request.args.get("risk") or None
    status = request.args.get("status") or None
    rule = request.args.get("rule") or None
    q = (request.args.get("q") or "").strip().lower()
    if risk and risk not in RISK_CATEGORIES:
        raise ApiError(400, "invalid_risk_category", "risk must be Low, Medium or High.")
    if status and status not in REVIEW_STATUSES:
        raise ApiError(400, "invalid_status", f"status must be one of {REVIEW_STATUSES}.")
    filtered = [r for r in records
                if (split == "all" or r["split"] == split)
                and (not risk or r["model_output"]["risk_category"] == risk)
                and (not status or r["review"]["status"] == status)
                and (not rule or any(s["rule_id"] == rule for s in r["suggestions"]))
                and (not q or q in str(r["identifier"]).lower())]
    filtered.sort(key=lambda r: (-(r["model_output"]["risk_score"] or 0), r["row_id"]))
    page_size = int_arg("page_size", 20, 1, 100)
    pages = max(1, -(-len(filtered) // page_size))
    page = min(int_arg("page", 1, 1), pages)
    return ok({
        "disclaimer": DISCLAIMER,
        "indicators": indicators,
        "mapping_mode": "user" if sess.indicator_mapping is not None else "auto",
        "rules": rule_availability(indicators),
        "summary": {"students_with_suggestions": len(records), "scored_rows": int(len(sess.predictions["frame"])),
                    "by_status": status_counts, "by_rule": rule_counts},
        "records": filtered[(page - 1) * page_size: page * page_size],
        "total": len(filtered), "page": page, "page_size": page_size, "pages": pages,
        "at_risk_class": sess.training["at_risk_class"],
        "thresholds": sess.thresholds,
    })


@bp.get("/interventions/mapping")
def get_mapping():
    sess = require_dataset()
    if sess.config is None:
        raise ApiError(409, "target_not_confirmed", "Confirm the target column first.")
    excluded = _excluded_columns(sess.config, sess.profile)
    candidates = []
    for col in sess.df.columns:
        if col in excluded or is_demographic(col):
            continue
        binary = _binary_truthy(sess.df[col]) is not None
        numeric = pd.api.types.is_numeric_dtype(sess.df[col])
        if binary or numeric:
            candidates.append({"column": col, "binary": binary, "numeric": numeric and not binary})
    return ok({
        "indicators": effective_indicators(sess),
        "auto_detected": detect_indicators(sess.df, sess.config, sess.profile),
        "mode": "user" if sess.indicator_mapping is not None else "auto",
        "candidates": candidates,
        "categories": CATEGORIES, "directions": DIRECTIONS,
        "note": "Demographic attributes (e.g. gender, nationality, age) are never used to trigger suggestions.",
    })


@bp.put("/interventions/mapping")
def put_mapping():
    sess = require_dataset()
    if sess.config is None:
        raise ApiError(409, "target_not_confirmed", "Confirm the target column first.")
    body = body_json()
    with sess.lock:
        if body.get("reset"):
            sess.indicator_mapping = None
        else:
            sess.indicator_mapping = validate_mapping(sess.df, sess.config, sess.profile, body.get("indicators"))
    return ok({"indicators": effective_indicators(sess),
               "mode": "user" if sess.indicator_mapping is not None else "auto"})


def _row_record(sess, row_id):
    frame = scored_rows(sess)
    row = frame[frame["row_id"] == row_id]
    if row.empty:
        raise ApiError(404, "row_not_scored", f"Row {row_id} has no prediction. Score it on the Risk Predictions page.")
    recs = build_interventions(sess.df, effective_indicators(sess), row, sess.reviews)
    if recs:
        return recs[0]
    r = row.iloc[0]
    return {"row_id": row_id, "identifier": r["identifier"], "split": r["split"], "evidence": [],
            "indicator_areas": [], "suggestions": [],
            "model_output": {"label": "Model output (estimate, not an observed fact)",
                             "predicted_class": r["predicted_class"], "risk_score": float(r["risk_score"]),
                             "risk_category": r["risk_category"]},
            "review": sess.reviews.get(row_id, {"status": "Not reviewed", "note": None, "updated_at": None}),
            "message": "No support rule fired for this student based on the available columns."}


@bp.get("/interventions/<int:row_id>")
def get_intervention(row_id):
    sess = require_dataset()
    require_predictions(sess)
    indicators = effective_indicators(sess)
    return ok({"disclaimer": DISCLAIMER, "record": _row_record(sess, row_id),
               "rules": rule_availability(indicators)})


@bp.patch("/interventions/<int:row_id>/review")
def review(row_id):
    sess = require_dataset()
    require_predictions(sess)
    body = body_json()
    _row_record(sess, row_id)  # 404 if not scored
    with sess.lock:
        sess.reviews[row_id] = make_review(body.get("status"), body.get("note"))
    return ok({"row_id": row_id, "review": sess.reviews[row_id]})
