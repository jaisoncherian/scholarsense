"""Train Logistic Regression and Random Forest on one shared, stratified split."""
import logging
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from errors import ApiError
from services.data_validation import normalize_target
from services.evaluation import MODEL_LABELS, evaluate, select_model
from services.preprocessing import build_preprocessor, build_schema, prepare_X

log = logging.getLogger("scholarsense")

_CLASS_WEIGHTS = {"balanced": "balanced", "none": None, None: None}


def parse_params(body, cfg):
    body = body or {}
    try:
        test_size = float(body.get("test_size", cfg.DEFAULT_TEST_SIZE))
    except (TypeError, ValueError):
        raise ApiError(400, "invalid_test_size", "test_size must be a number.")
    if not cfg.MIN_TEST_SIZE <= test_size <= cfg.MAX_TEST_SIZE:
        raise ApiError(400, "invalid_test_size",
                       f"test_size must be between {cfg.MIN_TEST_SIZE} and {cfg.MAX_TEST_SIZE}.")
    params = {"test_size": test_size}
    for key in ("lr_class_weight", "rf_class_weight"):
        value = body.get(key, "balanced")
        if value not in _CLASS_WEIGHTS:
            raise ApiError(400, "invalid_class_weight", f"{key} must be 'balanced' or 'none'.")
        params[key] = value or "none"
    n_est = body.get("rf_n_estimators")
    if n_est is not None:
        try:
            n_est = int(n_est)
        except (TypeError, ValueError):
            raise ApiError(400, "invalid_n_estimators", "rf_n_estimators must be an integer.")
        if not 10 <= n_est <= cfg.RF_MAX_ESTIMATORS:
            raise ApiError(400, "invalid_n_estimators",
                           f"rf_n_estimators must be between 10 and {cfg.RF_MAX_ESTIMATORS}.")
    params["rf_n_estimators"] = n_est
    return params


def prepare_training_data(df, config, cfg):
    """Drop rows without a target and run the hard pre-training checks."""
    y_all = normalize_target(df[config["target"]])
    labelled = y_all.notna()
    dropped = int((~labelled).sum())
    y = y_all[labelled].astype(str)
    if not config["features"]:
        raise ApiError(422, "no_features", "No usable feature columns are configured.")
    if len(y) < cfg.MIN_TRAIN_ROWS:
        raise ApiError(422, "too_few_rows",
                       f"At least {cfg.MIN_TRAIN_ROWS} rows with a target value are needed to train; found {len(y)}.",
                       {"rows": int(len(y)), "minimum": cfg.MIN_TRAIN_ROWS, "dropped_missing_target": dropped})
    counts = y.value_counts()
    if len(counts) < 2:
        raise ApiError(422, "too_few_classes", "Fewer than 2 target classes remain after removing missing targets.",
                       {"class_counts": counts.to_dict()})
    rare = counts[counts < cfg.MIN_CLASS_ROWS]
    if len(rare):
        raise ApiError(422, "rare_class",
                       f"Every class needs at least {cfg.MIN_CLASS_ROWS} rows to be split into train and test sets.",
                       {"classes": rare.index.tolist(), "class_counts": counts.to_dict()})
    schema = build_schema(df, config, cfg.OHE_MAX_CATEGORIES)
    X = prepare_X(df.loc[labelled], schema)
    return X, y, schema, dropped


def make_split(X, y, test_size, seed):
    """One stratified split shared by both models; non-stratified fallback with a warning."""
    warnings = []
    try:
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)
        stratified = True
    except ValueError as exc:
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=test_size, random_state=seed)
        stratified = False
        warnings.append(f"A stratified split was not possible ({exc}); a random split was used instead, "
                        "so class proportions may differ between train and test sets.")
    if y_tr.nunique() < 2:
        raise ApiError(422, "too_few_classes", "The training split contains fewer than 2 classes.")
    missing_in_test = sorted(set(y.unique()) - set(y_te.unique()))
    if missing_in_test:
        warnings.append(f"These classes have no rows in the test set, so their metrics are not available: {missing_in_test}.")
    return X_tr, X_te, y_tr, y_te, stratified, warnings


def build_pipelines(schema, params, n_rows, cfg):
    n_est = params["rf_n_estimators"] or (
        cfg.RF_LARGE_DATA_ESTIMATORS if n_rows > cfg.RF_LARGE_DATA_ROWS else cfg.RF_DEFAULT_ESTIMATORS)
    n_est = min(n_est, cfg.RF_MAX_ESTIMATORS)
    lr = Pipeline([
        ("preprocess", build_preprocessor(schema, scale_numeric=True)),
        ("model", LogisticRegression(max_iter=cfg.LR_MAX_ITER, class_weight=_CLASS_WEIGHTS[params["lr_class_weight"]],
                                     random_state=cfg.RANDOM_SEED)),
    ])
    rf = Pipeline([
        ("preprocess", build_preprocessor(schema, scale_numeric=False)),
        ("model", RandomForestClassifier(n_estimators=n_est, class_weight=_CLASS_WEIGHTS[params["rf_class_weight"]],
                                         random_state=cfg.RANDOM_SEED, n_jobs=cfg.RF_N_JOBS)),
    ])
    return {"logistic_regression": lr, "random_forest": rf}, n_est


