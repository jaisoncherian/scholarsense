"""In-memory, per-session state with temp-file lifecycle management.

Each session holds the uploaded DataFrame and everything derived from it.
Nothing is written to disk except the raw upload, which is stored under a
random UUID filename and deleted on replacement, session deletion, TTL
expiry and process shutdown.
"""
import logging
import os
import re
import threading
import time
import uuid

log = logging.getLogger("scholarsense")

_SESSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def valid_session_id(value):
    return bool(value) and bool(_SESSION_ID_RE.match(value))


class SessionData:
    """All dataset-specific state for one browser session."""

    def __init__(self, session_id):
        self.id = session_id
        self.created_at = time.time()
        self.last_access = self.created_at
        # Guards mutation of this session by concurrent requests.
        self.lock = threading.RLock()
        self.file_path = None
        self.clear_dataset()

    def clear_dataset(self):
        """Drop every dataset-specific artefact (temp file is handled by the store)."""
        self.df = None
        self.dataset_info = None   # filename, size, delimiter, warnings
        self.profile = None        # per-column profile + issues
        self.target_check = None   # last dry-run target validation
        self.config = None         # confirmed target / feature config
        self.eda = None
        self.training = None       # fitted pipelines, split, metrics
        self.predictions = None    # scored rows
        self.thresholds = None     # risk thresholds (low, high)
        self.explanations = {}     # cached global explanations
        self.indicator_mapping = None
        self.reviews = {}          # row_id -> review record

    @property
    def stage(self):
        if self.df is None:
            return "empty"
        if self.predictions is not None:
            return "predicted"
        if self.training is not None:
            return "trained"
        if self.eda is not None:
            return "analyzed"
        if self.config is not None:
            return "configured"
        return "uploaded"

    def touch(self):
        self.last_access = time.time()


class SessionStore:
    def __init__(self, upload_dir, ttl_seconds):
        self.upload_dir = upload_dir
        self.ttl_seconds = ttl_seconds
        self._sessions = {}
        self._lock = threading.Lock()
        self._last_cleanup = 0.0
        os.makedirs(self.upload_dir, exist_ok=True)

    # --- session lookup -------------------------------------------------
    def get(self, session_id):
        if not valid_session_id(session_id):
            return None
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is not None:
                sess.touch()
            return sess

    def create(self):
        sid = uuid.uuid4().hex
        sess = SessionData(sid)
        with self._lock:
            self._sessions[sid] = sess
        log.info("session created sid=%s", sid[:8])
        return sess

    def __len__(self):
        with self._lock:
            return len(self._sessions)

    def __contains__(self, session_id):
        with self._lock:
            return session_id in self._sessions

    # --- temp files -----------------------------------------------------
    def new_upload_path(self):
        """Random server-side filename; the client filename is never used on disk."""
        os.makedirs(self.upload_dir, exist_ok=True)
        return os.path.join(self.upload_dir, f"{uuid.uuid4().hex}.upload")

    @staticmethod
    def _remove_file(path):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                log.warning("could not remove temp file")

    def reset_dataset(self, sess):
        """Delete the session's temp file and all dataset-derived state."""
        with sess.lock:
            self._remove_file(sess.file_path)
            sess.file_path = None
            sess.clear_dataset()

    def delete(self, session_id):
        with self._lock:
            sess = self._sessions.pop(session_id, None)
        if sess is not None:
            self.reset_dataset(sess)
            log.info("session deleted sid=%s", session_id[:8])
        return sess is not None

    # --- expiry ---------------------------------------------------------
    def cleanup_expired(self, now=None):
        now = time.time() if now is None else now
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if now - s.last_access > self.ttl_seconds]
            removed = [self._sessions.pop(sid) for sid in expired]
            self._last_cleanup = now
        for sess in removed:
            self.reset_dataset(sess)
            log.info("session expired sid=%s", sess.id[:8])
        return len(removed)

    def maybe_cleanup(self, interval_seconds):
        if time.time() - self._last_cleanup >= interval_seconds:
            self.cleanup_expired()

    def cleanup_all(self):
        """Called at process shutdown: remove every temp file and session."""
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for sess in sessions:
            self.reset_dataset(sess)
