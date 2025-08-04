import re
import os
import pandas as pd
import numpy as np
import sys
import json
from PIL import Image, ImageTk
import shutil
from tkinter import messagebox
from packaging.version import Version

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

def get_local_config_dir():
    return os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "LICOR", "7800", "configs")


def get_config_path(model, version):
    return os.path.join(get_local_config_dir(), model, f"{version}.json")

def find_existing_versions(model):
    model_dir = os.path.join(get_local_config_dir(), model)
    if not os.path.exists(model_dir):
        return []
    return [f.removesuffix(".json") for f in os.listdir(model_dir) if f.endswith(".json")]

def load_variable_config(model_id, version_str=None, master=None):
    # Determine software version
    version = Version(version_str or "0.0.0")

    # Ensure target path exists
    local_dir = os.path.join(get_local_config_dir(), model_id)
    os.makedirs(local_dir, exist_ok=True)

    local_path = os.path.join(local_dir, f"{version}.json")

    if os.path.exists(local_path):
        print(f"Config File Found: {version}")
        with open(local_path, "r", encoding='utf-8') as f:
            return json.load(f)

    # Check for any previous versions
    existing_versions = find_existing_versions(model_id)
    existing_versions.sort(key=Version, reverse=True)

    if existing_versions:
        latest_version = existing_versions[0]
        if master:
            response = messagebox.askyesno(
                "New Software Version",
                f"No config found for software version {version}.\n"
                f"Would you like to copy from existing version {latest_version}?",
                parent=master
            )
        else:
            response = True  # fallback in non-GUI context

        if response:
            src = os.path.join(local_dir, f"{latest_version}.json")
            shutil.copy(src, local_path)
            with open(local_path, "r", encoding='utf-8') as f:
                return json.load(f)

    # Fall back to default in assets
    try:
        from file_parsing import resource_path  # safe circular import
    except:
        resource_path = lambda p: p  # fallback

    default_path = resource_path(os.path.join("assets", "defaults", f"{model_id}.json"))
    if os.path.exists(default_path):
        with open(default_path, "r", encoding='utf-8') as f: # Open the default json for the model
            default_config = json.load(f)
        with open(local_path, "w", encoding='utf-8') as f: # Save the default where the current model/version is
            json.dump(default_config, f, indent=2)
        return default_config

    # If all else fails, create an empty config
    with open(local_path, "w", encoding='utf-8') as f:
        json.dump({}, f, indent=2)
    return {}

def save_variable_config(model_id, version, config_dict):
    path = get_config_path(model_id, version)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding='utf-8') as f:
        json.dump(config_dict, f, indent=2)


#Plot Options Saving/Loading

def get_plot_options_path(model):
    base_dir = os.path.join(get_local_config_dir(), model)
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "plot_options.json")

def save_plot_options(model, options_dict):
    path = get_plot_options_path(model)
    try:
        with open(path, "w") as f:
            json.dump(options_dict, f, indent=4)
    except Exception as e:
        print(f"❌ Failed to save plot options: {e}")

def load_plot_options(model):
    path = get_plot_options_path(model)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load plot options: {e}")
    return {}


# Written by Elijah Schoneweis - 6/11/2025
