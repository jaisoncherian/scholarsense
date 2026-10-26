"""Rule-based support suggestions driven only by columns present in the dataset.

Rules fire on observed evidence (dataset quartiles or user thresholds). Model
output is reported alongside but never used as evidence. Demographic columns
can never trigger a rule.
"""
import re
import time

import numpy as np
import pandas as pd

from errors import ApiError
from services.data_validation import is_demographic
from services.serialization import display_value, round_or_none

REVIEW_STATUSES = ["Not reviewed", "In review", "Actioned", "Dismissed"]
CATEGORIES = ["performance", "attendance", "financial"]
DIRECTIONS = ["low", "high", "truthy", "falsy"]
DISCLAIMER = "Suggestions for staff review, not automated decisions."

_PERFORMANCE_RE = re.compile(r"grade|gpa|score|marks?\b|exam|approved|passed|credits?.?earned|earned.?credits?", re.I)
_ATTENDANCE_RE = re.compile(r"attend|absen|presence", re.I)
_FIN_NEGATIVE_RE = re.compile(r"debt|owed|arrear|overdue|outstanding", re.I)
_FIN_POSITIVE_FLAG_RE = re.compile(r"up.?to.?date|paid|cleared", re.I)
_FIN_AMOUNT_RE = re.compile(r"debt|owed|arrear|overdue|balance|outstanding", re.I)
_TRUTHY = {"1", "true", "yes", "y", "t"}

RULES = [
    {"id": "academic_support", "category": "performance", "title": "Academic support",
     "text": "Offer tutoring or a mentoring check-in focused on the areas shown in the evidence."},
    {"id": "attendance_conversation", "category": "attendance", "title": "Supportive attendance conversation",
     "text": "Arrange a supportive conversation to understand any barriers to attending and agree on practical next steps."},
    {"id": "financial_aid_referral", "category": "financial", "title": "Financial-aid referral",
     "text": "Share information about financial-aid and hardship options and offer a referral to the financial-aid office."},
    {"id": "advisor_review", "category": None, "title": "Advisor / counselor review",
     "text": "Indicators in two or more areas are present; consider a holistic check-in with an academic advisor or counselor."},
]
CATEGORY_LABELS = {"performance": "Academic performance", "attendance": "Attendance", "financial": "Financial"}


def _binary_truthy(s):
    """Boolean Series (NaN for missing) if the column is binary, else None."""
    nonnull = s.dropna()
    if nonnull.empty or nonnull.nunique() > 2:
        return None
    if pd.api.types.is_numeric_dtype(s):
        if not set(np.unique(nonnull.astype(float))) <= {0.0, 1.0}:
            return None
        return s.map(lambda v: None if pd.isna(v) else float(v) == 1.0)
    low = nonnull.astype(str).str.lower()
    if not set(low.unique()) <= _TRUTHY | {"0", "false", "no", "n", "f"}:
        return None
    return s.map(lambda v: None if pd.isna(v) else str(v).lower() in _TRUTHY)


def _excluded_columns(config, profile):
    skip = {config["target"], config.get("id_column")}
    skip |= {c["name"] for c in profile["columns"] if c["type"] in ("identifier", "constant", "datetime")}
    return skip


def detect_indicators(df, config, profile):
    """Auto-detect indicator columns by name keywords + numeric type.

    Columns the user excluded as "not available at prediction time" are skipped
    (staff can still map them explicitly).
    """
    indicators = []
    later = {e["column"] for e in config.get("exclusions", []) if e["reason"] == "later_term"}
    for col in df.columns:
        if col in _excluded_columns(config, profile) or col in later or is_demographic(col):
            continue
        s = df[col]
        binary = _binary_truthy(s)
        numeric = pd.api.types.is_numeric_dtype(s) and binary is None
        name = str(col)
        if _PERFORMANCE_RE.search(name) and numeric:
            indicators.append({"column": col, "category": "performance", "direction": "low"})
        elif _ATTENDANCE_RE.search(name) and numeric:
            indicators.append({"column": col, "category": "attendance",
                               "direction": "high" if re.search(r"absen", name, re.I) else "low"})
        elif binary is not None and _FIN_NEGATIVE_RE.search(name):
            indicators.append({"column": col, "category": "financial", "direction": "truthy"})
        elif binary is not None and _FIN_POSITIVE_FLAG_RE.search(name) and re.search(r"fee|tuition|payment", name, re.I):
            indicators.append({"column": col, "category": "financial", "direction": "falsy"})
        elif numeric and _FIN_AMOUNT_RE.search(name):
            indicators.append({"column": col, "category": "financial", "direction": "high"})
    for ind in indicators:
        ind.update({"threshold": None, "source": "auto"})
    return indicators


