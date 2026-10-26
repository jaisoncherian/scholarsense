"""Column-aware exploratory analysis. Every value is computed from the uploaded DataFrame.

Charts that cannot be built return {"available": False, "reason": "..."}.
"""
import re

import numpy as np
import pandas as pd

from services.data_validation import normalize_target
from services.serialization import display_value, round_or_none

TOP_N_CATEGORIES = 10
MAX_HISTOGRAM_COLUMNS = 60
MAX_CATEGORICAL_COLUMNS = 40
MAX_CORRELATION_COLUMNS = 25
MAX_FEATURE_VS_TARGET = 6
MAX_ACADEMIC_COLUMNS = 8
ACADEMIC_RE = re.compile(
    r"grade|score|mark|attendance|attend|absen|units?\b|credit|approved|evaluat|gpa|exam", re.I
)


def unavailable(reason):
    return {"available": False, "reason": reason}


def _analysis_columns(df, profile, config):
    types = {c["name"]: c["type"] for c in profile["columns"]}
    skip = {config["target"], config.get("id_column")}
    numeric, categorical = [], []
    for col in df.columns:
        if col in skip or types[col] in ("identifier", "constant", "datetime"):
            continue
        if types[col] == "numeric":
            numeric.append(col)
        elif types[col] in ("categorical", "boolean"):
            categorical.append(col)
    return numeric, categorical


def _top_categories(s, top_n):
    """Values as strings, keeping the top_n most frequent and folding the rest into 'Other'."""
    vals = s.dropna().map(display_value)
    counts = vals.value_counts()
    keep = set(counts.index[:top_n])
    return vals.where(vals.isin(keep), "Other"), counts


def _eta_squared(x, y):
    mask = x.notna() & y.notna()
    x, y = x[mask].astype(float), y[mask]
    if len(x) < 3 or x.var() == 0:
        return None
    grand = x.mean()
    ss_total = ((x - grand) ** 2).sum()
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for _, g in x.groupby(y))
    return float(ss_between / ss_total) if ss_total else None


def _cramers_v(x, y):
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return None
    folded, _ = _top_categories(x[mask], 20)
    table = pd.crosstab(folded, y[mask]).values.astype(float)
    if table.shape[0] < 2 or table.shape[1] < 2:
        return None
    n = table.sum()
    expected = table.sum(axis=1, keepdims=True) * table.sum(axis=0, keepdims=True) / n
    chi2 = ((table - expected) ** 2 / np.where(expected == 0, 1, expected)).sum()
    k = min(table.shape) - 1
    return float(np.sqrt(chi2 / (n * k))) if k else None


def _histogram(s):
    vals = s.dropna().astype(float)
    if vals.empty:
        return unavailable("All values are missing.")
    uniq = np.unique(vals)
    if len(uniq) <= 30 and np.all(np.isclose(uniq % 1, 0)):
        counts = vals.value_counts().sort_index()
        return {"available": True, "kind": "discrete",
                "x": [display_value(v) for v in counts.index], "counts": counts.astype(int).tolist()}
    bins = int(min(30, max(5, np.ceil(np.log2(len(vals)) + 1))))
    counts, edges = np.histogram(vals, bins=bins)
    return {"available": True, "kind": "bins", "edges": [round_or_none(e, 6) for e in edges],
            "counts": counts.astype(int).tolist()}


def _box_stats(x, y, classes):
    out = []
    for cls in classes:
        vals = x[(y == cls) & x.notna()].astype(float)
        if vals.empty:
            out.append({"class": cls, "n": 0})
            continue
        q1, med, q3 = np.percentile(vals, [25, 50, 75])
        iqr = q3 - q1
        lo = vals[vals >= q1 - 1.5 * iqr].min()
        hi = vals[vals <= q3 + 1.5 * iqr].max()
        out.append({"class": cls, "n": int(len(vals)), "q1": round_or_none(q1, 6), "median": round_or_none(med, 6),
                    "q3": round_or_none(q3, 6), "lowerfence": round_or_none(lo, 6),
                    "upperfence": round_or_none(hi, 6), "mean": round_or_none(vals.mean(), 6)})
    return out


def _stacked(x, y, classes):
    mask = x.notna() & y.notna()
    folded, _ = _top_categories(x[mask], 8)
    table = pd.crosstab(folded, y[mask]).reindex(columns=classes, fill_value=0)
    totals = table.sum(axis=1)
    return {
        "categories": [str(c) for c in table.index],
        "series": [{"class": cls, "counts": table[cls].astype(int).tolist(),
                    "proportions": [round_or_none(v, 4) for v in (table[cls] / totals.replace(0, np.nan)).tolist()]}
                   for cls in classes],
    }


