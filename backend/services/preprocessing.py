"""Feature schema + sklearn preprocessing that lives inside each fitted Pipeline."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from services.serialization import display_value


def build_schema(df, config, max_categories=50):
    """Split confirmed features into numeric and categorical inputs."""
    numeric, categorical = [], []
    for col in config["features"]:
        ftype = config["feature_types"][col]
        is_num = pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col])
        if ftype == "numeric" or (ftype in ("boolean", "identifier") and is_num):
            numeric.append(col)
        else:
            categorical.append(col)
    return {"numeric": numeric, "categorical": categorical, "max_categories": max_categories}


def prepare_X(df, schema):
    """Raw input frame with consistent dtypes; used for training, scoring and perturbation."""
    X = pd.DataFrame(index=df.index)
    for col in schema["numeric"]:
        X[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    for col in schema["categorical"]:
        X[col] = df[col].map(lambda v: np.nan if display_value(v) is None else display_value(v)).astype(object)
    return X[schema["numeric"] + schema["categorical"]]


def build_preprocessor(schema, scale_numeric):
    """Median-impute (+scale) numeric; constant-impute + one-hot each categorical column.

    One transformer per categorical column keeps a clean mapping from encoded
    columns back to the original column (used by local explanations).
    """
    transformers = []
    if schema["numeric"]:
        steps = [("imputer", SimpleImputer(strategy="median", keep_empty_features=True))]
        if scale_numeric:
            steps.append(("scaler", StandardScaler()))
        transformers.append(("num", Pipeline(steps), list(schema["numeric"])))
    for i, col in enumerate(schema["categorical"]):
        transformers.append((f"cat{i}", Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="missing", keep_empty_features=True)),
            ("onehot", OneHotEncoder(handle_unknown="ignore", max_categories=schema["max_categories"])),
        ]), [col]))
    return ColumnTransformer(transformers, remainder="drop")


def encoded_column_groups(preprocessor, schema):
    """Map each original column to the indices of its encoded output columns."""
    groups = {}
    for name, sl in preprocessor.output_indices_.items():
        if name == "num":
            for offset, col in enumerate(schema["numeric"]):
                groups[col] = [sl.start + offset]
        elif name.startswith("cat"):
            col = schema["categorical"][int(name[3:])]
            groups[col] = list(range(sl.start, sl.stop))
    return groups


def to_dense(matrix):
    return matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix)
