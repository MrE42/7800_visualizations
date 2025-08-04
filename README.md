<h1>
  LI-7800 Series Data Viewer
  <img align="right" src="./scripts/assets/logo.png" alt="LI-COR" width="120"/>
</h1>

**LI-7800 Series Data Viewer** is a cross-platform graphical interface for visualizing and analyzing `.data` files produced by LI-COR 7800 series instruments (e.g., LI-7810). It provides period-based data segmentation, spec validation, and intuitive interaction with multivariable time-series plots.

---

## 🚀 Features

- 📊 **Multi-variable plotting** of TGA `.data` files
- 🔍 **Zoom and pan** support with dynamic data rescaling
- ✅ **Startup, running and shutdown period detection** (based on NDX and temperature thresholds)
- ⚠️ **Outlier filtering** via IQR or running-only views
- 📉 **Stats panel** with real-time min, max, mean, and range compliance
- 🎛 **Config editor** for per-variable threshold editing and autoplots
- 🧱 **Error value masking** via customizable JSON
- 🧪 **Supports multiple model types** (TG10, etc.)
- 👾 **Differeniates between TGA Software versions** (2.3.8, etc.)

---

## ⚙️ Usage

### 🖥 Running Locally

Packaged executables (`.exe` & `.app`) are supplied in [Releases](https://github.com/MrE42/7800_visualizations/releases/). You can also run the program using:

```bash
python scripts/sim_gui.py
```

### 📈 Opening Data

1. Launch the application.
2. Use the **Browse** button to select one or more `.data` files.
3. Click **"Open Plot"** to load and interact with the plot viewer.

---

## 🔧 Configuration JSON

Each instrument model has a folder with JSON files for each TGA software version (e.g., `TG10/2.3.8.json`) defining:

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
  - 💾 Save local changes to change the defaults

---

## 🧠 Period Logic

Period detection identifies:

- 🟦 **Startup** = NDX present but not yet thermally stable (T ≥ 55°C/54°C)
- 🟩 **Running** = Once thermally stable, and until the device stops indexing.
- 🟥 **Shutdown** = Period where the device is shutting down
  
## ⭕ Outlier Handling

Valid outliers are used to determine the initial frame of data, and the validation ranges for each variable based on the configuration json. The options for handling are:

- **Running** = Only uses data within running periods for determining outliers
- **IQR** = Same restriction, but also applies interquantile range filtering (data within the 25%-75% percentile)
- **None** = Applies no filtering to what is included in outlier determination

If you are enountering outliers near the end of your running periods and want to exclude them, adjust the **Running Period Threshold** in the **Plot Options** menu. This directly changes the length of the **Shutdown** period.

---

## ⚠️ Error Handling

- Files containing invalid codes (e.g., `-9999`) are auto-converted to `NaN` based on `assets/error_codes.json`.
- If a JSON config for a model is missing or empty, a default template is generated.
- Period detection failure or zooming to empty views will trigger graceful fallbacks.

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

Make sure any additional assets are accessed via `resource_path()` in `file_parsing.py`.

---

## 🧪 Developer Notes

- GUI is managed via Tkinter (`sim_gui.py`)
- Plotting is done with Matplotlib embedded in the Tk window
- Period logic and spec checks are implemented in `manipulation.py`
- Data loading and JSON resources handled by `file_parsing.py`
- Project adheres to no-new-dependency policy (pure stdlib + matplotlib, pandas, numpy)

---

## 📂 File Structure

```
├── assets/
│   ├── icon.ico
│   ├── logo.png
│   └── defaults/
│        └──[model].json          # e.g., TG10.json for default variable specs
├── scripts/
│   ├── data_processing.py    # Plotting logic
│   ├── manipulation.py       # Period detection, spec stats, filtering
│   ├── file_parsing.py       # File loading, JSON resource path
│   └── sim_gui.py            # Tkinter main app
```

---

## 👨‍💻 Author

Developed by Elijah Schoneweis