def compute_eda(df, profile, config):
    target = config["target"]
    y = normalize_target(df[target])
    n = len(df)
    classes = sorted(y.dropna().unique().tolist(), key=str)
    numeric, categorical = _analysis_columns(df, profile, config)
    feature_types = config["feature_types"]

    overview = {
        "rows": n,
        "columns": len(df.columns),
        "feature_count": len(config["features"]),
        "numeric_features": sum(1 for t in feature_types.values() if t == "numeric"),
        "categorical_features": sum(1 for t in feature_types.values() if t != "numeric"),
        "type_counts": profile["type_counts"],
        "target": target,
        "class_count": len(classes),
    }

    missing_cols = [{"column": c["name"], "missing": c["missing"], "pct": c["missing_pct"]}
                    for c in profile["columns"] if c["missing"]]
    missing_cols.sort(key=lambda r: -r["missing"])
    missing = {"total_cells": profile["missing_cells"], "pct_cells": profile["missing_cells_pct"],
               "columns": missing_cols}
    missing_chart = ({"available": True, "columns": missing_cols[:40]} if missing_cols
                     else unavailable("No missing values were found in this dataset."))

    dup = profile["duplicate_rows"]
    duplicates = {"count": dup, "pct": round_or_none(100 * dup / n if n else 0, 2)}

    numeric_stats = []
    for col in numeric:
        s = df[col].astype(float)
        nn = s.dropna()
        q = np.percentile(nn, [25, 50, 75]) if len(nn) else [None] * 3
        numeric_stats.append({
            "column": col, "count": int(len(nn)), "missing": int(s.isna().sum()),
            "mean": round_or_none(nn.mean()), "std": round_or_none(nn.std()), "min": round_or_none(nn.min()),
            "q1": round_or_none(q[0]), "median": round_or_none(q[1]), "q3": round_or_none(q[2]),
            "max": round_or_none(nn.max()),
        })

    categorical_counts = []
    for col in categorical[:MAX_CATEGORICAL_COLUMNS]:
        folded, counts = _top_categories(df[col], TOP_N_CATEGORIES)
        vc = folded.value_counts()
        ordered = [v for v in counts.index[:TOP_N_CATEGORIES]] + (["Other"] if "Other" in vc.index and len(counts) > TOP_N_CATEGORIES else [])
        total = int(vc.sum())
        categorical_counts.append({
            "column": col, "distinct": int(len(counts)), "missing": int(df[col].isna().sum()),
            "values": [{"value": v, "count": int(vc.get(v, 0)), "pct": round_or_none(100 * vc.get(v, 0) / total if total else 0, 2)}
                       for v in ordered],
        })

    tcounts = y.value_counts()
    labelled = int(tcounts.sum())
    target_distribution = {
        "available": True,
        "classes": [{"class": c, "count": int(tcounts.get(c, 0)),
                     "pct": round_or_none(100 * tcounts.get(c, 0) / labelled if labelled else 0, 2)} for c in classes],
        "missing": int(y.isna().sum()),
    }

    association = []
    for col in numeric:
        score = _eta_squared(df[col], y)
        if score is not None:
            association.append({"column": col, "type": "numeric", "score": round_or_none(score), "measure": "eta_squared"})
    for col in categorical:
        score = _cramers_v(df[col], y)
        if score is not None:
            association.append({"column": col, "type": "categorical", "score": round_or_none(score), "measure": "cramers_v"})
    association.sort(key=lambda r: -(r["score"] or 0))

    histograms = {col: _histogram(df[col]) for col in numeric[:MAX_HISTOGRAM_COLUMNS]}
    ranked_numeric = [a["column"] for a in association if a["type"] == "numeric" and a["column"] in histograms]
    default_histograms = (ranked_numeric + [c for c in histograms if c not in ranked_numeric])[:4]

    feature_vs_target = []
    for a in association[:MAX_FEATURE_VS_TARGET]:
        col = a["column"]
        if a["type"] == "numeric":
            feature_vs_target.append({"column": col, "kind": "box", "score": a["score"], "measure": a["measure"],
                                      "stats": _box_stats(df[col], y, classes)})
        else:
            feature_vs_target.append({"column": col, "kind": "stacked", "score": a["score"], "measure": a["measure"],
                                      **_stacked(df[col], y, classes)})
    fvt = ({"available": True, "charts": feature_vs_target} if feature_vs_target
           else unavailable("No feature had enough non-missing values to compare against the target."))

    corr_candidates = [c for c in numeric if df[c].nunique(dropna=True) > 2]
    if len(corr_candidates) < 2:
        correlation = unavailable(
            f"A correlation heatmap needs at least 2 numeric, non-binary, non-ID columns; this dataset has {len(corr_candidates)}.")
    else:
        rank = {a["column"]: i for i, a in enumerate(association)}
        chosen = sorted(corr_candidates, key=lambda c: rank.get(c, 1e9))[:MAX_CORRELATION_COLUMNS]
        mat = df[chosen].astype(float).corr()
        correlation = {"available": True, "columns": chosen,
                       "matrix": [[round_or_none(v, 3) for v in row] for row in mat.values],
                       "truncated": len(corr_candidates) > MAX_CORRELATION_COLUMNS,
                       "total_candidates": len(corr_candidates)}

    academic_cols = [c for c in numeric if ACADEMIC_RE.search(str(c))][:MAX_ACADEMIC_COLUMNS]
    if not academic_cols:
        academic = unavailable("No numeric columns with academic keywords (grade, score, marks, attendance, units, credits, approved, evaluated) were detected.")
    else:
        rows = []
        for col in academic_cols:
            means = df[col].astype(float).groupby(y).mean()
            rows.append({"column": col, "means": {c: round_or_none(means.get(c)) for c in classes}})
        academic = {"available": True, "classes": classes, "columns": rows,
                    "note": "Columns detected by name keywords; mean value per observed outcome class."}

    return {
        "overview": overview,
        "missing": missing,
        "missing_chart": missing_chart,
        "duplicates": duplicates,
        "numeric_stats": numeric_stats,
        "categorical_counts": categorical_counts,
        "target_distribution": target_distribution,
        "classes": classes,
        "histograms": histograms,
        "default_histograms": default_histograms,
        "association": association,
        "feature_vs_target": fvt,
        "correlation": correlation,
        "academic": academic,
    }
