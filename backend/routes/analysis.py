"""Exploratory data analysis."""
import logging
import time

from flask import Blueprint

from errors import ApiError
from routes.common import ok, require_config, require_dataset
from services.eda import compute_eda

log = logging.getLogger("scholarsense")
bp = Blueprint("analysis", __name__)


@bp.post("/analysis")
def run_analysis():
    sess = require_dataset()
    require_config(sess)
    started = time.time()
    with sess.lock:
        sess.eda = compute_eda(sess.df, sess.profile, sess.config)
    log.info("analysis sid=%s seconds=%.2f", sess.id[:8], time.time() - started)
    return ok({"stage": sess.stage, "analysis": sess.eda})


@bp.get("/analysis")
def get_analysis():
    sess = require_dataset()
    if sess.eda is None:
        raise ApiError(404, "analysis_not_available", "Run the analysis first.")
    return ok({"stage": sess.stage, "analysis": sess.eda})
