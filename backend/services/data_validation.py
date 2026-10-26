"""Column profiling, dataset issue detection, target validation and feature config."""
import re

import numpy as np
import pandas as pd

from errors import ApiError
from services.serialization import display_value, round_or_none

TARGET_NAME_HINTS = ["target", "outcome", "dropout", "status", "label", "class"]
AT_RISK_NAME_HINTS = ["dropout", "drop out", "dropped", "withdraw", "withdrawn", "at risk", "at-risk", "fail", "left"]
_ID_NAME_RE = re.compile(r"(^|[\s_\-.])(id|uuid|guid|key|code|number|no|num|index|idx)$|^id[\s_\-.]|student.?id", re.I)
LATER_TERM_RE = re.compile(r"2nd|second|semester[\s_\-]*2|sem[\s_\-]*2|final", re.I)
_BOOL_STRINGS = {"true", "false", "yes", "no", "y", "n", "t", "f"}
_DATE_HINT_RE = re.compile(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}")
DEMOGRAPHIC_TOKENS = {"gender", "sex", "nationality", "nacionality", "race", "ethnicity", "ethnic", "religion",
                      "age", "marital", "citizenship", "birth", "country", "origin", "disability"}


def is_demographic(name):
    """Name-token check for sensitive / demographic attributes."""
    tokens = set(re.split(r"[^a-z]+", str(name).lower()))
    return bool(tokens & DEMOGRAPHIC_TOKENS)


def _is_integer_valued(s):
    vals = s.dropna()
    if vals.empty:
        return False
    return bool(np.all(np.isclose(vals.astype(float) % 1, 0)))


def classify_column(name, s):
    """Return (type, details) for one column.

    type is one of numeric / categorical / boolean / datetime / identifier / constant.
    """
    n = len(s)
    nonnull = s.dropna()
    nn = len(nonnull)
    nunique = int(nonnull.nunique()) if nn else 0
    unique_ratio = (nunique / nn) if nn else 0.0
    numeric = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)

    if nunique <= 1:
        return "constant", {"all_missing": nn == 0}
    if pd.api.types.is_bool_dtype(s):
        return "boolean", {}
    if nunique == 2:
        if numeric and set(np.unique(nonnull.astype(float))) <= {0.0, 1.0}:
            return "boolean", {}
        if not numeric and set(nonnull.astype(str).str.lower().unique()) <= _BOOL_STRINGS:
            return "boolean", {}

    name_looks_like_id = bool(_ID_NAME_RE.search(str(name)))
    mostly_present = nn >= 0.9 * n
    if nn >= 10 and mostly_present and unique_ratio >= 0.98:
        if not numeric:
            return "identifier", {"reason": "almost every value is unique"}
        if _is_integer_valued(nonnull):
            sorted_vals = np.sort(nonnull.astype(float).values)
            consecutive = len(sorted_vals) > 1 and np.all(np.diff(sorted_vals) == 1)
            if name_looks_like_id or consecutive:
                return "identifier", {"reason": "unique integer values that look like an ID or row counter"}
    if name_looks_like_id and nn >= 10 and unique_ratio >= 0.9:
        return "identifier", {"reason": "column name and near-unique values suggest an identifier"}

    if numeric:
        return "numeric", {}
    if s.dtype == object:
        sample = nonnull.astype(str).head(500)
        if sample.str.match(_DATE_HINT_RE).mean() >= 0.9:
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
            if parsed.notna().mean() >= 0.9:
                return "datetime", {}
    return "categorical", {}


def _high_cardinality(col_type, nunique, nonnull):
    return col_type == "categorical" and (nunique > 50 or (nunique > 10 and nonnull and nunique / nonnull > 0.5))


