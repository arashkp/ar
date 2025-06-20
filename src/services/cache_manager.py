import pandas as pd
import os
from typing import List, Optional

# Define the column names for the cache file
CACHE_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

def ensure_cache_directory_exists(cache_dir: str):
    """Ensures that the cache directory exists."""
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        print(f"Cache directory created: {cache_dir}") # For now, simple print, consider logging

def get_cache_filepath(cache_dir: str, symbol: str) -> str:
    """Generates the filepath for a symbol's cache CSV file."""
    # Sanitize symbol name for filename (e.g., replace '/' with '_')
    safe_symbol_filename = symbol.replace('/', '_') + ".csv"
    return os.path.join(cache_dir, safe_symbol_filename)

def read_ohlcv_from_cache(cache_dir: str, symbol: str) -> Optional[pd.DataFrame]:
    """
    Reads OHLCV data from a CSV cache file for a given symbol.
    Returns a DataFrame if the cache file exists and is valid, otherwise None.
    The DataFrame will be sorted by timestamp in ascending order.
    """
    ensure_cache_directory_exists(cache_dir)
    filepath = get_cache_filepath(cache_dir, symbol)

    if not os.path.exists(filepath):
        # print(f"Cache file not found for {symbol} at {filepath}") # Debug
        return None
    try:
        # Read, ensuring timestamp is parsed as int64 to match ccxt
        df = pd.read_csv(filepath, header=0, names=CACHE_COLUMNS,
                         dtype={'timestamp': 'int64', 'open': 'float64', 'high': 'float64',
                                'low': 'float64', 'close': 'float64', 'volume': 'float64'})

        if df.empty:
            # print(f"Cache file for {symbol} is empty.") # Debug
            return None

        # Ensure correct columns and sort by timestamp
        if not all(col in df.columns for col in CACHE_COLUMNS):
            # print(f"Cache file for {symbol} has incorrect columns.") # Debug
            # Potentially delete or rename the corrupted file
            os.remove(filepath) # Basic error handling: remove corrupt file
            return None

        df.sort_values(by='timestamp', ascending=True, inplace=True)
        df.reset_index(drop=True, inplace=True)
        # print(f"Successfully read cache for {symbol}: {len(df)} records.") # Debug
        return df
    except pd.errors.EmptyDataError:
        # print(f"Cache file for {symbol} is empty or corrupted (EmptyDataError).") # Debug
        os.remove(filepath) # Remove empty/corrupt file
        return None
    except Exception as e:
        # print(f"Error reading cache file for {symbol} at {filepath}: {e}") # Debug
        # Potentially delete or rename the corrupted file for safety
        # For now, just return None, signaling no usable cache
        # Consider more robust error handling, like moving the corrupted file
        if os.path.exists(filepath):
             os.remove(filepath) # Basic error handling: remove corrupt file
        return None

def write_ohlcv_to_cache(cache_dir: str, symbol: str, data: pd.DataFrame):
    """
    Writes OHLCV data (DataFrame) to a CSV cache file for a given symbol.
    The DataFrame should contain columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
    The data is written by overwriting the existing file.
    """
    ensure_cache_directory_exists(cache_dir)
    filepath = get_cache_filepath(cache_dir, symbol)

    if not all(col in data.columns for col in CACHE_COLUMNS):
        raise ValueError(f"DataFrame to be cached for {symbol} is missing required columns. Expected: {CACHE_COLUMNS}")

    try:
        # Ensure data is sorted by timestamp before writing
        data_sorted = data.sort_values(by='timestamp', ascending=True)
        data_sorted.to_csv(filepath, index=False, header=True) # Write header
        # print(f"Successfully wrote {len(data_sorted)} records to cache for {symbol} at {filepath}") # Debug
    except Exception as e:
        # print(f"Error writing cache file for {symbol} at {filepath}: {e}") # Debug
        # Handle potential errors, e.g., disk full, permissions
        raise # Re-raise the exception for now
