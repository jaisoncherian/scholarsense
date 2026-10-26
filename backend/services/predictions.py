"""Scoring rows and applying (uncalibrated) risk categories."""
import time

import numpy as np
import pandas as pd

from errors import ApiError
from services.data_validation import normalize_target
from services.preprocessing import prepare_X
from services.serialization import display_value, round_or_none

RISK_CATEGORIES = ["Low", "Medium", "High"]
RISK_NOTE = ("Risk score = the model's predicted probability for the selected at-risk class. "
             "It is a model-estimated risk, not a calibrated real-world probability.")
SPLIT_NOTES = {
    "test": "Held-out test rows: the model never saw these during training, so these predictions are unbiased estimates.",
    "train": "Training rows: the model was fitted on these rows, so their predictions are optimistic (in-sample).",
    "unlabeled": "Rows without a target value: not used for training or testing (out-of-sample).",
}


def validate_thresholds(low, high):
    try:
        low, high = float(low), float(high)
    except (TypeError, ValueError):
        raise ApiError(400, "invalid_thresholds", "Thresholds must be numbers.")
    if not 0 < low < high < 1:
        raise ApiError(422, "invalid_thresholds", "Thresholds must satisfy 0 < low < high < 1.",
                       {"low": low, "high": high})
    return {"low": low, "high": high}


def risk_category(score, low, high):
    if score is None or pd.isna(score):
        return None
    if score >= high:
        return "High"
    if score >= low:
        return "Medium"
    return "Low"


def row_identifiers(df, id_column, index):
    if id_column:
        return [display_value(v) or f"Row {i + 1}" for i, v in zip(index, df.loc[index, id_column])]
    return [f"Row {i + 1}" for i in index]


def split_labels(df, training):
    split = pd.Series("unlabeled", index=df.index, dtype=object)
    split.loc[training["train_index"]] = "train"
    split.loc[training["test_index"]] = "test"
    return split


def generate_predictions(df, config, training, model_key, scope):
    if model_key not in training["pipelines"]:
        raise ApiError(422, "model_unavailable", f"Model '{model_key}' is not trained.")
    if scope not in ("test", "all"):
        raise ApiError(400, "invalid_scope", "scope must be 'test' or 'all'.")
    pipe = training["pipelines"][model_key]
    index = pd.Index(training["test_index"]) if scope == "test" else df.index
    X = prepare_X(df.loc[index], training["schema"])
    proba = pipe.predict_proba(X)
    classes = [str(c) for c in pipe.classes_]
    predicted = np.asarray(classes, dtype=object)[proba.argmax(axis=1)]
    at_risk = training["at_risk_class"]
    split = split_labels(df, training).loc[index]
    observed = normalize_target(df.loc[index, config["target"]])

    frame = pd.DataFrame({
        "row_id": index.to_numpy().astype(int),
        "identifier": row_identifiers(df, config.get("id_column"), index),
        "split": split.to_numpy(),
        "predicted_class": predicted,
        "risk_score": proba[:, classes.index(at_risk)],
        "observed": observed.to_numpy(),
    })
    for i, cls in enumerate(classes):
        frame[f"prob::{cls}"] = proba[:, i]
    return {"model": model_key, "scope": scope, "classes": classes, "frame": frame, "generated_at": time.time()}


def with_categories(frame, thresholds):
    out = frame.copy()
    out["risk_category"] = [risk_category(s, thresholds["low"], thresholds["high"]) for s in out["risk_score"]]
    return out


def row_to_dict(row, classes):
    return {
        "row_id": int(row["row_id"]),
        "identifier": row["identifier"],
        "split": row["split"],
        "predicted_class": row["predicted_class"],
        "probabilities": {c: round_or_none(row[f"prob::{c}"]) for c in classes},
        "risk_score": round_or_none(row["risk_score"]),
        "risk_category": row["risk_category"],
        "observed": None if pd.isna(row["observed"]) else row["observed"],
    }


def counts(frame, column, keys):
    vc = frame[column].value_counts()
    return {k: int(vc.get(k, 0)) for k in keys}


def query_predictions(preds, thresholds, split="test", predicted_class=None, risk=None, q=None,
                      sort="risk_desc", page=1, page_size=25):
    frame = with_categories(preds["frame"], thresholds)
    split_counts = counts(frame, "split", ["test", "train", "unlabeled"])
    if split and split != "all":
        if split not in SPLIT_NOTES:
            raise ApiError(400, "invalid_split", "split must be test, train, unlabeled or all.")
        frame = frame[frame["split"] == split]
    summary = {
        "total": int(len(frame)),
        "by_predicted_class": counts(frame, "predicted_class", preds["classes"]),
        "by_risk_category": counts(frame, "risk_category", RISK_CATEGORIES),
        "mean_risk_score": round_or_none(frame["risk_score"].mean()) if len(frame) else None,
        "risk_histogram": {"edges": [round(e, 2) for e in np.linspace(0, 1, 21)],
                           "counts": np.histogram(frame["risk_score"], bins=20, range=(0, 1))[0].astype(int).tolist()},
    }
    if predicted_class:
        frame = frame[frame["predicted_class"] == predicted_class]
    if risk:
        if risk not in RISK_CATEGORIES:
            raise ApiError(400, "invalid_risk_category", "risk must be Low, Medium or High.")
        frame = frame[frame["risk_category"] == risk]
    if q:
        frame = frame[frame["identifier"].str.lower().str.contains(q.strip().lower(), regex=False, na=False)]
    if sort == "risk_asc":
        frame = frame.sort_values(["risk_score", "row_id"], ascending=[True, True])
    elif sort == "row":
        frame = frame.sort_values("row_id")
    else:
        frame = frame.sort_values(["risk_score", "row_id"], ascending=[False, True])
    total = int(len(frame))
    page_size = max(1, min(int(page_size), 200))
    pages = max(1, -(-total // page_size))
    page = max(1, min(int(page), pages))
    chunk = frame.iloc[(page - 1) * page_size: page * page_size]
    return {
        "rows": [row_to_dict(r, preds["classes"]) for _, r in chunk.iterrows()],
        "total": total, "page": page, "page_size": page_size, "pages": pages,
        "split_counts": split_counts,
        "summary": summary,
    }


def lookup_row(preds, thresholds, row_id):
    frame = preds["frame"]
    match = frame[frame["row_id"] == row_id]
    if match.empty:
        return None
    return row_to_dict(with_categories(match, thresholds).iloc[0], preds["classes"])
