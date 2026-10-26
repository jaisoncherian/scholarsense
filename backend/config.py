"""Runtime configuration. Every limit can be overridden with an environment variable."""
import os
import tempfile


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _float_env(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    # Upload limits
    MAX_UPLOAD_MB = _int_env("SCHOLARSENSE_MAX_UPLOAD_MB", 20)
    MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
    # Flask rejects bodies larger than this with 413 before we read them.
    # A small margin covers multipart framing overhead.
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES + 64 * 1024
    MAX_ROWS = _int_env("SCHOLARSENSE_MAX_ROWS", 200_000)
    MAX_COLUMNS = _int_env("SCHOLARSENSE_MAX_COLUMNS", 500)
    PREVIEW_ROWS = 20

    # Temp files live outside any served directory.
    UPLOAD_DIR = os.environ.get(
        "SCHOLARSENSE_UPLOAD_DIR",
        os.path.join(tempfile.gettempdir(), "scholarsense_uploads"),
    )

    # Sessions
    SESSION_TTL_SECONDS = _int_env("SCHOLARSENSE_SESSION_TTL_MINUTES", 60) * 60
    SESSION_COOKIE = "ss_session"
    SESSION_COOKIE_SECURE = os.environ.get("SCHOLARSENSE_COOKIE_SECURE", "0") == "1"
    CLEANUP_INTERVAL_SECONDS = 60

    # Modelling
    RANDOM_SEED = 42
    DEFAULT_TEST_SIZE = 0.2
    MIN_TEST_SIZE = 0.1
    MAX_TEST_SIZE = 0.5
    MIN_TRAIN_ROWS = 30
    MIN_CLASS_ROWS = 2
    RECOMMENDED_CLASS_ROWS = 5
    MAX_TARGET_CLASSES = 20
    RF_DEFAULT_ESTIMATORS = 200
    RF_LARGE_DATA_ESTIMATORS = 100
    RF_LARGE_DATA_ROWS = 50_000
    RF_MAX_ESTIMATORS = 300
    RF_N_JOBS = _int_env("SCHOLARSENSE_RF_N_JOBS", 4)
    LR_MAX_ITER = 2000
    OHE_MAX_CATEGORIES = 50
    SELECTION_TOLERANCE = 0.01

    # Explainability
    PERMUTATION_REPEATS = 5
    PERMUTATION_MAX_ROWS = 5000

    # Risk thresholds (model-estimated, not calibrated)
    RISK_LOW_THRESHOLD = _float_env("SCHOLARSENSE_RISK_LOW", 0.33)
    RISK_HIGH_THRESHOLD = _float_env("SCHOLARSENSE_RISK_HIGH", 0.66)

    # CORS: only the Vite dev origin by default.
    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get(
            "SCHOLARSENSE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]
