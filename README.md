# LI-7800 Series Data Viewer

**LI-7800 Series Data Viewer** is a cross-platform graphical interface for visualizing and analyzing `.data` files produced by LI-COR 7800 series instruments (e.g., LI-7810). It provides span-based data segmentation, spec validation, and intuitive interaction with multivariable time-series plots.

---

## 🚀 Features

- 📊 **Multi-variable plotting** of TGA `.data` files
- 🔍 **Zoom and pan** support with dynamic data rescaling
- ✅ **Startup and running span detection** (based on NDX and temperature thresholds)
- ⚠️ **Outlier filtering** via IQR or running-only views
- 📉 **Stats panel** with real-time min, max, mean, and range compliance
- 🎛 **Config editor** for per-variable threshold editing and autoplots
- 🧱 **Error value masking** via customizable JSON
- 🧪 **Supports multiple model types** (TG10, etc.)
- 🧰 Built-in file browser and smooth matplotlib + Tkinter integration

---

## 📂 File Structure

```
├── assets/
│   ├── icon.ico
│   ├── logo.png
│   └── [model].json          # e.g., TG10.json for variable specs
├── scripts/
│   ├── data_processing.py    # Plotting logic
│   ├── manipulation.py       # Span detection, spec stats, filtering
│   ├── file_parsing.py       # File loading, JSON resource path
│   └── sim_gui.py            # Tkinter main app
```

---

## ⚙️ Usage

### 🖥 Running Locally

You can run the program using:

```bash
python scripts/sim_gui.py
```

Alternatively, a packaged `.exe` or Mac `.app` is supplied in releases.

### 📈 Opening Data

1. Launch the application.
2. Use the **Browse** button to select one or more `.data` files.
3. Click **"Open Plot"** to load and interact with the plot viewer.

---

## 🔧 Configuration JSON

Each instrument model has a JSON file (e.g., `TG10.json`) defining:

```json
{
  "CH4 (ppb)": {
    "typical": [1850, 2100],
    "absolute": [1600, 2300],
    "autoplot": true
  }
}
```

To manage this:

- Use **"Config Editor"** in the plot window to:
  - 🖊 Modify typical/absolute ranges
  - ➕ Add/remove variables based on loaded file columns
  - ✅ Enable/disable autoplots

---

## 🧠 Span Logic

Span detection identifies:

- **Startup** = NDX present but not yet thermally stable (T ≥ 55°C/54°C)
- **Running** = After startup, until NDX goes inactive or there's a >10s gap
- **Off** = All other periods

## ⭕ Outlier Handling

Valid outliers are used to determine the initial frame of data, and the validation ranges for each variable based on the configuration json. The options for handling are:

- **Running** = Only uses data within running spans for determining outliers
- **IQR** = Same restriction, but also applies interquantile range filtering (data within the 25%-75% percentile)
- **None** = Applies no filtering to what is included in outlier determination

---

## ⚠️ Error Handling

- Files containing invalid codes (e.g., `-9999`) are auto-converted to `NaN` based on `assets/error_codes.json`.
- If a JSON config for a model is missing or empty, a default template is generated.
- Span detection failure or zooming to empty views will trigger graceful fallbacks.

---

## 📦 Building Executables

For Windows:

```bash
pyinstaller windows.spec
```

For macOS (Intel/Silicon):

```bash
pyinstaller mac.spec
```

Make sure assets are accessible via `resource_path()` in `file_parsing.py`.

---

## 🧪 Developer Notes

- GUI is managed via Tkinter (`sim_gui.py`)
- Plotting is done with Matplotlib embedded in the Tk window
- Span logic and spec checks are implemented in `manipulation.py`
- Data loading and JSON resources handled by `file_parsing.py`
- Project adheres to no-new-dependency policy (pure stdlib + matplotlib, pandas, numpy)

---

## 👨‍💻 Author

Developed by Elijah Schoneweis
