import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd
import numpy as np
import tkinter as tk
from unicodedata import normalize
import os
import json
from file_parsing import load_and_merge_files, resource_path
from datetime import datetime
import pytz
from matplotlib.ticker import FixedLocator, ScalarFormatter


def embed_plot_7800_data(parent_frame, filepaths):
    df, model, metadata = load_and_merge_files(filepaths)
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

    for col in df.columns:
        if col == time_col:
            continue
        y = df[col]

        config = variable_config.get(col, {})
        should_plot = config.get("autoplot", False)

        line, = ax.plot(x, y, label=col, linewidth=1.5, visible=should_plot)
        lines[col] = line
        colors[col] = line.get_color()


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
    hide_outliers_var = tk.BooleanVar(value=True)
    use_human_time = tk.BooleanVar(value=False)

    def open_plot_options():
        options_win = tk.Toplevel(parent_frame)
        options_win.title("Plot Options")
        options_win.geometry("250x200")
        options_win.iconbitmap(resource_path("assets/icon.ico"))


        tk.Label(options_win, text="Line Thickness:").pack(pady=5)
        slider = tk.Scale(options_win, from_=0.5, to=5.0, resolution=0.1, orient='horizontal')
        slider.set(1.5)
        slider.pack(pady=0, padx=10)

        tk.Checkbutton(
            options_win,
            text="Hide Outliers from Zoom",
            variable=hide_outliers_var
        ).pack(pady=5)

        tk.Checkbutton(
            options_win,
            text="Show Human-Readable Time",
            variable=use_human_time
        ).pack(pady=5)

        def apply():
            lw = float(slider.get())
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

    def rescale():
        ymins, ymaxs = [], []

        for var, line in lines.items():
            if not line.get_visible():
                continue

            y_data = df[var]
            conf = variable_config.get(var, {})

            # For y-limits only, apply filtering if 'Hide Outliers' is active
            if hide_outliers_var.get() and "typical" in conf:
                low, high = conf["typical"]
                filtered = y_data[(y_data >= low) & (y_data <= high)]
            else:
                filtered = y_data[np.isfinite(y_data)]

            if filtered.empty:
                continue

            if use_human_time.get():
                ticks = ax.get_xticks()
                tz = pytz.timezone(metadata.get("Timezone", "UTC"))
                fmt_ticks = [datetime.fromtimestamp(t, tz).strftime("%Y-%m-%d %H:%M:%S") for t in ticks]

                ax.xaxis.set_major_locator(FixedLocator(ticks))  # Lock the locations
                ax.set_xticklabels(fmt_ticks, rotation=45, fontsize=8)
            else:
                ax.xaxis.set_major_locator(plt.AutoLocator())
                ax.xaxis.set_major_locator(plt.AutoLocator())
                ax.xaxis.set_major_formatter(ScalarFormatter())
                ax.ticklabel_format(style='sci', axis='x', scilimits=(9, 9))  # keep sci formatting for large values

            ymins.append(filtered.min())
            ymaxs.append(filtered.max())

        if ymins and ymaxs:
            ymin, ymax = min(ymins), max(ymaxs)
            pad = (ymax - ymin) * 0.05
            ax.set_ylim(ymin - pad, ymax + pad)

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