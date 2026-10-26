"""ScholarSense API: Flask app factory."""
import atexit
import logging
import os

from flask import Flask, g, request
from flask_cors import CORS

from config import Config
from errors import register_error_handlers
from routes.analysis import bp as analysis_bp
from routes.common import ok
from routes.explanations import bp as explanations_bp
from routes.export import bp as export_bp
from routes.interventions import bp as interventions_bp
from routes.predictions import bp as predictions_bp
from routes.training import bp as training_bp
from routes.upload import bp as upload_bp
from services.session_store import SessionStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(config_object=None, **overrides):
    cfg = config_object or Config
    if overrides:
        cfg = type("OverriddenConfig", (cfg,), overrides)
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = cfg.MAX_CONTENT_LENGTH
    app.config["MAX_UPLOAD_MB"] = cfg.MAX_UPLOAD_MB
    app.config["JSON_SORT_KEYS"] = False

    store = SessionStore(cfg.UPLOAD_DIR, cfg.SESSION_TTL_SECONDS)
    app.extensions["session_store"] = store
    app.extensions["scholarsense_config"] = cfg
    atexit.register(store.cleanup_all)

    CORS(app, resources={r"/api/*": {"origins": cfg.CORS_ORIGINS}}, supports_credentials=True)
    register_error_handlers(app)

    for bp in (upload_bp, analysis_bp, training_bp, predictions_bp, explanations_bp, interventions_bp, export_bp):
        app.register_blueprint(bp, url_prefix="/api")

    @app.before_request
    def _expire_sessions():
        store.maybe_cleanup(cfg.CLEANUP_INTERVAL_SECONDS)

    @app.after_request
    def _finalize(resp):
        new_sid = g.pop("new_session_id", None)
        if new_sid:
            resp.set_cookie(cfg.SESSION_COOKIE, new_sid, httponly=True, samesite="Lax",
                            secure=cfg.SESSION_COOKIE_SECURE, max_age=cfg.SESSION_TTL_SECONDS)
        if g.pop("clear_session_cookie", False):
            resp.delete_cookie(cfg.SESSION_COOKIE)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cross-Origin-Resource-Policy"] = "same-site"
        if request.path.startswith("/api"):
            resp.headers["Cache-Control"] = "no-store"
            resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return resp

    @app.get("/api/health")
    def health():
        return ok({"status": "ok", "service": "scholarsense-api", "sessions": len(store)})

    return app


if __name__ == "__main__":
    port = int(os.environ.get("SCHOLARSENSE_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    create_app().run(host="127.0.0.1", port=port, debug=debug, use_reloader=False)
