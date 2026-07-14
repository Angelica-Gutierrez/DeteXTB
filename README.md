# DeteXTB

DeteXTB is a Streamlit-based tuberculosis X-ray detection and case management system. It includes separate workflows for receptionist and manager users, with dashboards, patient records, registration, case management, reports, heatmaps, and account/privacy pages.

## Features

- Streamlit web interface
- Receptionist and manager user roles
- X-ray upload and TB prediction workflow
- Supabase-backed authentication and records
- Dashboard, reports, heatmap, and case management modules
- Light/dark themed UI assets

## Important Model File Notice

The `.keras` model files are **not included in this GitHub repository** because they are too large for a normal GitHub upload.

Excluded model files include:

- `deteXTB_final_mandaue_model.keras`

The app expects the main model file to be named:

```text
deteXTB_final_mandaue_model.keras
```

In `main.py`, the app is configured to download the model with `gdown` if the file is missing. If the download link is unavailable, place the required `.keras` model file manually in the project root folder before running the app.

## Project Structure

```text
DeteXTB/
|-- main.py
|-- Login.py
|-- Supabase.py
|-- Manager/
|-- Receptionist/
|-- images/
`-- uploaded_xrays/
```

## Requirements

Install the required Python packages before running the project:

```powershell
pip install streamlit tensorflow gdown pillow python-dotenv supabase pandas numpy matplotlib requests folium streamlit-autorefresh streamlit-image-zoom scikit-image fpdf openpyxl python-dateutil pytz
```

## Setup

1. Clone the repository:

```powershell
git clone https://github.com/Angelica-Gutierrez/DeteXTB.git
cd DeteXTB
```

2. Add the model file if needed:

```text
deteXTB_final_mandaue_model.keras
```

Place it in the project root folder, beside `main.py`.

3. Configure Supabase if needed.

Create a `.env` file in the project root:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

4. Run the app:

```powershell
streamlit run main.py
```

## Notes

- `.keras` files are ignored by Git because of their large size.
- Python cache files such as `__pycache__/` and `*.pyc` are also ignored.
- If the model file is not present, the app may try to download it automatically using the link configured in `main.py`.
