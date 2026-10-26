"""Held-out evaluation and transparent model selection."""
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             precision_recall_fscore_support)

from services.serialization import round_or_none

MODEL_LABELS = {"logistic_regression": "Logistic Regression", "random_forest": "Random Forest"}
AVERAGING_NOTE = ("Macro = unweighted mean across classes; it weights every class equally and exposes "
                  "weak performance on small classes. Weighted = mean weighted by each class's support.")


def evaluate(pipeline, X_test, y_test, classes, at_risk_class, n_train):
    y_pred = pipeline.predict(X_test)
    prec, rec, f1, sup = precision_recall_fscore_support(y_test, y_pred, labels=classes, zero_division=0)
    macro = precision_recall_fscore_support(y_test, y_pred, labels=classes, average="macro", zero_division=0)
    weighted = precision_recall_fscore_support(y_test, y_pred, labels=classes, average="weighted", zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=classes)
    per_class = [{"class": c, "precision": round_or_none(prec[i]), "recall": round_or_none(rec[i]),
                  "f1": round_or_none(f1[i]), "support": int(sup[i])} for i, c in enumerate(classes)]
    k = classes.index(at_risk_class)
    flagged = int(cm[:, k].sum())
    false_alarms = flagged - int(cm[k, k])
    missed = int(cm[k, :].sum()) - int(cm[k, k])
    return {
        "accuracy": round_or_none(accuracy_score(y_test, y_pred)),
        "macro_precision": round_or_none(macro[0]),
        "macro_recall": round_or_none(macro[1]),
        "macro_f1": round_or_none(macro[2]),
        "weighted_f1": round_or_none(weighted[2]),
        "per_class": per_class,
        "classification_report": classification_report(y_test, y_pred, labels=classes, output_dict=True,
                                                        zero_division=0),
        "confusion_matrix": {"labels": classes, "matrix": cm.astype(int).tolist(),
                             "axes": "rows = observed class, columns = predicted class"},
        "at_risk": {
            "class": at_risk_class,
            "recall": round_or_none(rec[k]),
            "precision": round_or_none(prec[k]),
            "f1": round_or_none(f1[k]),
            "support": int(sup[k]),
            "flagged": flagged,
            "false_alarms": false_alarms,
            "missed": missed,
        },
        "n_train": int(n_train),
        "n_test": int(len(y_test)),
        "averaging": AVERAGING_NOTE,
    }


def selection_criteria_text(at_risk_class, tol):
    return (f"1) Highest recall for the at-risk class '{at_risk_class}' on the held-out test set. "
            f"2) If recalls are within {tol:.2f}, highest macro-F1 (also within {tol:.2f} counts as a tie). "
            "3) Then highest accuracy. 4) A complete tie goes to Logistic Regression (simpler and directly interpretable).")


def select_model(metrics, at_risk_class, tol=0.01):
    """metrics: {model_key: evaluate() output}. Returns the selection with its reasoning."""
    keys = [k for k in ("logistic_regression", "random_forest") if k in metrics]
    comparison = [{
        "model": k, "label": MODEL_LABELS[k],
        "at_risk_recall": metrics[k]["at_risk"]["recall"], "at_risk_precision": metrics[k]["at_risk"]["precision"],
        "macro_f1": metrics[k]["macro_f1"], "weighted_f1": metrics[k]["weighted_f1"], "accuracy": metrics[k]["accuracy"],
    } for k in keys]
    result = {"criteria": selection_criteria_text(at_risk_class, tol), "tolerance": tol,
              "comparison": comparison, "steps": []}
    if not keys:
        return {**result, "selected": None}
    if len(keys) == 1:
        result["steps"].append(f"Only {MODEL_LABELS[keys[0]]} trained successfully, so it is selected.")
        return {**result, "selected": keys[0]}

    a, b = keys
    ma, mb = metrics[a], metrics[b]
    for label, getter, tolerance in (
        (f"recall for '{at_risk_class}'", lambda m: m["at_risk"]["recall"] or 0.0, tol),
        ("macro-F1", lambda m: m["macro_f1"] or 0.0, tol),
        ("accuracy", lambda m: m["accuracy"] or 0.0, 1e-9),
    ):
        va, vb = getter(ma), getter(mb)
        if abs(va - vb) > tolerance:
            winner = a if va > vb else b
            result["steps"].append(
                f"{label}: {MODEL_LABELS[a]} {va:.3f} vs {MODEL_LABELS[b]} {vb:.3f} — {MODEL_LABELS[winner]} is higher.")
            return {**result, "selected": winner}
        result["steps"].append(
            f"{label}: {MODEL_LABELS[a]} {va:.3f} vs {MODEL_LABELS[b]} {vb:.3f} — tie (difference within tolerance).")
    result["steps"].append("All criteria tied; Logistic Regression is selected as the simpler model.")
    return {**result, "selected": "logistic_regression"}
