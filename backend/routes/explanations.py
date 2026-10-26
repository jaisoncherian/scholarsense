"""Global and local explanations."""
import logging
import time

from flask import Blueprint, request

from errors import ApiError
from routes.common import cfg, ok, require_dataset, require_training, resolve_model
from services.explainability import global_importance, local_explanation
from services.predictions import row_identifiers, split_labels

log = logging.getLogger("scholarsense")
bp = Blueprint("explanations", __name__)


@bp.get("/explanations/global")
def global_explanations():
    sess = require_dataset()
    require_training(sess)
    model = resolve_model(sess, request.args.get("model"))
    scoring = request.args.get("scoring", "f1_macro")
    key = (model, scoring)
    with sess.lock:
        if key not in sess.explanations:
            started = time.time()
            sess.explanations[key] = global_importance(sess.training, model, scoring, cfg())
            log.info("permutation importance sid=%s model=%s seconds=%.2f", sess.id[:8], model, time.time() - started)
        result = sess.explanations[key]
    return ok({"explanation": result, "features": sess.training["features"],
               "timing_label": sess.training["timing_label"]})


@bp.get("/explanations/local/<int:row_id>")
def local_explanations(row_id):
    sess = require_dataset()
    require_training(sess)
    if row_id not in sess.df.index:
        raise ApiError(404, "row_not_found", f"Row {row_id} does not exist in this dataset.")
    model = resolve_model(sess, request.args.get("model"))
    split = split_labels(sess.df, sess.training).loc[row_id]
    result = local_explanation(sess.df, sess.config, sess.training, model, row_id, split)
    result["identifier"] = row_identifiers(sess.df, sess.config.get("id_column"), [row_id])[0]
    return ok({"explanation": result})