def profile_dataset(df, meta):
    n = len(df)
    columns, issues = [], []
    for name in df.columns:
        s = df[name]
        col_type, extra = classify_column(name, s)
        missing = int(s.isna().sum())
        nonnull = n - missing
        nunique = int(s.nunique(dropna=True))
        flags = []
        if col_type == "constant":
            flags.append("constant")
        if col_type == "identifier":
            flags.append("id_like")
        if _high_cardinality(col_type, nunique, nonnull):
            flags.append("high_cardinality")
        if n and missing / n > 0.5:
            flags.append("mostly_missing")
        if LATER_TERM_RE.search(str(name)):
            flags.append("later_term")
        columns.append({
            "name": name,
            "type": col_type,
            "dtype": str(s.dtype),
            "missing": missing,
            "missing_pct": round_or_none(100 * missing / n if n else 0, 2),
            "unique": nunique,
            "unique_ratio": round_or_none(nunique / nonnull if nonnull else 0, 4),
            "flags": flags,
            "notes": extra.get("reason"),
            "examples": [display_value(v) for v in s.dropna().unique()[:3]],
        })

    def cols_with(flag):
        return [c["name"] for c in columns if flag in c["flags"]]

    if meta.get("blank_column_positions"):
        issues.append({"level": "warning", "code": "blank_column_names",
                       "message": "Some columns had blank names and were renamed to 'unnamed_<position>'.",
                       "columns": [f"unnamed_{p}" for p in meta["blank_column_positions"]]})
    if meta.get("duplicate_column_names"):
        issues.append({"level": "warning", "code": "duplicate_column_names",
                       "message": "Duplicate column names were found; repeats were renamed with a ' (n)' suffix.",
                       "columns": meta["duplicate_column_names"]})
    if cols_with("constant"):
        issues.append({"level": "warning", "code": "constant_columns",
                       "message": "These columns have a single value (or are empty) and will not be used as features.",
                       "columns": cols_with("constant")})
    if cols_with("id_like"):
        issues.append({"level": "info", "code": "id_like_columns",
                       "message": "These columns look like identifiers and are excluded from features by default.",
                       "columns": cols_with("id_like")})
    if cols_with("high_cardinality"):
        issues.append({"level": "warning", "code": "high_cardinality_columns",
                       "message": "These text columns have many distinct values; only the 50 most frequent categories are encoded.",
                       "columns": cols_with("high_cardinality")})
    if cols_with("mostly_missing"):
        issues.append({"level": "warning", "code": "mostly_missing_columns",
                       "message": "More than half of the values are missing in these columns.",
                       "columns": cols_with("mostly_missing")})
    if cols_with("later_term"):
        issues.append({"level": "warning", "code": "possible_later_term_columns",
                       "message": "Column names suggest possible later-term information (e.g. second semester or final results).",
                       "columns": cols_with("later_term")})
    if meta.get("decimal_comma_columns"):
        issues.append({"level": "info", "code": "decimal_comma",
                       "message": "Values with a decimal comma were converted to numbers.",
                       "columns": meta["decimal_comma_columns"]})
    for w in meta.get("parse_warnings", []):
        issues.append({"level": "warning", "code": "parse_warning", "message": w, "columns": []})

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        issues.append({"level": "warning", "code": "duplicate_rows",
                       "message": f"{duplicate_rows} row(s) are exact duplicates of an earlier row.", "columns": []})

    type_counts = {}
    for c in columns:
        type_counts[c["type"]] = type_counts.get(c["type"], 0) + 1
    missing_cells = int(df.isna().sum().sum())
    return {
        "columns": columns,
        "issues": issues,
        "type_counts": type_counts,
        "duplicate_rows": duplicate_rows,
        "missing_cells": missing_cells,
        "missing_cells_pct": round_or_none(100 * missing_cells / (n * len(df.columns)) if n else 0, 2),
        "columns_with_missing": sum(1 for c in columns if c["missing"]),
        "target_candidates": suggest_target_candidates(df.columns),
    }


def suggest_target_candidates(columns):
    """Exact case-insensitive name matches first, then names containing a hint."""
    exact, partial = [], []
    for c in columns:
        low = str(c).strip().lower()
        if low in TARGET_NAME_HINTS:
            exact.append(c)
        elif any(h in low for h in TARGET_NAME_HINTS):
            partial.append(c)
    return [{"name": c, "match": "exact"} for c in exact] + [{"name": c, "match": "partial"} for c in partial]


def column_profile(profile, name):
    for c in profile["columns"]:
        if c["name"] == name:
            return c
    return None


def normalize_target(series):
    """Target values as strings; integer-valued floats lose their '.0'."""
    s = series.copy()
    nonnull = s.dropna()
    if pd.api.types.is_numeric_dtype(s) and _is_integer_valued(nonnull):
        out = pd.Series(pd.NA, index=s.index, dtype=object)
        out[nonnull.index] = nonnull.astype(float).astype(np.int64).astype(str)
        return out.where(out.notna(), None)
    return s.map(lambda v: None if pd.isna(v) else str(v))


def suggest_at_risk_class(classes):
    for cls in classes:
        low = str(cls).lower()
        if any(h in low for h in AT_RISK_NAME_HINTS):
            return cls
    return None


