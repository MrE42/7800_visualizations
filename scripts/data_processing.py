from tkinter import messagebox
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd
import numpy as np
import tkinter as tk
from unicodedata import normalize
import os
import json
from datetime import datetime
import pytz
from matplotlib.ticker import FixedLocator, ScalarFormatter, FuncFormatter

from manipulation import *
from file_parsing import *


def embed_plot_7800_data(parent_frame, filepaths):
    df, model, metadata = load_and_merge_files(filepaths)

    df = clean_error_codes(df)

    time_col = next((col for col in df.columns if "SECONDS" in col.upper()), df.columns[0])
    x = df[time_col]

    # Load range config for this model
    config_path = resource_path(os.path.join("assets", f"{model}.json"))
    variable_config = {}

    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            raw_config = json.load(f)

            def normalize_key(key):
                return normalize('NFC', key.strip())

            normalized_config = {normalize_key(k): v for k, v in raw_config.items()}

            print("\n📄 Normalized config keys:")
            for key in normalized_config:
                print(f"  - {repr(key)}")

            print("\n📊 Normalized DataFrame columns:")
            for col in df.columns:
                norm_col = normalize_key(col)
                print(f"  - {repr(norm_col)}")
                if norm_col in normalized_config:
                    variable_config[col] = normalized_config[norm_col]
                else:
                    print(f"    ⚠️  No match found for: {repr(norm_col)}")
    else:
        print("<UNK> Config file not found.")

    print("\n🔍 Identifying startup and outlier regions...")
    spans = identify_operational_spans(df)

    latest_stats = {}
    stats_win_ref = None
    stats_text_ref = None

    # Classify variable statuses
    validation_results = {}
    for var, conf in variable_config.items():
        col_data = df.get(var)
        if col_data is None:
            continue
        values = col_data.dropna()

        status = "unclassified"
        if "absolute" in conf and conf["absolute"][0] is not None and conf["absolute"][1] is not None:
            out_abs = (values < conf["absolute"][0]) | (values > conf["absolute"][1])
            if out_abs.any():
                status = "outside absolute"
            else:
                if "typical" in conf and conf["typical"][0] is not None and conf["typical"][1] is not None:
                    out_typ = (values < conf["typical"][0]) | (values > conf["typical"][1])
                    if out_typ.any():
                        status = "outside typical"
                    else:
                        status = "within typical"
                else:
                    status = "within absolute"
        validation_results[var] = status

    print("Loaded model config keys:", list(variable_config.keys()))
    print("Available DataFrame columns:", list(df.columns))
    print(model)
    serial = metadata.get("SN", "Unknown SN")
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    fig.suptitle(f"LI-78{model[2]}{model[3]}: {serial}", fontsize=14)
    lines = {}
    colors = {}

    break_on_gaps_enabled = True  # default, updated by Plot Options
    # Example time_col assignment from earlier:
    time_col = next((col for col in df.columns if "SECONDS" in col.upper()), df.columns[0])
    x = df[time_col]
    plottable_columns = [col for col in df.columns if col != time_col and col not in ['NANOSECONDS (nsecs)', 'DATE (date)', 'TIME (time)']]
    colormap = cm.get_cmap('berlin', len(plottable_columns))
    for i, col in enumerate(plottable_columns):
        y = df[col]

        if break_on_gaps_enabled:
            x_plot, y_plot = insert_nan_gaps(x, y, threshold=2.0)
        else:
            x_plot, y_plot = x, y

        config = variable_config.get(col, {})
        should_plot = config.get("autoplot", False)
        color = mcolors.to_hex(colormap(i))
        line, = ax.plot(x_plot, y_plot, label=col, linewidth=1.5, visible=should_plot, color=color)
        lines[col] = line
        colors[col] = color


    ax.set_xlabel(time_col)
    ax.set_ylabel("Value")
    ax.grid(True)

    canvas_frame = tk.Frame(parent_frame)
    canvas_frame.pack(side='left', fill='both', expand=True)

    canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

    toolbar = NavigationToolbar2Tk(canvas, canvas_frame)
    toolbar.update()
    toolbar.pack(side='bottom', fill='x')

    if hasattr(toolbar, 'children'):
        for widget in toolbar.winfo_children():
            if isinstance(widget, tk.Button) and widget['command'] == toolbar.configure_subplots:
                widget.destroy()

    # Toggles
    hide_outliers_mode = tk.StringVar(value="IQR")  # Options: None, IQR, Running
    use_human_time = tk.BooleanVar(value=True)
    gap_toggle_var = tk.BooleanVar(value=True)
    gap_threshold = tk.IntVar(value=2)
    draw_spans_var = tk.BooleanVar(value=True)
    run_threshold = tk.IntVar(value=2)

    def open_plot_options():
        options_win = tk.Toplevel(parent_frame)
        options_win.title("Plot Options")
        options_win.geometry("280x400")
        options_win.iconbitmap(resource_path("assets/icon.ico"))

        # Line thickness
        tk.Label(options_win, text="Line Thickness:").pack(pady=(5, 0))
        slider = tk.Scale(options_win, from_=0.5, to=5.0, resolution=0.1, orient='horizontal')
        slider.set(1.5)
        slider.pack(pady=5, padx=10)

        # Hide outliers menu
        tk.Label(options_win, text="Outlier Handling:").pack(pady=(5, 0))
        outlier_dropdown = tk.OptionMenu(
            options_win, hide_outliers_mode, "None", "IQR", "Running"
        )
        outlier_dropdown.pack(pady=5)

        gap_checkbox = tk.Checkbutton(options_win, text="Break lines at gaps", variable=gap_toggle_var)
        gap_checkbox.pack(pady=5)

        # Threshold slider
        tk.Label(options_win, text="Data Gap Threshold (seconds):").pack(pady=(5, 0))
        gap_thresh_entry = tk.Entry(options_win)
        gap_thresh_entry.insert(0, str(gap_threshold.get()))
        gap_thresh_entry.pack(pady=5, padx=10)

        tk.Checkbutton(
            options_win,
            text="Show Human-Readable Time",
            variable=use_human_time
        ).pack(pady=5)

        tk.Checkbutton(
            options_win,
            text="Draw Startup/Running Spans",
            variable=draw_spans_var
        ).pack(pady=5)

        tk.Label(options_win, text="Running Span Threshold (seconds):").pack(pady=(5, 0))
        run_thresh_entry = tk.Entry(options_win)
        run_thresh_entry.insert(0, str(run_threshold.get()))
        run_thresh_entry.pack(pady=5, padx=10)

        def apply():
            nonlocal break_on_gaps_enabled
            lw = float(slider.get())
            try:
                val = float(gap_thresh_entry.get())
                gap_threshold.set(val)
            except ValueError:
                messagebox.showerror("Invalid Input", "Gap threshold must be a number.")
                return
            try:
                v = float(run_thresh_entry.get())
                if v != run_threshold.get():
                    run_threshold.set(v)
                    nonlocal spans
                    spans = identify_operational_spans(df, run_threshold.get())
                on_zoom()
            except ValueError:
                messagebox.showerror("Invalid Input", "Running end threshold must be a number.")
                return
            if break_on_gaps_enabled != gap_toggle_var.get():
                break_on_gaps_enabled = gap_toggle_var.get()
                for var, line in lines.items():
                    line.set_linewidth(lw)

                    # Reload x/y data with or without gaps
                    x = df[time_col]
                    y = df[var]
                    if break_on_gaps_enabled:
                        x_plot, y_plot = insert_nan_gaps(x, y, threshold=gap_threshold.get())
                    else:
                        x_plot, y_plot = x, y

                    line.set_xdata(x_plot)
                    line.set_ydata(y_plot)

            for line in lines.values():
                line.set_linewidth(lw)

            rescale()

        tk.Button(options_win, text="Apply", command=apply).pack(pady=5)

    custom_btn = tk.Button(toolbar, text="Plot Options", command=open_plot_options)
    custom_btn.pack(side='left')

    control_frame = tk.Frame(parent_frame)
    control_frame.pack(side='right', fill='y')




    tk.Label(control_frame, text="Search Variable:", font=("Helvetica", 10, "bold")).pack(pady=(5, 2))
    search_var = tk.StringVar()
    search_entry = tk.Entry(control_frame, textvariable=search_var, width=30)
    search_entry.pack(padx=5, pady=(0, 5), fill='x')

    textbox = tk.Text(control_frame, height=20, width=40)
    textbox.pack(padx=5, pady=5, fill='y', expand=True)
    textbox.config(
        state='disabled',
        cursor='arrow',
        exportselection=False,
        highlightthickness=0,
        bd=0,
        wrap='none',
        takefocus=0
    )  # make it read-only after inserting

    variable_names = list(lines.keys())



    # Updating the variable list
    def update_listbox(*args):
        search_term = search_var.get().lower()
        textbox.config(state='normal')
        textbox.delete("1.0", "end")

        for var in variable_names:
            if search_term not in var.lower():
                continue

            visible = lines[var].get_visible()
            checkmark = "☑" if visible else "☐"
            status = validation_results.get(var, "unclassified")
            icon, color = {
                "within typical": ("✅", "green"),
                "outside typical": ("⚠️", "orange"),
                "outside absolute": ("❌", "red"),
                "unclassified": ("❓", "gray")
            }.get(status, ("❓", "gray"))

            line_text = f"{checkmark} {icon} {var}\n"
            start_idx = textbox.index("end-1c")
            end_idx = f"{start_idx}+{len(line_text)}c"
            textbox.insert("end", line_text)
            textbox.tag_add(var, start_idx, end_idx)
            textbox.tag_config(var, foreground=color)

        textbox.config(
            state='disabled',
            cursor='arrow',
            exportselection=False,
            highlightthickness=0,
            bd=0,
            wrap='none',
            takefocus=0
        )

    update_listbox()

    legend_frame = tk.Frame(control_frame)
    legend_frame.pack(pady=5, fill='both', expand=False)
    legend_labels = {}

    def update_legend():
        for widget in legend_frame.winfo_children():
            widget.destroy()
        for var in variable_names:
            if lines[var].get_visible():
                row = tk.Frame(legend_frame)
                row.pack(fill='x', padx=2, pady=1)
                swatch = tk.Label(row, bg=colors[var], width=2, height=1)
                swatch.pack(side='left')
                label = tk.Label(row, text=var, anchor='w')
                label.pack(side='left')
                legend_labels[var] = label

    update_listbox()
    update_legend()
    spans_drawn = False
    def rescale():
        nonlocal spans_drawn
        nonlocal spans

        mode = hide_outliers_mode.get()
        ymins, ymaxs = [], []

        xlim = ax.get_xlim()
        visible_mask = (df[time_col] >= xlim[0]) & (df[time_col] <= xlim[1])

        if mode == "Running" or mode == "IQR":
            # Combine all running span filters
            running_mask = pd.Series(False, index=df.index)
            for startup, running in spans:
                r_start, r_end = running
                running_mask |= (df[time_col] >= r_start) & (df[time_col] <= r_end - run_threshold.get())
            combined_mask = visible_mask & running_mask
        else:
            combined_mask = visible_mask

        for var, line in lines.items():
            if not line.get_visible():
                continue

            y_data = df[var][combined_mask].dropna()

            if y_data.empty:
                continue

            # Hide outliers using IQR method
            if mode == "IQR":
                Q1 = np.percentile(y_data, 25)
                Q3 = np.percentile(y_data, 75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                y_data = y_data[(y_data >= lower_bound) & (y_data <= upper_bound)]


            if y_data.empty:
                continue

            ymins.append(y_data.min())
            ymaxs.append(y_data.max())

        if ymins and ymaxs:
            ymin, ymax = min(ymins), max(ymaxs)
            if ymin == ymax:
                ax.set_ylim(ymin - 1, ymax + 1)
            else:
                pad = (ymax - ymin) * 0.05
                ax.set_ylim(ymin - pad, ymax + pad)

        # Remove old spans first
        if not draw_spans_var.get() and spans_drawn:
            spans_drawn = False
            for patch in ax.patches[:]:
                if getattr(patch, "_span", False):
                    patch.remove()

        # Draw new spans only if toggled on
        if draw_spans_var.get() and not spans_drawn:
            spans_drawn = True
            for (startup_start, startup_end), (running_start, running_end) in spans:
                start = ax.axvspan(startup_start, startup_end, color='blue', alpha=0.2, label='Starting')
                run = ax.axvspan(running_start, running_end, color='green', alpha=0.1, label='Running')
                start._span = True
                run._span = True

        if use_human_time.get():
            tz = pytz.timezone(metadata.get("Timezone", "UTC"))
            ax.xaxis.set_major_formatter(FuncFormatter(
                lambda x, _: datetime.fromtimestamp(x, tz).strftime("%Y-%m-%d %H:%M:%S") if x > 0 else ""
            ))
            ax.tick_params(axis='x', rotation=45, labelsize=8)
        else:
            ax.xaxis.set_major_locator(plt.AutoLocator())
            ax.xaxis.set_major_formatter(ScalarFormatter())
            ax.ticklabel_format(style='sci', axis='x', scilimits=(9, 9))  # keep sci formatting for large values

        canvas.draw()

    rescale()

    search_var.trace_add('write', update_listbox)

    # Toggling functionality
    def toggle_variable_by_click(event=None):
        idx = textbox.index("@%d,%d" % (event.x, event.y))
        line = textbox.get(f"{idx} linestart", f"{idx} lineend")
        parts = line.split(maxsplit=2)
        if len(parts) < 3:
            return
        var = parts[2]
        if var not in lines:
            return

        line_obj = lines[var]
        line_obj.set_visible(not line_obj.get_visible())
        update_listbox()
        update_legend()

        rescale()
        # Old Auto-rescale
        # ymins, ymaxs = [], []
        # for l in lines.values():
        #     if l.get_visible():
        #         y = l.get_ydata()
        #         y = y[np.isfinite(y)]
        #         if y.size > 0:
        #             ymins.append(np.min(y))
        #             ymaxs.append(np.max(y))
        # if ymins and ymaxs:
        #     ymin, ymax = min(ymins), max(ymaxs)
        #     pad = (ymax - ymin) * 0.05
        #     ax.set_ylim(ymin - pad, ymax + pad)
        # canvas.draw()

    def ignore_event(event):
        return "break"

    for event in ("<Button-1>", "<B1-Motion>", "<Double-1>", "<Triple-1>", "<ButtonRelease-1>"):
        textbox.bind(event, ignore_event)

    textbox.bind("<Double-1>", toggle_variable_by_click)  # Restore our double-click toggle
    textbox.bind("<ButtonRelease-1>", lambda e: "break")  # Ignore default selection effect

    e_legend_frame = tk.Frame(control_frame)
    e_legend_frame.pack(pady=10, padx=5, anchor='w')

    legend_items = [
        ("✅", "Within Typical Range", "green"),
        ("⚠️", "Outside Typical Range", "orange"),
        ("❌", "Outside Absolute Range", "red"),
        ("❓", "Unclassified Restrictions", "gray")
    ]

    for symbol, label, color in legend_items:
        row = tk.Frame(e_legend_frame)
        row.pack(anchor='w')
        icon = tk.Label(row, text=symbol, fg=color, font=("Segoe UI", 10))
        icon.pack(side="left")
        text = tk.Label(row, text=f"= {label}", font=("Segoe UI", 9))
        text.pack(side="left")

    def update_stats_window():
        if not stats_text_ref or not stats_text_ref.winfo_exists():
            return

        stats_text_ref.config(state='normal')
        stats_text_ref.delete("1.0", "end")

        if not latest_stats:
            stats_text_ref.insert("end", "⚠️ No data available.\n")
        else:
            for var, stat in latest_stats.items():
                stats_text_ref.insert("end", f"{var}:\n")
                stats_text_ref.insert("end", f"  Mean: {stat['mean']:.2f}\n")
                stats_text_ref.insert("end", f"  Min:  {stat['min']:.2f}\n")
                stats_text_ref.insert("end", f"  Max:  {stat['max']:.2f}\n")
                if stat["in_typical"] is not None:
                    stats_text_ref.insert("end", f"  In Typical: {stat['in_typical']}/{stat['total']}\n")
                if stat["in_absolute"] is not None:
                    stats_text_ref.insert("end", f"  In Absolute: {stat['in_absolute']}/{stat['total']}\n")
                stats_text_ref.insert("end", "\n")

        stats_text_ref.config(state='disabled')

    def on_zoom(event_ax = None):
        nonlocal validation_results
        nonlocal latest_stats
        print("zooming")
        validation_results, latest_stats = update_spec_checks(ax, df, variable_config, [r for _, r in spans], validation_results, run_threshold.get(), hide_outliers_mode.get())
        update_listbox()
        update_stats_window()

    # Connect the zoom (x-axis change) event
    ax.callbacks.connect("xlim_changed", on_zoom)

    on_zoom()



    def open_stats_window():
        nonlocal stats_win_ref, stats_text_ref

        if stats_win_ref and stats_win_ref.winfo_exists():
            stats_win_ref.lift()
            return

        stats_win = tk.Toplevel(parent_frame)
        stats_win.title("Statistics Window")
        stats_win.geometry("280x600")
        stats_win.iconbitmap(resource_path("assets/icon.ico"))
        stats_win_ref = stats_win

        tk.Label(stats_win, text="Visible & Running Segment Stats", font=("Helvetica", 12, "bold")).pack(pady=10)

        stats_text = tk.Text(stats_win, wrap='none', font=("Courier New", 9))
        stats_text.pack(fill='both', expand=True, padx=5, pady=5)
        stats_text_ref = stats_text

        update_stats_window()

    stats_btn = tk.Button(toolbar, text="Statistics", command=open_stats_window)
    stats_btn.pack(side='left')

if __name__ == "__main__":
    import sys

    root = tk.Tk()
    root.title("Embedded Plot Test")

    if len(sys.argv) > 1:
        embed_plot_7800_data(root, sys.argv[1])
    else:
        tk.Label(root, text="Usage: provide a .data filepath as CLI arg").pack()

    root.mainloop()

# Written by Elijah Schoneweis - 6/11/2025