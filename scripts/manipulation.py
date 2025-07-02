import numpy as np
import pandas as pd

def insert_nan_gaps(x, y, threshold):
    """Insert NaN between time gaps greater than `threshold`."""
    x = np.asarray(x)
    y = np.asarray(y)

    if len(x) < 2:
        return x, y

    dx = np.diff(x)
    gap_indices = np.where(dx > threshold)[0]

    x_new = []
    y_new = []

    for i in range(len(x)):
        x_new.append(x[i])
        y_new.append(y[i])
        if i in gap_indices:
            x_new.append(np.nan)
            y_new.append(np.nan)

    return np.array(x_new), np.array(y_new)


def identify_operational_spans(df, threshold= 2, time_col='SECONDS (secs)', cavity_col='CAVITY_T (°C)', enclosure_col='THERMAL_ENCLOSURE_T (°C)', index_col='NDX (index)', warmup_thresholds=(55, 54), max_gap=10):
    """
    Identify startup and running spans based on NDX activity and component temperature thresholds.

    Returns:
        List of (startup_start, startup_end, running_start, running_end) tuples.
    """
    from datetime import datetime
    import pytz

    if time_col not in df or index_col not in df:
        print("❌ Required columns missing.")
        return []

    df = df.sort_values(time_col).reset_index(drop=True)

    # Identify all rows where NDX is present (device active)
    active = df[index_col].notna()
    active_times = df[time_col][active]

    if active_times.empty:
        print("⚠️ No active NDX entries.")
        return []

    # Group into blocks based on time gap > max_gap
    blocks = []
    current_block = [active_times.iloc[0]]
    for prev, curr in zip(active_times, active_times.iloc[1:]):
        if curr - prev > max_gap:
            blocks.append(current_block)
            current_block = []
        current_block.append(curr)
    if current_block:
        blocks.append(current_block)

    spans = []
    tz = pytz.timezone(df.attrs.get("timezone", "UTC")) if hasattr(df, "attrs") else pytz.UTC

    for i, block in enumerate(blocks):
        t_start = block[0]
        t_end = block[-1]
        if t_end - t_start < threshold:
            continue

        block_df = df[(df[time_col] >= t_start) & (df[time_col] <= t_end)]

        warmed_up = (block_df[cavity_col] >= warmup_thresholds[0]) & (block_df[enclosure_col] >= warmup_thresholds[1])
        if not warmed_up.any():
            print(f"⛔ Block {i}: No stable temperature — skipping")
            continue

        startup_end_time = block_df[warmed_up].iloc[0][time_col]
        startup_span = (t_start, startup_end_time)
        running_span = (startup_end_time + 1, t_end)

        spans.append((startup_span, running_span))

        def fmt(ts): return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M:%S")

        print(f"🟦 Startup span: {fmt(startup_span[0])} to {fmt(startup_span[1])}")
        print(f"🟩 Running span: {fmt(running_span[0])} to {fmt(running_span[1])}")

    print(f"✅ Done: {len(spans)*2} spans identified")
    return spans

def update_spec_checks(ax, df, variable_config, running_spans, results = {}, threshold = 2, time_col='SECONDS (secs)'):
    if time_col not in df:
        print("⚠️ DataFrame missing required time column for spec checks.")
        return results

    xlim = ax.get_xlim()
    visible_mask = (df[time_col] >= xlim[0]) & (df[time_col] <= xlim[1])

    # Combine all running span filters
    running_mask = pd.Series(False, index=df.index)
    for start, end in running_spans:
        if (end - start) > threshold:
            running_mask |= (df[time_col] >= start) & (df[time_col] <= end - threshold)

    combined_mask = visible_mask & running_mask
    subset = df[combined_mask]

    if subset.empty:
        print("⚠️ No data in view and running spans.")
        return results


    for var, config in variable_config.items():
        if var not in subset.columns:
            continue

        values = subset[var].dropna()
        if values.empty:
            continue

        status = "undefined"
        if "typical" in config:
            low, high = config["typical"]
            out_typical = (values < low) | (values > high)
            print(f"{var}: {out_typical.sum()} / {len(values)} outside typical range")
            if out_typical.any():
                status = "outside typical"
            else:
                status = "within typical"

        if "absolute" in config:
            low, high = config["absolute"]
            out_abs = (values < low) | (values > high)
            print(f"{var}: {out_abs.sum()} / {len(values)} outside absolute range")
            if out_abs.any():
                status = "outside absolute"
            elif status not in ["within typical"]:
                status = "outside typical"

        results[var] = status
    return results