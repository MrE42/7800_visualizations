import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd
import numpy as np
import tkinter as tk
from file_parsing import parse_7800_data_file


def embed_plot_7800_data(parent_frame, filepath):
    df, model = parse_7800_data_file(filepath)

    time_col = next((col for col in df.columns if "SECONDS" in col.upper()), df.columns[0])
    x = df[time_col]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.suptitle(f"LI-78{model[2]}{model[3]} Data Visualization", fontsize=14)
    lines = {}
    colors = {}

    for col in df.columns:
        if col == time_col:
            continue
        y = df[col]
        line, = ax.plot(x, y, label=col, linewidth=1.5, visible=False)
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

    def open_plot_options():
        options_win = tk.Toplevel(parent_frame)
        options_win.title("Plot Options")
        options_win.geometry("250x100")

        tk.Label(options_win, text="Line Thickness:").pack(pady=5)
        slider = tk.Scale(options_win, from_=0.5, to=5.0, resolution=0.1, orient='horizontal')
        slider.set(1.5)
        slider.pack(pady=5, padx=10)

        def apply():
            lw = float(slider.get())
            for line in lines.values():
                line.set_linewidth(lw)
            canvas.draw()

        tk.Button(options_win, text="Apply", command=apply).pack(pady=5)

    custom_btn = tk.Button(toolbar, text="Plot Options", command=open_plot_options)
    custom_btn.pack(side='left')

    control_frame = tk.Frame(parent_frame)
    control_frame.pack(side='right', fill='y')

    tk.Label(control_frame, text="Search Variable:", font=("Helvetica", 10, "bold")).pack(pady=(5, 2))
    search_var = tk.StringVar()
    search_entry = tk.Entry(control_frame, textvariable=search_var, width=30)
    search_entry.pack(padx=5, pady=(0, 5), fill='x')

    listbox = tk.Listbox(control_frame, exportselection=False, height=20, width=30)
    listbox.pack(padx=5, pady=5, fill='y', expand=True)
    variable_names = list(lines.keys())
    for var in variable_names:
        listbox.insert('end', f"☐ {var}")

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

    def update_listbox(*args):
        search_term = search_var.get().lower()
        listbox.delete(0, 'end')
        for var in variable_names:
            visible = lines[var].get_visible()
            checkmark = '☑' if visible else '☐'
            if search_term in var.lower():
                listbox.insert('end', f"{checkmark} {var}")

    search_var.trace_add('write', update_listbox)

    def toggle_selected(event=None):
        selection = listbox.curselection()
        for i in selection:
            entry = listbox.get(i)
            checkmark, var = entry[:1], entry[2:]
            line = lines[var]
            new_state = not line.get_visible()
            line.set_visible(new_state)

        listbox.delete(0, 'end')
        for var in variable_names:
            visible = lines[var].get_visible()
            checkmark = '☑' if visible else '☐'
            listbox.insert('end', f"{checkmark} {var}")

        ymins, ymaxs = [], []
        for line in lines.values():
            if line.get_visible():
                y_data = line.get_ydata()
                y_data = y_data[np.isfinite(y_data)]
                if y_data.size > 0:
                    ymins.append(np.min(y_data))
                    ymaxs.append(np.max(y_data))
        if ymins and ymaxs:
            ymin, ymax = min(ymins), max(ymaxs)
            headroom = (ymax - ymin) * 0.05
            ax.set_ylim(ymin - headroom, ymax + headroom)

        update_legend()
        canvas.draw()

    listbox.bind('<Double-1>', toggle_selected)


if __name__ == "__main__":
    import sys

    root = tk.Tk()
    root.title("Embedded Plot Test")

    if len(sys.argv) > 1:
        embed_plot_7800_data(root, sys.argv[1])
    else:
        tk.Label(root, text="Usage: provide a .data filepath as CLI arg").pack()

    root.mainloop()