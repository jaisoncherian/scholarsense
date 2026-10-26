"""Safe CSV ingestion: type/size checks, encoding + delimiter detection, parsing.

Uploaded content is only ever parsed as data by pandas; nothing is executed.
"""
import csv
import io
import logging
import os
import re
import time

import numpy as np
import pandas as pd

from errors import ApiError

log = logging.getLogger("scholarsense")

_ALLOWED_DELIMITERS = [",", ";", "\t"]
_BINARY_SIGNATURES = (b"PK\x03\x04", b"%PDF", b"\x89PNG", b"\xd0\xcf\x11\xe0", b"GIF8", b"\xff\xd8\xff")
_DECIMAL_COMMA_RE = re.compile(r"^-?\d+(,\d+)?$")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_filename(name):
    """Display-only filename: basename, no control characters, bounded length."""
    name = os.path.basename((name or "").replace("\\", "/"))
    name = _CONTROL_CHARS_RE.sub("", name).strip()
    if len(name) > 120:
        name = name[:117] + "..."
    return name or "dataset.csv"


def check_upload_type(filename, raw):
    if not filename or not filename.lower().endswith(".csv"):
        raise ApiError(415, "unsupported_file_type", "Only .csv files are accepted.",
                       {"filename": sanitize_filename(filename)})
    head = raw[:8192]
    if head.startswith(_BINARY_SIGNATURES) or b"\x00" in head:
        raise ApiError(415, "not_a_csv", "The file content does not look like CSV text (binary content detected).")


def decode_bytes(raw):
    """Return (text, encoding, warnings). Handles a UTF-8 BOM."""
    try:
        return raw.decode("utf-8-sig"), "utf-8", []
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1", [
            "The file is not valid UTF-8; it was decoded as Latin-1. Check that special characters display correctly."
        ]


def detect_delimiter(text):
    sample = text[:65536]
    lines = [ln for ln in sample.splitlines() if ln.strip()][:50]
    if not lines:
        return ","
    try:
        dialect = csv.Sniffer().sniff("\n".join(lines), delimiters="".join(_ALLOWED_DELIMITERS))
        if dialect.delimiter in _ALLOWED_DELIMITERS:
            return dialect.delimiter
    except csv.Error:
        pass
    # Fallback: the allowed delimiter appearing most often in the header line.
    header = lines[0]
    counts = {d: header.count(d) for d in _ALLOWED_DELIMITERS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def _clean_column_names(raw_names):
    """Strip names, rename blanks/duplicates; return (names, warnings, details)."""
    names, seen = [], {}
    blank_positions, duplicates = [], []
    for i, raw in enumerate(raw_names):
        name = str(raw).strip()
        if not name:
            blank_positions.append(i + 1)
            name = f"unnamed_{i + 1}"
        if name in seen:
            seen[name] += 1
            duplicates.append(name)
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        names.append(name)
    return names, blank_positions, sorted(set(duplicates))


def _coerce_decimal_comma(df):
    """Columns like '3,5' (common with ';' delimiters) become numeric."""
    converted = []
    for col in df.columns:
        s = df[col]
        if s.dtype != object:
            continue
        nonnull = s.dropna().astype(str).str.strip()
        if nonnull.empty or not nonnull.str.contains(",", regex=False).any():
            continue
        if nonnull.str.match(_DECIMAL_COMMA_RE).all():
            df[col] = pd.to_numeric(s.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")
            df.loc[s.isna(), col] = float("nan")
            converted.append(col)
    return converted


def parse_csv_file(path, max_rows, max_columns):
    """Parse the saved upload. Returns (df, meta)."""
    started = time.time()
    with open(path, "rb") as fh:
        raw = fh.read()
    if not raw.strip():
        raise ApiError(422, "empty_file", "The uploaded file is empty.")
    text, encoding, warnings = decode_bytes(raw)
    if not text.strip():
        raise ApiError(422, "empty_file", "The uploaded file is empty.")
    delimiter = detect_delimiter(text)

    try:
        header_row = next(csv.reader(io.StringIO(text), delimiter=delimiter))
    except (csv.Error, StopIteration) as exc:
        raise ApiError(422, "malformed_csv", "The header row could not be read.", {"reason": str(exc)[:200]})
    if len(header_row) > max_columns:
        raise ApiError(422, "too_many_columns",
                       f"The file has {len(header_row)} columns; the limit is {max_columns}.",
                       {"columns": len(header_row), "max_columns": max_columns})
    names, blank_positions, duplicates = _clean_column_names(header_row)

    try:
        df = pd.read_csv(
            io.StringIO(text), sep=delimiter, header=0, names=names, skipinitialspace=True,
            low_memory=False, on_bad_lines="error", nrows=max_rows + 1,
        )
    except pd.errors.EmptyDataError:
        raise ApiError(422, "empty_file", "The uploaded file has no readable content.")
    except (pd.errors.ParserError, csv.Error, ValueError) as exc:
        # pandas messages reference line/field counts, not cell contents.
        raise ApiError(422, "malformed_csv",
                       "The CSV could not be parsed. Check that every row has the same number of fields.",
                       {"reason": str(exc).strip()[:300]})

    if len(df) == 0:
        raise ApiError(422, "header_only", "The file contains a header row but no data rows.",
                       {"columns": names})
    if len(df) > max_rows:
        raise ApiError(422, "too_many_rows", f"The file has more than {max_rows:,} rows.",
                       {"max_rows": max_rows})

    # Normalise string cells: trim whitespace, blank -> missing.
    for col in df.columns:
        if df[col].dtype == object:
            s = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
            df[col] = s.mask(s == "", np.nan)
    decimal_comma_cols = _coerce_decimal_comma(df) if delimiter != "," else []
    # Fully-missing rows carry no information.
    empty_rows = int(df.isna().all(axis=1).sum())
    if empty_rows:
        df = df.loc[~df.isna().all(axis=1)]
        warnings.append(f"{empty_rows} completely empty row(s) were ignored.")
        if len(df) == 0:
            raise ApiError(422, "header_only", "The file contains a header row but no data rows.")
    df = df.reset_index(drop=True)

    meta = {
        "encoding": encoding,
        "delimiter": {",": "comma", ";": "semicolon", "\t": "tab"}[delimiter],
        "blank_column_positions": blank_positions,
        "duplicate_column_names": duplicates,
        "decimal_comma_columns": decimal_comma_cols,
        "parse_warnings": warnings,
        "parse_seconds": round(time.time() - started, 3),
    }
    return df, meta
