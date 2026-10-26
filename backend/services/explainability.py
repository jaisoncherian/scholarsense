"""Global (permutation) and local (per-student) explanations.

Global importance permutes ORIGINAL input columns through the full pipeline on
the held-out test set. Local explanations are model-specific and labelled with
their method and limits.
"""
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import recall_score
from sklearn.model_selection import train_test_split

from errors import ApiError
from services.evaluation import MODEL_LABELS
from services.preprocessing import encoded_column_groups, prepare_X, to_dense
from services.serialization import display_value, round_or_none

GLOBAL_NOTE = ("Permutation importance measures how much the test-set score drops when one column's values are "
               "shuffled. It describes model behaviour, not causation, and is not the reason for any individual prediction.")
LR_METHOD = ("Logistic Regression contribution: coefficient × (this student's encoded value − the training-set average), "
             "summed over the encoded columns of each original feature. Values are on the log-odds scale of the predicted class.")
LR_LIMITS = ("Exact for this linear model, but it describes what the model computed, not why the outcome happens. "
             "Correlated features can share or swap credit.")
RF_METHOD = ("Random Forest perturbation approximation: each feature is replaced, one at a time, by its training median "
             "(numeric) or most common value (categorical), and the change in the predicted-class probability is reported.")
RF_LIMITS = ("An approximation: it ignores interactions between features, depends on the chosen reference value, and "
             "describes model behaviour, not causes.")
MISSING_NOTE = "Value missing in the uploaded file; no explanation is given for this feature."


def _scorer(scoring, at_risk):
    if scoring == "f1_macro":
        return "f1_macro", "Macro-F1"
    if scoring == "at_risk_recall":
        def at_risk_recall(estimator, X, y):
            return recall_score(y, estimator.predict(X), labels=[at_risk], average="macro", zero_division=0)
        return at_risk_recall, f"Recall for '{at_risk}'"
    raise ApiError(400, "invalid_scoring", "scoring must be 'f1_macro' or 'at_risk_recall'.")


def global_importance(training, model_key, scoring, cfg):
    if model_key not in training["pipelines"]:
        raise ApiError(422, "model_unavailable", f"Model '{model_key}' is not trained.")
    scorer, scoring_label = _scorer(scoring, training["at_risk_class"])
    X_te, y_te = training["X_test"], training["y_test"]
    sampled = False
    if len(X_te) > cfg.PERMUTATION_MAX_ROWS:
        sampled = True
        try:
            X_te, _, y_te, _ = train_test_split(X_te, y_te, train_size=cfg.PERMUTATION_MAX_ROWS,
                                                random_state=cfg.RANDOM_SEED, stratify=y_te)
        except ValueError:
            X_te, _, y_te, _ = train_test_split(X_te, y_te, train_size=cfg.PERMUTATION_MAX_ROWS,
                                                random_state=cfg.RANDOM_SEED)
    result = permutation_importance(training["pipelines"][model_key], X_te, y_te, scoring=scorer,
                                    n_repeats=cfg.PERMUTATION_REPEATS, random_state=cfg.RANDOM_SEED)
    features = [{"feature": col, "importance": round_or_none(result.importances_mean[i], 5),
                 "std": round_or_none(result.importances_std[i], 5)}
                for i, col in enumerate(X_te.columns)]
    features.sort(key=lambda f: -(f["importance"] or 0))
    return {
        "model": model_key, "model_label": MODEL_LABELS[model_key],
        "scoring": scoring, "scoring_label": scoring_label,
        "n_repeats": cfg.PERMUTATION_REPEATS, "random_state": cfg.RANDOM_SEED,
        "evaluated_on": "held-out test set", "rows_used": int(len(X_te)), "sampled": sampled,
        "features": features, "note": GLOBAL_NOTE,
    }


def _lr_contributions(pipe, x_row, training, k):
    pre, model = pipe.named_steps["preprocess"], pipe.named_steps["model"]
    z = to_dense(pre.transform(x_row))[0]
    coef = model.coef_
    if coef.shape[0] == 1:  # binary: one coefficient row for classes_[1]
        w = coef[0] if k == 1 else -coef[0]
    else:
        w = coef[k]
    centered = w * (z - training["lr_transformed_mean"])
    groups = encoded_column_groups(pre, training["schema"])
    return {col: float(centered[idx].sum()) for col, idx in groups.items()}


