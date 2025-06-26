import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import sys
import os
from data_processing import embed_plot_7800_data

# To allow the exe to access assets
from file_parsing import resource_path

from version import __version__

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"7800 Data Viewer v{__version__}")
        self.root.geometry("650x250")
        self.root.iconbitmap(resource_path("assets/icon.ico"))
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
        row.pack(fill='x', pady=5)

        tk.Label(row, text=label, width=15, anchor='w').pack(side='left')
        entry = tk.Entry(row, textvariable=self.file_display_var, width=50, state='readonly')
        entry.pack(side='left', padx=5)
        entry.bind("<Button-1>", lambda e: command())
        tk.Button(row, text="Browse", command=command).pack(side='left')

    def browse_data(self):
        paths = filedialog.askopenfilenames(filetypes=[("7800 .data Files", "*.data")])
        if paths:
            self.data_paths = list(paths)
            num_files = len(self.data_paths)
            display_text = f"{num_files} file(s) selected"
            self.file_display_var.set(display_text)

    def plot_file(self):
        if not self.data_paths:
            messagebox.showerror("Missing File", "Please select a .data file.")
            return

        try:
            plot_window = tk.Toplevel(self.root)
            plot_window.title("Data Plot Viewer")
            plot_window.geometry("1200x800")
            plot_window.iconbitmap(resource_path("assets/icon.ico"))
            embed_plot_7800_data(plot_window, self.data_paths)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to plot:\n{self.data_paths}\n\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()


# Adapted for 7800 Viewer by Elijah Schoneweis - 6/11/2025