def validate_mapping(df, config, profile, items):
    if not isinstance(items, list):
        raise ApiError(400, "invalid_mapping", "indicators must be a list.")
    out = []
    excluded = _excluded_columns(config, profile)
    for item in items:
        col = item.get("column")
        cat = item.get("category")
        direction = item.get("direction")
        if col not in df.columns:
            raise ApiError(422, "unknown_column", f"Column '{col}' does not exist.", {"column": col})
        if col in excluded:
            raise ApiError(422, "column_not_allowed", f"'{col}' is the target, identifier, constant or date column.")
        if is_demographic(col):
            raise ApiError(422, "demographic_column", "Demographic attributes cannot be used to trigger support rules.",
                           {"column": col})
        if cat not in CATEGORIES:
            raise ApiError(400, "invalid_category", f"category must be one of {CATEGORIES}.")
        if direction not in DIRECTIONS:
            raise ApiError(400, "invalid_direction", f"direction must be one of {DIRECTIONS}.")
        binary = _binary_truthy(df[col])
        if direction in ("truthy", "falsy") and binary is None:
            raise ApiError(422, "not_binary", f"'{col}' is not a yes/no column.")
        if direction in ("low", "high") and not pd.api.types.is_numeric_dtype(df[col]):
            raise ApiError(422, "not_numeric", f"'{col}' must be numeric for a threshold rule.")
        threshold = item.get("threshold")
        if threshold not in (None, ""):
            try:
                threshold = float(threshold)
            except (TypeError, ValueError):
                raise ApiError(400, "invalid_threshold", "threshold must be a number.")
        else:
            threshold = None
        out.append({"column": col, "category": cat, "direction": direction, "threshold": threshold, "source": "user"})
    return out


def evaluate_indicator(df, ind):
    """Boolean fired-mask over all rows plus a description of the comparison basis."""
    s = df[ind["column"]]
    d = ind["direction"]
    if d in ("truthy", "falsy"):
        flags = _binary_truthy(s)
        mask = flags.map(lambda v: v is not None and (bool(v) if d == "truthy" else not bool(v)))
        basis = "value indicates yes" if d == "truthy" else "value indicates no"
        return mask.astype(bool), basis, None
    vals = pd.to_numeric(s, errors="coerce").astype(float)
    nonnull = vals.dropna()
    if nonnull.empty:
        return pd.Series(False, index=df.index), "no values", None
    if ind.get("threshold") is not None:
        t = ind["threshold"]
        mask = vals < t if d == "low" else vals > t
        return mask.fillna(False), f"{'below' if d == 'low' else 'above'} the staff-set threshold of {t:g}", t
    q1, med, q3 = np.percentile(nonnull, [25, 50, 75])
    if d == "low":
        mask = vals < q1
        if q1 == nonnull.min() and q1 < med:  # many ties at the minimum
            mask = vals <= q1
            basis = f"at or below the dataset's lower quartile (Q1 = {q1:g}, also the minimum)"
        else:
            basis = f"below the dataset's lower quartile (Q1 = {q1:g})"
        return mask.fillna(False), basis, float(q1)
    mask = vals > q3
    if q3 == nonnull.max() and q3 > med:
        mask = vals >= q3
        basis = f"at or above the dataset's upper quartile (Q3 = {q3:g}, also the maximum)"
    else:
        basis = f"above the dataset's upper quartile (Q3 = {q3:g})"
    return mask.fillna(False), basis, float(q3)


def rule_availability(indicators):
    cats = {i["category"] for i in indicators}
    out = []
    for rule in RULES:
        if rule["category"] is None:
            ok = len(cats) >= 2
            reason = None if ok else "Needs indicator columns in at least two areas (performance, attendance, financial)."
        else:
            ok = rule["category"] in cats
            reason = None if ok else f"No {CATEGORY_LABELS[rule['category']].lower()} columns were detected or mapped."
        out.append({"id": rule["id"], "title": rule["title"], "text": rule["text"], "available": ok, "reason": reason})
    return out


def build_interventions(df, indicators, pred_rows, reviews):
    """pred_rows: DataFrame of scored rows with risk_category. Returns per-student records with ≥1 suggestion."""
    evaluated = [(ind, *evaluate_indicator(df, ind)) for ind in indicators]
    if not evaluated:
        return []
    any_fired = np.logical_or.reduce([mask.to_numpy() for _, mask, _, _ in evaluated])
    pred_rows = pred_rows[pred_rows["row_id"].isin(df.index[any_fired])]
    records = []
    for _, row in pred_rows.iterrows():
        rid = int(row["row_id"])
        evidence = []
        for ind, mask, basis, _ in evaluated:
            if bool(mask.loc[rid]):
                evidence.append({"column": ind["column"], "category": ind["category"],
                                 "category_label": CATEGORY_LABELS[ind["category"]],
                                 "value": display_value(df.at[rid, ind["column"]]), "comparison": basis,
                                 "source": ind["source"]})
        if not evidence:
            continue
        cats = sorted({e["category"] for e in evidence}, key=CATEGORIES.index)
        suggestions = []
        for rule in RULES:
            if rule["category"] in cats:
                suggestions.append({"rule_id": rule["id"], "title": rule["title"], "text": rule["text"],
                                    "evidence_columns": [e["column"] for e in evidence if e["category"] == rule["category"]]})
        if len(cats) >= 2:
            rule = RULES[-1]
            suggestions.append({"rule_id": rule["id"], "title": rule["title"], "text": rule["text"],
                                "evidence_columns": [e["column"] for e in evidence]})
        review = reviews.get(rid, {"status": "Not reviewed", "note": None, "updated_at": None})
        records.append({
            "row_id": rid, "identifier": row["identifier"], "split": row["split"],
            "evidence": evidence, "indicator_areas": cats, "suggestions": suggestions,
            "model_output": {"label": "Model output (estimate, not an observed fact)",
                             "predicted_class": row["predicted_class"],
                             "risk_score": round_or_none(row["risk_score"]),
                             "risk_category": row["risk_category"]},
            "review": review,
        })
    return records


def make_review(status, note):
    if status not in REVIEW_STATUSES:
        raise ApiError(400, "invalid_status", f"status must be one of {REVIEW_STATUSES}.")
    if note is not None:
        note = str(note)[:500]
    return {"status": status, "note": note, "updated_at": time.time()}
