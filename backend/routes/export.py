"""CSV export with CSV-injection neutralisation."""
import csv
import io

import pandas as pd

from flask import Blueprint, Response, request

from errors import ApiError
from routes.common import require_dataset, require_predictions
from routes.interventions import all_records
from services.evaluation import MODEL_LABELS
from services.predictions import RISK_NOTE, with_categories

bp = Blueprint("export", __name__)

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def neutralize(value):
    """Prefix text cells that a spreadsheet could interpret as a formula."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def to_csv(header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([neutralize(h) for h in header])
    for row in rows:
        writer.writerow([neutralize(v) for v in row])
    return buf.getvalue()


def _fmt(x):
    return "" if x is None else round(float(x), 6)


def predictions_csv(sess):
    p = sess.predictions
    frame = with_categories(p["frame"], sess.thresholds).sort_values("row_id")
    classes = p["classes"]
    header = (["identifier", "row_number", "split", "predicted_class"] + [f"probability_{c}" for c in classes]
              + ["risk_score", "risk_category", "at_risk_class", "observed_outcome", "model", "risk_thresholds", "note"])
    thresholds = f"low<{sess.thresholds['low']}; medium<{sess.thresholds['high']}; high>={sess.thresholds['high']}"
    rows = []
    for _, r in frame.iterrows():
        rows.append([r["identifier"], int(r["row_id"]) + 1, r["split"], r["predicted_class"]]
                    + [_fmt(r[f"prob::{c}"]) for c in classes]
                    + [_fmt(r["risk_score"]), r["risk_category"], sess.training["at_risk_class"],
                       "" if pd.isna(r["observed"]) else r["observed"], MODEL_LABELS[p["model"]], thresholds, RISK_NOTE])
    return to_csv(header, rows)


def interventions_csv(sess):
    header = ["identifier", "row_number", "split", "suggestion", "suggestion_detail", "evidence",
              "model_predicted_class", "model_risk_score", "model_risk_category", "review_status", "review_note", "note"]
    rows = []
    for rec in sorted(all_records(sess), key=lambda r: r["row_id"]):
        evidence = "; ".join(f"{e['column']} = {e['value']} ({e['comparison']})" for e in rec["evidence"])
        for s in rec["suggestions"]:
            rows.append([rec["identifier"], rec["row_id"] + 1, rec["split"], s["title"], s["text"], evidence,
                         rec["model_output"]["predicted_class"], _fmt(rec["model_output"]["risk_score"]),
                         rec["model_output"]["risk_category"], rec["review"]["status"], rec["review"]["note"] or "",
                         "Suggestion for staff review, not an automated decision."])
    return to_csv(header, rows)


@bp.get("/export")
def export():
    sess = require_dataset()
    require_predictions(sess)
    kind = request.args.get("type")
    if kind == "predictions":
        content = predictions_csv(sess)
    elif kind == "interventions":
        content = interventions_csv(sess)
    else:
        raise ApiError(400, "invalid_export_type", "type must be 'predictions' or 'interventions'.")
    return Response(content, mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="scholarsense_{kind}.csv"'})