def validate_target(df, profile, target):
    """Raise ApiError(422) on hard failures; return class info + warnings otherwise."""
    if not target or target not in df.columns:
        raise ApiError(422, "unknown_column", "The selected target column does not exist in this dataset.",
                       {"target": target})
    prof = column_profile(profile, target)
    n = len(df)
    y = normalize_target(df[target])
    missing = int(y.isna().sum())
    errors, warnings = [], []
    if missing / n > 0.5:
        errors.append({"code": "target_mostly_missing",
                       "message": f"{missing} of {n} target values are missing (more than half)."})
    if prof and prof["type"] == "identifier":
        errors.append({"code": "target_id_like",
                       "message": "This column looks like an identifier (almost every value is unique), not an outcome."})
    counts = y.dropna().value_counts()
    if len(counts) < 2:
        errors.append({"code": "single_class",
                       "message": "The target must contain at least two different classes."})
    elif len(counts) > 20:
        errors.append({"code": "too_many_classes",
                       "message": f"The target has {len(counts)} distinct values; a classification target should have at most 20."})
    rare = [str(k) for k, v in counts.items() if v < 2]
    if rare and len(counts) >= 2:
        errors.append({"code": "rare_class",
                       "message": "Every class needs at least 2 rows.", "classes": rare})
    few = [str(k) for k, v in counts.items() if 2 <= v < 5]
    if few:
        warnings.append({"code": "small_class",
                         "message": "Some classes have fewer than 5 rows; their metrics will be unreliable.",
                         "classes": few})
    if missing:
        warnings.append({"code": "target_missing",
                         "message": f"{missing} row(s) have no target value and will be excluded from training."})
    if errors:
        raise ApiError(422, errors[0]["code"], errors[0]["message"], {"errors": errors, "warnings": warnings})
    classes = sorted(counts.index.tolist(), key=str)
    return {
        "target": target,
        "classes": classes,
        "class_counts": {str(k): int(v) for k, v in counts.items()},
        "missing_target_rows": missing,
        "suggested_at_risk_class": suggest_at_risk_class(classes),
        "warnings": warnings,
    }


def build_feature_config(profile, target, id_column=None, excluded=None, include_id_like=None,
                         timing_preset="all"):
    """Decide which columns become model features, with a reason for every exclusion."""
    excluded = set(excluded or [])
    include_id_like = set(include_id_like or [])
    names = [c["name"] for c in profile["columns"]]
    for col in list(excluded) + list(include_id_like) + ([id_column] if id_column else []):
        if col not in names:
            raise ApiError(422, "unknown_column", f"Column '{col}' does not exist in this dataset.", {"column": col})
    if timing_preset not in ("all", "exclude_later"):
        raise ApiError(400, "invalid_timing_preset", "timing_preset must be 'all' or 'exclude_later'.")
    if id_column == target:
        raise ApiError(422, "id_is_target", "The identifier column cannot also be the target.")

    features, exclusions, warnings = [], [], []
    later_term_flagged = []
    for c in profile["columns"]:
        name = c["name"]
        if "later_term" in c["flags"] and name != target:
            later_term_flagged.append(name)
        reason = None
        if name == target:
            reason = "target"
        elif name == id_column:
            reason = "student_identifier"
        elif c["type"] == "constant":
            reason = "constant"
        elif c["type"] == "datetime":
            reason = "datetime_not_supported"
        elif c["type"] == "identifier" and name not in include_id_like:
            reason = "id_like"
        elif name in excluded:
            reason = "user_excluded"
        elif timing_preset == "exclude_later" and "later_term" in c["flags"]:
            reason = "later_term"
        if reason:
            exclusions.append({"column": name, "reason": reason})
        else:
            features.append(name)
            if c["type"] == "identifier":
                warnings.append({"code": "id_like_included",
                                 "message": f"'{name}' looks like an identifier. Including it can let the model memorise individual rows.",
                                 "column": name})

    demographic = [f for f in features if is_demographic(f)]
    if demographic:
        warnings.append({"code": "demographic_features",
                         "message": "Demographic attributes are used as model features. Review whether this is appropriate "
                                    "for your context; they are never used to trigger support suggestions.",
                         "columns": demographic})

    later_in_features = [c for c in later_term_flagged if c in features]
    # "Early prediction" is only claimed when flagged later-term columns exist and were all excluded.
    early = False
    if later_in_features:
        timing_label = "Uses all selected columns, including possible later-term information"
        warnings.append({"code": "later_term_included",
                         "message": "Some features may only be known later in the programme. Results do not represent early prediction.",
                         "columns": later_in_features})
    elif later_term_flagged:
        timing_label = "Excludes columns flagged as possible later-term information (name-based check)"
        early = True
    elif timing_preset == "exclude_later":
        timing_label = ("No columns were flagged as later-term by name; confirm manually that every "
                        "feature is available at prediction time")
    else:
        timing_label = "Uses all selected columns (no later-term columns detected by name)"

    if not features:
        raise ApiError(422, "no_features", "No usable feature columns remain after exclusions.",
                       {"exclusions": exclusions})
    types = {c["name"]: c["type"] for c in profile["columns"]}
    return {
        "features": features,
        "feature_types": {f: types[f] for f in features},
        "exclusions": exclusions,
        "warnings": warnings,
        "timing_preset": timing_preset,
        "timing_label": timing_label,
        "early_prediction": early,
        "later_term_columns": later_term_flagged,
    }
