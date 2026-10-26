"""Model training and metrics."""
import logging

from flask import Blueprint

from routes.common import body_json, cfg, ok, require_config, require_dataset, require_training
from services.train_models import parse_params, train_models, training_summary

log = logging.getLogger("scholarsense")
bp = Blueprint("training", __name__)


@bp.post("/models/train")
def train():
    sess = require_dataset()
    require_config(sess)
    params = parse_params(body_json(), cfg())
    with sess.lock:
        training = train_models(sess.df, sess.config, params, cfg())
        sess.training = training
        # Downstream results belong to the previous models.
        sess.predictions = None
        sess.explanations = {}
        sess.reviews = {}
    return ok({"stage": sess.stage, "metrics": training_summary(training)})


@bp.get("/models/metrics")
def metrics():
    sess = require_dataset()
    require_training(sess)
    return ok({"stage": sess.stage, "metrics": training_summary(sess.training)})