def _rf_contributions(pipe, x_row, training, k, base_prob):
    ref = training["reference_values"]
    rows, cols = [], []
    for col in x_row.columns:
        value, reference = x_row.iloc[0][col], ref.get(col)
        if pd.isna(value) or reference is None or value == reference:
            continue
        perturbed = x_row.copy()
        perturbed.iloc[0, perturbed.columns.get_loc(col)] = reference
        rows.append(perturbed)
        cols.append(col)
    out = {col: 0.0 for col in x_row.columns}
    if rows:
        probs = pipe.predict_proba(pd.concat(rows, ignore_index=True))[:, k]
        for col, p in zip(cols, probs):
            out[col] = float(base_prob - p)
    return out


def local_explanation(df, config, training, model_key, row_id, split_label):
    if model_key not in training["pipelines"]:
        raise ApiError(422, "model_unavailable", f"Model '{model_key}' is not trained.")
    pipe = training["pipelines"][model_key]
    x_row = prepare_X(df.loc[[row_id]], training["schema"])
    proba = pipe.predict_proba(x_row)[0]
    classes = [str(c) for c in pipe.classes_]
    k = int(np.argmax(proba))
    predicted = classes[k]

    if model_key == "logistic_regression":
        raw = _lr_contributions(pipe, x_row, training, k)
        method, limits, unit = LR_METHOD, LR_LIMITS, "log-odds"
    else:
        raw = _rf_contributions(pipe, x_row, training, k, proba[k])
        method, limits, unit = RF_METHOD, RF_LIMITS, "probability"

    ref = training["reference_values"]
    contributions = []
    for col in x_row.columns:
        value = x_row.iloc[0][col]
        missing = bool(pd.isna(value))
        contrib = None if missing else round_or_none(raw.get(col, 0.0), 5)
        if contrib is None:
            effect = "not_explained"
        elif abs(contrib) < 1e-9:
            effect = "none"
        else:
            effect = "toward" if contrib > 0 else "away"
        item = {"feature": col, "value": display_value(value), "value_missing": missing,
                "contribution": contrib, "effect": effect}
        if model_key == "random_forest":
            item["reference"] = display_value(ref.get(col))
        if missing:
            item["note"] = MISSING_NOTE
        contributions.append(item)
    contributions.sort(key=lambda c: -(abs(c["contribution"]) if c["contribution"] is not None else -1))

    return {
        "row_id": int(row_id),
        "model": model_key, "model_label": MODEL_LABELS[model_key],
        "predicted_class": predicted,
        "probabilities": {c: round_or_none(p) for c, p in zip(classes, proba)},
        "at_risk_class": training["at_risk_class"],
        "split": split_label,
        "in_sample": split_label == "train",
        "method": method, "limitations": limits, "unit": unit,
        "contributions": contributions,
        "summary": plain_language(contributions, predicted, model_key),
        "missing_features": [c["feature"] for c in contributions if c["value_missing"]],
    }


def plain_language(contributions, predicted, model_key):
    """Short staff-facing sentences built only from computed, non-missing contributions."""
    toward = [c for c in contributions if c["effect"] == "toward"][:3]
    away = [c for c in contributions if c["effect"] == "away"][:2]
    lines = []
    for c in toward:
        if model_key == "random_forest":
            lines.append(f"'{c['feature']}' = {c['value']}: replacing it with the typical value ({c['reference']}) "
                         f"would lower the model's estimate for '{predicted}' by {abs(c['contribution']):.3f}.")
        else:
            lines.append(f"'{c['feature']}' = {c['value']} moved the model toward predicting '{predicted}'.")
    for c in away:
        if model_key == "random_forest":
            lines.append(f"'{c['feature']}' = {c['value']}: replacing it with the typical value ({c['reference']}) "
                         f"would raise the model's estimate for '{predicted}' by {abs(c['contribution']):.3f}.")
        else:
            lines.append(f"'{c['feature']}' = {c['value']} moved the model away from predicting '{predicted}'.")
    if not lines:
        lines.append("No single feature changed this prediction noticeably under this method.")
    return lines
