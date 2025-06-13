import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import sys
import os
from data_processing import embed_plot_7800_data

# To allow the exe to access assets
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("7800 Data Viewer")
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

        self.data_path = tk.StringVar()
        self.add_file_selector(file_frame, ".data File:", self.data_path, self.browse_data)

        tk.Button(root, text="Open Plot", font=("Helvetica", 12), command=self.plot_file).pack(pady=10)

    def add_file_selector(self, parent, label, var, command):
        row = tk.Frame(parent)
        row.pack(fill='x', pady=5)

        tk.Label(row, text=label, width=15, anchor='w').pack(side='left')
        entry = tk.Entry(row, textvariable=var, width=50)
        entry.pack(side='left', padx=5)
        entry.bind("<Button-1>", lambda e: command())
        tk.Button(row, text="Browse", command=command).pack(side='left')

    def browse_data(self):
        path = filedialog.askopenfilename(filetypes=[("7800 .data Files", "*.data")])
        if path:
            self.data_path.set(path)

    def plot_file(self):
        filepath = self.data_path.get().strip()
        if not filepath:
            messagebox.showerror("Missing File", "Please select a .data file.")
            return

        try:
            plot_window = tk.Toplevel(self.root)
            plot_window.title("Data Plot Viewer")
            plot_window.geometry("1000x600")
            plot_window.iconbitmap(resource_path("assets/icon.ico"))
            embed_plot_7800_data(plot_window, filepath)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to plot:\n{filepath}\n\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()


# Adapted for 7800 Viewer by Elijah Schoneweis - 6/11/2025
