import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import sys
from data_processing import embed_plot_7800_data

# To allow the exe to access assets
from file_parsing import resource_path, set_icon

from version import __version__

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"7800 Data Viewer v{__version__}")
        self.root.geometry("650x250")
        self.root.resizable(False, False)

        top_frame = tk.Frame(root)
        top_frame.pack(padx=10, pady=10, fill='x')

        self.logo_img = ImageTk.PhotoImage(Image.open(resource_path("assets/logo.png")).resize((144, 60)))
        tk.Label(top_frame, image=self.logo_img).pack(side='left')

        tk.Label(top_frame, text="LI-7800 Series Data Viewer", font=("Helvetica", 16, "bold")).pack(side='right')

        file_frame = tk.Frame(root)
        file_frame.pack(pady=20)

        self.file_display_var = tk.StringVar()
        tk.Label(root, textvariable=self.file_display_var, font=("Helvetica", 10)).pack()

        self.data_path = []
        self.add_file_selector(file_frame, ".data File:", self.data_path, self.browse_data)

        tk.Button(root, text="Open Plot", font=("Helvetica", 12), command=self.plot_file).pack(pady=10)

    def add_file_selector(self, parent, label, var, command):
        row = tk.Frame(parent)
        row.pack(pady=5, fill='x')

        tk.Label(row, text=label, anchor='w').grid(row=0, column=0, padx=(0, 5), sticky='w')
        entry = tk.Entry(row, textvariable=self.file_display_var, state='readonly')
        entry.grid(row=0, column=1, sticky='ew', padx=(0, 5))
        entry.bind("<Button-1>", lambda e: command())

        browse_btn = tk.Button(row, text="Browse", command=command)
        browse_btn.grid(row=0, column=2)

        row.columnconfigure(1, weight=1)  # Allow the entry field to expand nicely

    def browse_data(self):
        paths = filedialog.askopenfilenames(filetypes=[("7800 .data Files", "*.data")])
        if paths:
            self.data_paths = list(paths)
            num_files = len(self.data_paths)
            if num_files == 1:
                display_text = f"{num_files} file selected"
            else:
                display_text = f"{num_files} files selected"
            self.file_display_var.set(display_text)

    def plot_file(self):
        if not self.data_paths:
            messagebox.showerror("Missing File", "Please select a .data file.")
            return

        try:
            plot_window = tk.Toplevel(self.root)
            plot_window.title("Data Plot Viewer")
            plot_window.geometry("1600x800")
            set_icon(plot_window)
            embed_plot_7800_data(plot_window, self.data_paths)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to plot:\n{self.data_paths}\n\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    set_icon(root)

    def on_closing():
        root.destroy()
        sys.exit()


    root.protocol("WM_DELETE_WINDOW", on_closing)
    app = App(root)
    root.mainloop()


# Adapted for 7800 Viewer by Elijah Schoneweis - 6/11/2025
