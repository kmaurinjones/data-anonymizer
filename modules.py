from itertools import combinations
import numpy as np
import pandas as pd

SUPPORTED_TYPES = [".csv", ".json", ".xlsx"]

def hello_world(): return "hello world!"

def load_file(file):
    """
    Takes a file given by Streamlit and loads into a DataFrame.
    Returns a DataFrame, metadata, and result string.

    @param file: File uploaded into streamlit.
    @rtype: tuple
    @return: A tuple of format (pd.DataFrame, (str, str), str).
    """
    df = None

    if file is None: return df, ("", ""), ""

    filename = file.name
    extension = filename.split(".")[-1] 
    metadata = (filename, extension)

    import_functions = {
        "csv": pd.read_csv,
        "json": pd.read_json,
        "xlsx": pd.read_excel
    }
    try:
        reader = import_functions.get(extension, None)
        if reader is None: 
            return df, metadata, f"Error: Invalid extension '{extension}'"
        df = reader(file)
        rows, columns = df.shape
        return df, metadata, f"File '{filename}' loaded successfully.\nFound {rows} rows, {columns} columns."
    except Exception as error:
        return df, metadata, f"Error: Unable to read file '{filename}' ({type(error)}: {error})"

def data_cleaner(df, drop_missing=False, remove_duplicates=True):
    """
    Takes a DataFrame and removes empty and duplicate entries.

    @type df: pd.DataFrame
    @param df: A DataFrame of uncleaned data.
    @type drop_missing: bool
    @param drop_missing: Determines if rows with any missing values are dropped ("any"), or just empty rows ("all").
    @type remove_duplicates: bool
    @param remove_duplicates: Determines if duplicate rows are removed.
    @rtype: pd.DataFrame
    @return: A DataFrame with requested cleaning applied
    """
    df = df.dropna(how="any" if drop_missing else "all")
    if remove_duplicates: df = df.drop_duplicates()
    return df

def column_combinations(df, k):
    return list(combinations(df.columns, k))

def k_redact(df, k):
    kwise_combinations = column_combinations(df, k) 
    
    for columns in kwise_combinations:
        df_search = df.loc[:, columns]
        sensitive_data = [
            (columns, key)
            for key, value
            in df_search.value_counts().to_dict().items()
            if value == 1
            ]
        if not sensitive_data: continue
        for columns, values in sensitive_data:
            for column, value in zip(columns, values):
                df_search = df_search.loc[df[column] == value]
                if df_search.shape[0] == 1:
                    for column in columns:
                        df_search[column] = None
    
    return df

def sensitive_values(series, sensitivity_minimum):
    return {key
        for key, value
        in series.value_counts().to_dict().items()
        if value < sensitivity_minimum
        }

def drop_sensitive(series, sensitivity_minimum):
    series.loc[series.isin(sensitive_values(series, sensitivity_minimum))] = None

def bin_numeric(df, to_process, bin_size, sensitivity_minimum):
    processed = set()
    rows, _ = df.shape
    num_bins = rows//bin_size
    for column_name in to_process:
        column = df[column_name]
        if column.dtype.kind not in "biufc": continue
        array = sorted(np.array(column))
        array_min, array_max = array[0], array[-1]
        splits = [array_min] + list(np.array_split(array, num_bins)) + [array_max]
        bins = [
            (np.min(split), np.max(split))
            for split
            in (splits[i] for i in range(num_bins))
            ]
        result = [None] * rows
        for bin_min, bin_max in bins:
            for i, value in enumerate(column):
                if bin_min <= value <= bin_max:
                    result[i] = (bin_min, bin_max)
        df[column_name] = result
        drop_sensitive(df[column_name], sensitivity_minimum)
        processed.add(column_name)
    return df, to_process - processed

def find_categorical(df, to_process, max_categorical_size, sensitivity_minimum):
    processed = set()
    for column_name in to_process:
        column = df[column_name]
        if column.nunique() <= max_categorical_size:
            drop_sensitive(column, sensitivity_minimum)
            processed.add(column_name)
    return df, to_process - processed

def redact(df, to_process, sensitivity_minimum):
    processed = set()
    for column_name in to_process:
        column = df[column_name]
        
        is_object = column.dtype == object
        if not is_object: continue

        # Check if any unique values exist, and redact them
        drop_sensitive(column, sensitivity_minimum)
        processed.add(column_name)

    return df, to_process - processed

def anonymize(df, max_categorical_size, bin_size, sensitivity_minimum):
    to_process = set(df.columns)
    df, to_process = redact(df, to_process, sensitivity_minimum)
    df, to_process = find_categorical(df, to_process, max_categorical_size, sensitivity_minimum)
    df, to_process = bin_numeric(df, to_process, bin_size, sensitivity_minimum)
    return df, to_process

def data_anonymizer(df, k, max_categorical_size, bin_size, sensitivity_minimum):
    start_dtypes = df.dtypes.to_dict()
    df, unprocessed = anonymize(df, max_categorical_size, bin_size, sensitivity_minimum)
    df = k_redact(df, k)
    end_dtypes = df.dtypes.to_dict()

    # Type correction
    for column in df.columns:
        start_type, end_type  = start_dtypes[column], end_dtypes[column]
        if start_type == end_type: continue
        if start_type.kind == "i" and end_type.kind == "f":
            df[column] = df[column].astype("Int64")

    return df, unprocessed
