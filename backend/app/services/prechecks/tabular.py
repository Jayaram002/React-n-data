import io
import re
import json
import hashlib
from typing import Dict, Any, List, Tuple
import pandas as pd

# PII Regex Patterns
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
CREDIT_CARD_REGEX = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')

PII_COLUMN_NAME_KEYWORDS = [
    "email", "phone", "mobile", "ssn", "social_security", 
    "credit_card", "card_number", "password", "aadhaar", "passport"
]

def detect_pii_in_text(text: str) -> List[str]:
    findings = []
    if EMAIL_REGEX.search(text):
        findings.append("email")
    if PHONE_REGEX.search(text):
        findings.append("phone_number")
    if SSN_REGEX.search(text):
        findings.append("government_id")
    if CREDIT_CARD_REGEX.search(text):
        findings.append("credit_card")
    return findings

def mask_pii_value(val: Any) -> Any:
    if not isinstance(val, str):
        return val
    s = val
    s = EMAIL_REGEX.sub("[MASKED_EMAIL]", s)
    s = PHONE_REGEX.sub("[MASKED_PHONE]", s)
    s = SSN_REGEX.sub("[MASKED_ID]", s)
    s = CREDIT_CARD_REGEX.sub("[MASKED_CARD]", s)
    return s

def scan_dataframe_pii(df: pd.DataFrame, sample_rows: int = 50) -> Dict[str, Any]:
    flagged_columns = []
    pii_types_found = set()

    for col in df.columns:
        col_str = str(col).lower()
        has_pii = False
        
        # Check column name
        for keyword in PII_COLUMN_NAME_KEYWORDS:
            if keyword in col_str:
                flagged_columns.append({"column": str(col), "reason": f"Column name contains keyword '{keyword}'"})
                pii_types_found.add("pii_column_name")
                has_pii = True
                break

        if not has_pii:
            # Check sample values
            sample_vals = df[col].dropna().head(sample_rows).astype(str).tolist()
            for val in sample_vals:
                findings = detect_pii_in_text(val)
                if findings:
                    flagged_columns.append({"column": str(col), "reason": f"Detected {', '.join(findings)} in values"})
                    for f in findings:
                        pii_types_found.add(f)
                    break

    return {
        "pii_detected": len(flagged_columns) > 0,
        "flagged_columns": flagged_columns,
        "pii_types": list(pii_types_found)
    }

def infer_column_types(df: pd.DataFrame) -> Dict[str, str]:
    types = {}
    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_integer_dtype(dtype):
            types[str(col)] = "integer"
        elif pd.api.types.is_float_dtype(dtype):
            types[str(col)] = "float"
        elif pd.api.types.is_bool_dtype(dtype):
            types[str(col)] = "boolean"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            types[str(col)] = "datetime"
        else:
            types[str(col)] = "string"
    return types

def process_tabular(file_bytes: bytes, filename: str, max_size_bytes: int = 50 * 1024 * 1024, max_rows: int = 100000) -> Dict[str, Any]:
    """
    Parses and checks tabular files (CSV, JSON, XLSX).
    Computes row/col count, column schema, null ratios, content & signature hashes, PII scan, and safe masked preview.
    """
    if len(file_bytes) > max_size_bytes:
        raise ValueError(f"Tabular file exceeds maximum size of {max_size_bytes // (1024 * 1024)}MB")

    lower_name = filename.lower()
    df: pd.DataFrame = None
    mime_type: str = "text/csv"

    try:
        if lower_name.endswith(".csv"):
            mime_type = "text/csv"
            # Try utf-8 first, fallback to latin-1
            try:
                # auto-detect delimiter with sep=None
                df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine="python", nrows=max_rows)
            except Exception:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1", nrows=max_rows)

        elif lower_name.endswith(".json"):
            mime_type = "application/json"
            data = json.loads(file_bytes.decode("utf-8", errors="ignore"))
            if isinstance(data, list):
                df = pd.DataFrame(data[:max_rows])
            elif isinstance(data, dict):
                # Try table format or single record
                df = pd.DataFrame([data])
            else:
                raise ValueError("JSON file must contain an array of records or a JSON object")

        elif lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            # Parse safely with openpyxl (does not evaluate macros/formulas)
            df = pd.read_excel(io.BytesIO(file_bytes), nrows=max_rows, engine="openpyxl")
        else:
            raise ValueError(f"Unsupported tabular file format. Allowed: .csv, .json, .xlsx")

    except Exception as e:
        raise ValueError(f"Unable to parse tabular file safely: {str(e)}")

    if df is None or df.empty:
        raise ValueError("Dataset is empty or contains no records")

    row_count = len(df)
    col_count = len(df.columns)
    column_names = [str(c) for c in df.columns]

    # Inferred schema & null ratios
    col_types = infer_column_types(df)
    null_ratios = {str(col): float(df[col].isnull().mean()) for col in df.columns}
    
    # Duplicate row ratio
    duplicate_rows = int(df.duplicated().sum())
    duplicate_row_ratio = float(duplicate_rows / row_count) if row_count > 0 else 0.0

    column_schema = {
        "columns": [
            {
                "name": str(col),
                "type": col_types[str(col)],
                "null_ratio": round(null_ratios[str(col)], 4)
            }
            for col in df.columns
        ],
        "row_count": row_count,
        "column_count": col_count,
        "duplicate_row_ratio": round(duplicate_row_ratio, 4)
    }

    # Hashes: content_hash (SHA256 of raw bytes), signature_hash (sorted column names hash)
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    sorted_cols = sorted([str(c).strip().lower() for c in df.columns])
    signature_hash = hashlib.sha256(",".join(sorted_cols).encode("utf-8")).hexdigest()

    # PII Scan
    pii_results = scan_dataframe_pii(df)

    # Safe Preview: First 5 rows with PII values masked
    preview_df = df.head(5).copy()
    for col in preview_df.columns:
        preview_df[col] = preview_df[col].apply(mask_pii_value)
    
    # Fill NaN with None for valid JSON serialization
    preview_records = preview_df.where(pd.notnull(preview_df), None).to_dict(orient="records")

    preview_data = {
        "columns": column_schema["columns"],
        "row_count": row_count,
        "column_count": col_count,
        "sample_rows": preview_records,
        "pii_info": pii_results
    }
    preview_bytes = json.dumps(preview_data).encode("utf-8")

    return {
        "mime": mime_type,
        "size": len(file_bytes),
        "row_count": row_count,
        "column_schema": column_schema,
        "content_hash": content_hash,
        "signature_hash": signature_hash,
        "pii_results": pii_results,
        "preview_bytes": preview_bytes,
        "preview_mime": "application/json"
    }
