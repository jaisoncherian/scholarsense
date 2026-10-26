"""Shared route helpers: session resolution, stage guards and JSON responses."""
from flask import current_app, g, jsonify, request

from errors import ApiError
from services.serialization import jsonable

SESSION_HEADER = "X-Session-Id"


def store():
    return current_app.extensions["session_store"]


def cfg():
    return current_app.extensions["scholarsense_config"]


def current_session(create=False):
    """Session from the httpOnly cookie (or X-Session-Id header). Unknown ids are never adopted."""
    sid = request.cookies.get(cfg().SESSION_COOKIE) or request.headers.get(SESSION_HEADER)
    sess = store().get(sid)
    if sess is None and create:
        sess = store().create()
        g.new_session_id = sess.id
    return sess


def ok(payload, status=200):
    resp = jsonify(jsonable(payload))
    resp.status_code = status
    return resp


def body_json():
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_body", "The request body must be a JSON object.")
    return data


def require_dataset():
    sess = current_session()
    if sess is None or sess.df is None:
        raise ApiError(404, "no_dataset", "No dataset has been uploaded in this session.")
    return sess


def require_config(sess):
    if sess.config is None:
        raise ApiError(409, "target_not_confirmed", "Confirm the target column and feature configuration first.")


def require_training(sess):
    require_config(sess)
    if sess.training is None:
        raise ApiError(409, "models_not_trained", "Train the models first.")


def require_predictions(sess):
    require_training(sess)
    if sess.predictions is None:
        raise ApiError(409, "predictions_not_generated", "Generate predictions first.")


def resolve_model(sess, requested):
    """'selected' (default) maps to the model chosen by the documented criteria."""
    if requested in (None, "", "selected"):
        return sess.training["selection"]["selected"]
    if requested not in ("logistic_regression", "random_forest"):
        raise ApiError(400, "invalid_model", "model must be 'selected', 'logistic_regression' or 'random_forest'.")
    if requested not in sess.training["pipelines"]:
        raise ApiError(422, "model_unavailable", f"{requested} is not available (it may have failed to train).",
                       {"failures": sess.training["failures"]})
    return requested


def int_arg(name, default, minimum=None, maximum=None):
    raw = request.args.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ApiError(400, "invalid_parameter", f"'{name}' must be an integer.")
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value
