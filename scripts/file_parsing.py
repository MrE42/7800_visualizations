import re
import os
import pandas as pd
import numpy as np
import sys
import json
from PIL import Image, ImageTk

def set_icon(r):
    ico = Image.open(resource_path('assets/icon.png'))
    photo = ImageTk.PhotoImage(ico)
    r.wm_iconphoto(True, photo)

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def parse_7800_data_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # --- Extract metadata from lines before DATAH ---
    metadata = {}
    for line in lines:
        if line.startswith("DATAH"):
            break

        line = line.strip()
        if not line:
            continue

        # Match simple "Key: Value" pairs
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip()

        # Handle serial number variations
        if line.startswith("S/N") or line.startswith("S#"):
            match = re.search(r'TG\d{2}-\d+', line)
            if match:
                metadata["SerialNumber"] = match.group(0)

    # Extract model from metadata or fallback to filename
    model_match = re.search(r'TG\d{2}', metadata.get("SerialNumber", ""))
    if not model_match:
        model_match = re.search(r'TG\d{2}', os.path.basename(filepath))
    model_number = model_match.group(0) if model_match else "Unknown"

    # --- Parse data block ---
    header_line_index = next(i for i, line in enumerate(lines) if line.startswith("DATAH"))
    units_line_index = next(i for i, line in enumerate(lines) if line.startswith("DATAU"))
    data_start_index = units_line_index + 1

    headers = lines[header_line_index].strip().split('\t')[1:]
    units = lines[units_line_index].strip().split('\t')[1:]
    expected_columns = len(headers)

    data = []
    for line in lines[data_start_index:]:
        parts = line.strip().split('\t')
        if len(parts) == expected_columns + 1:
            data.append(parts[1:])  # Skip prefix (e.g., "DATA")

    df = pd.DataFrame(data, columns=headers)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.columns = [f"{col} ({unit})" for col, unit in zip(headers, units)]

    print(metadata)

    return df, model_number, metadata

def load_and_merge_files(filepaths):
    merged_df = None
    model_number = None
    base_metadata = None

    for i, fp in enumerate(filepaths):
        df, model, meta = parse_7800_data_file(fp)

        serial = meta.get("SN") or meta.get("S/N") or meta.get("SerialNumber")
        if not serial:
            raise ValueError(f"Missing serial number in file: {fp}")

        if i == 0:
            base_serial = serial
            base_metadata = meta
            model_number = model
            merged_df = df
        else:
            if serial != base_serial:
                raise ValueError(f"Serial mismatch: {serial} ≠ {base_serial} in {fp}")
            merged_df = pd.concat([merged_df, df], ignore_index=True)

    return merged_df, model_number, base_metadata

def clean_error_codes(df):
    path = resource_path(os.path.join("assets", "error_codes.json"))
    try:
        with open(path, 'r') as f:
            error_codes = json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load error_codes.json: {e}")
        return df

    if not isinstance(error_codes, list):
        print("⚠️ error_codes.json must be a list of values.")
        return df

    for col in df.select_dtypes(include=["float", "int"]).columns:
        df[col] = df[col].apply(lambda x: np.nan if x in error_codes else x)

    return df


def load_variable_config(model, config_folder="assets"):
    """
    Safely loads a variable config JSON. If missing, empty, or invalid, creates a default file.
    Returns the loaded or created config dictionary.
    """

    filename = os.path.join(config_folder, f"{model}.json")
    filepath = resource_path(filename)

    def create_empty_config(path):
        empty_config = {}
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(empty_config, f, indent=2, ensure_ascii=True)
            print(f"✅ Created empty config at {path}")
        except Exception as e:
            print(f"❌ Failed to create default config: {e}")
        return empty_config

    try:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            print(f"⚠️ Config file {filepath} not found or empty.")
            return create_empty_config(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)
            if not isinstance(config, dict):
                print(f"⚠️ Config file {filepath} is not a valid dictionary.")
                return create_empty_config(filepath)
            return config

    except json.JSONDecodeError:
        print(f"⚠️ Config file {filepath} is corrupted or not valid JSON.")
        return create_empty_config(filepath)
    except Exception as e:
        print(f"❌ Unexpected error loading config: {e}")
        return create_empty_config(filepath)


# Written by Elijah Schoneweis - 6/11/2025