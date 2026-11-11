"""Assignment 1 - Data Loading: read CSV / Excel files safely."""
import pandas as pd

SUPPORTED_TYPES = (".csv", ".xlsx")


def load_file(file_obj, filename):
    """Return a raw DataFrame, or raise ValueError with a clear message."""
    name = filename.lower()
    if not name.endswith(SUPPORTED_TYPES):
        raise ValueError(
            f"Unsupported file type: '{filename}'. Please upload a .csv or .xlsx file."
        )
    try:
        if name.endswith(".csv"):
            try:
                df = pd.read_csv(file_obj)
            except UnicodeDecodeError:
                file_obj.seek(0)                      # try again with another encoding
                df = pd.read_csv(file_obj, encoding="latin-1")
        else:
            df = pd.read_excel(file_obj, engine="openpyxl")
    except Exception as error:
        raise ValueError(
            f"'{filename}' could not be read. The file may be corrupted or not a "
            f"real {name[-4:]} file. Details: {error}"
        )
    if df.empty:
        raise ValueError(f"'{filename}' contains no data rows.")
    return df


def file_overview(df):
    """First 10 rows, shape, column names and data types (Assignment 1)."""
    dtypes = df.dtypes.astype(str).reset_index()
    dtypes.columns = ["Column", "Data type"]
    return {
        "head": df.head(10),
        "rows": df.shape[0],
        "columns": df.shape[1],
        "dtypes": dtypes,
    }