def reference_values(X_train, schema):
    """Training medians / modes used as the 'typical value' for RF perturbation explanations."""
    ref = {}
    for col in schema["numeric"]:
        med = X_train[col].median()
        ref[col] = None if pd.isna(med) else float(med)
    for col in schema["categorical"]:
        mode = X_train[col].dropna().mode()
        ref[col] = None if mode.empty else mode.iloc[0]
    return ref


def train_models(df, config, params, cfg):
    started = time.time()
    X, y, schema, dropped = prepare_training_data(df, config, cfg)
    X_tr, X_te, y_tr, y_te, stratified, warnings = make_split(X, y, params["test_size"], cfg.RANDOM_SEED)
    classes = sorted(y.unique().tolist(), key=str)
    at_risk = config["at_risk_class"]
    if at_risk not in classes:
        raise ApiError(422, "at_risk_class_missing", f"The at-risk class '{at_risk}' has no labelled rows.")
    pipelines, n_est = build_pipelines(schema, params, len(X_tr), cfg)

    fitted, metrics, failures, timings = {}, {}, {}, {}
    for key, pipe in pipelines.items():
        t0 = time.time()
        try:
            pipe.fit(X_tr, y_tr)  # training split only
            metrics[key] = evaluate(pipe, X_te, y_te, classes, at_risk, len(X_tr))
            fitted[key] = pipe
        except Exception as exc:  # one model failing must not hide the other
            log.warning("model %s failed: %s", key, type(exc).__name__)
            failures[key] = f"{MODEL_LABELS[key]} failed to train: {str(exc)[:300]}"
        timings[key] = round(time.time() - t0, 3)
    if not fitted:
        raise ApiError(422, "training_failed", "Neither model could be trained.", {"failures": failures})

    lr_mean = None
    if "logistic_regression" in fitted:
        Z = fitted["logistic_regression"].named_steps["preprocess"].transform(X_tr)
        lr_mean = np.asarray(Z.mean(axis=0)).ravel()  # works for sparse and dense output

    selection = select_model(metrics, at_risk, cfg.SELECTION_TOLERANCE)
    log.info("trained models=%s rows=%d features=%d seconds=%.2f",
             list(fitted), len(X), len(config["features"]), time.time() - started)
    return {
        "pipelines": fitted,
        "schema": schema,
        "X_train": X_tr, "X_test": X_te, "y_train": y_tr, "y_test": y_te,
        "train_index": X_tr.index.to_numpy(), "test_index": X_te.index.to_numpy(),
        "classes": classes,
        "at_risk_class": at_risk,
        "metrics": metrics,
        "failures": failures,
        "selection": selection,
        "reference_values": reference_values(X_tr, schema),
        "lr_transformed_mean": lr_mean,
        "params": {**params, "rf_n_estimators_used": n_est, "random_state": cfg.RANDOM_SEED},
        "stratified": stratified,
        "warnings": warnings,
        "dropped_missing_target": dropped,
        "labelled_rows": int(len(y)),
        "class_counts_train": {str(k): int(v) for k, v in y_tr.value_counts().items()},
        "class_counts_test": {str(k): int(v) for k, v in y_te.value_counts().items()},
        "features": list(config["features"]),
        "timing_label": config["timing_label"],
        "early_prediction": config["early_prediction"],
        "timings": timings,
        "trained_at": time.time(),
    }


def training_summary(training):
    """JSON-safe view of a training result (no fitted objects or frames)."""
    return {
        "models": {k: {"label": MODEL_LABELS[k], **m} for k, m in training["metrics"].items()},
        "failures": training["failures"],
        "selection": training["selection"],
        "classes": training["classes"],
        "at_risk_class": training["at_risk_class"],
        "params": training["params"],
        "stratified": training["stratified"],
        "warnings": training["warnings"],
        "dropped_missing_target": training["dropped_missing_target"],
        "labelled_rows": training["labelled_rows"],
        "n_train": int(len(training["train_index"])),
        "n_test": int(len(training["test_index"])),
        "class_counts_train": training["class_counts_train"],
        "class_counts_test": training["class_counts_test"],
        "features": training["features"],
        "feature_schema": {"numeric": training["schema"]["numeric"], "categorical": training["schema"]["categorical"]},
        "timing_label": training["timing_label"],
        "early_prediction": training["early_prediction"],
        "timings": training["timings"],
        "trained_at": training["trained_at"],
    }
