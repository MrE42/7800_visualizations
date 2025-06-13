import re
import os
import pandas as pd


def parse_7800_data_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # Extract model number (TG##) from METADATA or filename
    metadata_line = lines[0].strip() if lines else ""
    model_match = re.search(r'TG\d{2}', metadata_line)
    if not model_match:
        model_match = re.search(r'TG\d{2}', os.path.basename(filepath))
    model_number = model_match.group(0) if model_match else "Unknown"

    # Find header and units lines
    header_line_index = next(i for i, line in enumerate(lines) if line.startswith("DATAH"))
    units_line_index = next(i for i, line in enumerate(lines) if line.startswith("DATAU"))
    data_start_index = units_line_index + 1

    headers = lines[header_line_index].strip().split('\t')[1:]
    units = lines[units_line_index].strip().split('\t')[1:]
    expected_columns = len(headers)

    # Parse valid data lines
    data = []
    for line in lines[data_start_index:]:
        parts = line.strip().split('\t')
        if len(parts) == expected_columns + 1:
            data.append(parts[1:])  # skip DATAR

    df = pd.DataFrame(data, columns=headers)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.columns = [f"{col} ({unit})" for col, unit in zip(headers, units)]
    return df, model_number


# Written by Elijah Schoneweis - 6/11/2025
#fig.suptitle(f"LI-78{model[2]}{model[3]} Data Visualization", fontsize=14)