# Records.py

import streamlit as st
import io
import numpy as np
import re
import uuid
import time
import requests
from datetime import datetime, date
from PIL import Image, ImageOps
from skimage import filters
from io import BytesIO
from fpdf import FPDF
from PIL import Image as PILImage
import tempfile
import os
from streamlit_image_zoom import image_zoom
from Supabase import supabase
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image as keras_image


IMG_SIZE = (512, 512)
model = st.session_state.model


class PDFReport_format(FPDF):
    def __init__(self, orientation='P', unit='mm', format=None):
        # Use a custom page size: width=210mm, height=350mm (A4 is 297mm)
        super().__init__(orientation, unit, format or (210, 350))

    def header(self):
        try:
            self.image("images/logoonly-dark.png", 10, 4, 40)  # Left logo
        except RuntimeError:
            pass
        try:
            self.image("images/ctu-logo.png", 170, 10, 27)  # Right logo
        except RuntimeError:
            pass

        self.ln(3)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, "Mandaue City Health Office", align='C', ln=1)
        self.set_font('Arial', '', 10)
        self.cell(0, 6, "S.B. Cabahug, Mandaue City, Philippines.", align='C', ln=1)
        self.cell(0, 6, "Call us on: +63 (032) 230 4500 | FB: Mandaue City Public Affairs Office |", align='C', ln=1)
        self.cell(0, 6, "Email: cmo@mandauecity.gov.ph", align='C', ln=1)
        self.ln(10)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, "DeteXTB: AI-Assisted Presumptive Tuberculosis Detection and Mapping System", align='C', ln=1)
        self.ln(6)

    def write_key_value(self, key, value, color=(0, 0, 0)):
        self.set_font("Arial", "B", 11)
        self.set_text_color(0, 0, 0)
        self.set_x(25)
        self.cell(60, 8, f"{key}:", ln=0)
        self.set_text_color(*color)
        self.set_font("Arial", "", 11)
        self.cell(0, 8, str(value), ln=1)

    def footer(self):
        self.set_y(-15)  # 15mm from bottom
        self.set_font('Arial', 'I', 10)
        self.set_text_color(120, 120, 120)

        page_text = f"Page {self.page_no()} of {{nb}}"
        self.cell(0, 10, page_text, align='C')

# --- PDF generation function ---
def generate_patient_pdf(
    selected,
    xray_date,
    result,
    confidence,
    status,
    diagnosis_notes="",
    image_path=None,
    doctor_name=None,
    uploaded_by=None,
    confirmation_date=None,
    confirmed_by=None,
    last_modified=None,
    treatment_info=None  # <-- added treatment info
):
    pdf = PDFReport_format()
    pdf.add_page()

    # --- Page 1: Patient Info + Large X-ray Image ---
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Patient X-Ray Report", ln=1, align="C")
    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Patient Info
    pdf.write_key_value("Patient ID", selected['pt_id'])
    pdf.write_key_value("Patient Name", selected['name'])
    pdf.write_key_value("Age", selected.get('age', 'N/A'))
    pdf.write_key_value("Sex", selected.get('sex', 'N/A'))
    pdf.write_key_value("Phone Number", selected.get('phone', 'N/A'))
    pdf.write_key_value("Home Address", selected.get('address', 'N/A'))
    pdf.ln(8)

    # Large X-ray image below info
    y_img = pdf.get_y() + 5
    img_width = 160
    img_height = 0
    if image_path:
        try:
            if image_path.startswith("http"):
                response = requests.get(image_path)
                response.raise_for_status()
                img = PILImage.open(BytesIO(response.content)).convert("RGB")
            else:
                img = PILImage.open(image_path).convert("RGB")

            aspect = img.height / img.width if img.width else 1
            img_height = int(img_width * aspect)
            img = img.resize((int(img_width * 4), int(img_height * 4)), PILImage.LANCZOS)
            img_bytes = BytesIO()
            img.save(img_bytes, format="JPEG", quality=90)
            img_bytes.seek(0)

            x_img = (pdf.w - img_width) / 2
            pdf.image(img_bytes, x=x_img, y=y_img, w=img_width)
            pdf.set_y(y_img + img_height + 10)
        except Exception as e:
            pdf.set_font("Arial", "I", 12)
            pdf.set_text_color(217, 57, 53)
            pdf.cell(0, 12, f"❌ Failed to load X-ray image ({e})", ln=1)

    # --- Page 2: X-ray Analysis, Signature, Disclaimer ---
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "X-Ray Information", ln=1, align="C")
    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Helper function for right-aligned key-values
    def write_key_value_right(key, value, color=(0, 0, 0)):
        pdf.set_x(25)  # push to right half
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(60, 8, f"{key}:", ln=0)
        pdf.set_text_color(*color)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, str(value), ln=1)

    # Color codes
    dark_orange = (204, 122, 42)
    red = (217, 57, 53)
    green = (0, 128, 0)

    # X-ray fields
    write_key_value_right("X-Ray Date", xray_date)
    if uploaded_by:
        write_key_value_right("Uploaded By", uploaded_by)
    write_key_value_right(
        "Presumptive TB Result", result,
        red if "Positive" in result else green if "Negative" in result else dark_orange
    )
    write_key_value_right("AI Confidence Level", str(confidence))
    write_key_value_right(
        "Final Diagnosis", status,
        red if "Confirmed Positive" in status else green if "Confirmed Negative" in status else dark_orange
    )
    if confirmation_date and status in ["Confirmed Positive", "Confirmed Negative"]:
        write_key_value_right("Confirmation Date", confirmation_date)
    if confirmed_by and status in ["Confirmed Positive", "Confirmed Negative"]:
        write_key_value_right("Confirmed By", confirmed_by)
    if last_modified:
        write_key_value_right("Last Modified", last_modified)

    # Diagnostic Notes
    pdf.set_x((pdf.w - img_width) / 2)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(60, 8, "Final Diagnosis Notes:", ln=1)
    pdf.set_x((pdf.w - img_width) / 2)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(img_width, 8, diagnosis_notes if diagnosis_notes else "No diagnostic note provided.")

    # --- Page 3: Treatment Info ---
    if treatment_info:
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Treatment Information", ln=1, align="C")
        pdf.ln(3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        # Render treatment fields using same write_key_value_right
        write_key_value_right("Enrolled", treatment_info.get("enrolled"))
        write_key_value_right("Enrolled By", treatment_info.get("enrolled_by"))
        write_key_value_right("Treatment Start Date", treatment_info.get("start_date"))
        
        # Add color to Current Status
        current_status = treatment_info.get("status", "N/A")
        status_color = (0, 0, 0)  # default black
        if current_status and isinstance(current_status, str):
            current_status_lower = current_status.lower()
            if "ongoing" in current_status_lower:
                status_color = (33, 150, 243)  # #2196F3
            elif "interrupted" in current_status_lower:
                status_color = (204, 122, 42)  # Keep your existing dark_orange
            elif "lost to follow-up" in current_status_lower:
                status_color = (156, 39, 176)  # #9C27B0
            elif "transferred out" in current_status_lower:
                status_color = (96, 125, 139)  # #607D8B
            elif "failed" in current_status_lower:
                status_color = red
            elif "completed" in current_status_lower:
                status_color = green
        write_key_value_right("Current Status", current_status, status_color)
        
        write_key_value_right("Expected End Date", treatment_info.get("expected_end_date"))
        write_key_value_right("Actual End Date", treatment_info.get("actual_end_date"))
        
        # Add color to Final Outcome
        outcome = treatment_info.get("outcome", "N/A")
        outcome_color = (0, 0, 0)  # default black
        if outcome and isinstance(outcome, str):
            outcome_lower = outcome.lower()
            if "cured" in outcome_lower:
                outcome_color = green
            elif "completed" in outcome_lower:
                outcome_color = dark_orange  # Treatment completed gets orange
        write_key_value_right("Final Outcome", outcome, outcome_color)
        
        write_key_value_right("Last Modified", treatment_info.get("last_modified", "N/A"))
        write_key_value_right("Last Modified By", treatment_info.get("updated_by", "N/A"))

        pdf.set_x((pdf.w - img_width) / 2)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(60, 8, "Treatment Notes:", ln=1)
        pdf.set_x((pdf.w - img_width) / 2)
        pdf.set_font("Arial", "", 11)
        treatment_note = treatment_info.get("treatment_note", "")
        pdf.multi_cell(img_width, 8, treatment_note if treatment_note else "No treatment note provided.")

    # --- Signature block ---
    if doctor_name and status in ["Confirmed Positive", "Confirmed Negative"]:
        if pdf.get_y() > 230:  # ensure space
            pdf.add_page()
        pdf.ln(20)
        pdf.set_text_color(0, 0, 0)
        # Doctor name
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, doctor_name, ln=1, align="C")
        # Signature line
        line_y = pdf.get_y()
        pdf.line(70, line_y, 140, line_y)
        # Caption
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 10, "Doctor's Signature over Printed Name", ln=1, align="C")

    # --- Disclaimer ---
    pdf.ln(6)
    disclaimer_text = (
        "This report has been automatically generated by the DeteXTB system and is intended solely for "
        "informational purposes. It must not be used to inform or determine any course of medical treatment "
        "without the formal review and signed authorization of a licensed medical practitioner."
    )
    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Arial", "I", 10)
    pdf.multi_cell(0, 7, disclaimer_text, align="J")

    pdf.ln(8)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1, align='R')

    # --- End-of-document marker ---
    pdf.ln(10)
    pdf.set_draw_color(0, 0, 0)
    y = pdf.get_y()
    pdf.line(20, y, 190, y)
    pdf.ln(6)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "--- END OF MEDICAL REPORT ---", ln=1, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, "Nothing follows", ln=1, align="C")

    return bytes(pdf.output(dest="S"))


# Mandaue City Barangays
mandaue_barangays = [
    "Alang-Alang", "Bakilid", "Banilad", "Basak", "Cabancalan", "Cambaro", "Canduman", "Casili",
    "Casuntingan", "Centro (Poblacion)", "Cubacub", "Guizo", "Ibabao-Estancia", "Jagobiao", "Labogon", "Looc", "Maguikay",
    "Mantuyong", "Opao", "Pakna-an", "Pagsabungan", "Subangdaku", "Tabok", "Tawason", "Tingub", "Tipolo", "Umapad"
]

# Mandaue City Barangay Coordinates
mandaue_barangay_coordinates = {
    "Alang-Alang": (10.3315, 123.9453), "Bakilid": (10.3339, 123.9358), "Banilad": (10.3425, 123.9189),
    "Basak": (10.3633, 123.9511), "Cabancalan": (10.3553, 123.9261), "Cambaro": (10.3239, 123.9481),
    "Canduman": (10.3728, 123.9381), "Casili": (10.3833, 123.9333), "Casuntingan": (10.3508, 123.9317),
    "Centro (Poblacion)": (10.3275, 123.9419), "Cubacub": (10.3739, 123.9483), "Guizo": (10.3289, 123.9371),
    "Ibabao-Estancia": (10.3342, 123.9397), "Jagobiao": (10.3681, 123.9567), "Labogon": (10.3533, 123.9619),
    "Looc": (10.3253, 123.9486), "Maguikay": (10.3444, 123.9375), "Mantuyong": (10.3303, 123.9422),
    "Opao": (10.3347, 123.9536), "Pakna-an": (10.3462, 123.9603), "Pagsabungan": (10.3683, 123.9442),
    "Subangdaku": (10.3303, 123.9269), "Tabok": (10.3589, 123.9556), "Tawason": (10.3789, 123.9394),
    "Tingub": (10.3628, 123.9406), "Tipolo": (10.3381, 123.9333),"Umapad": (10.3397, 123.9564)
}

# Mandaue City Population Data (2025 Census) = 388,002
mandaue_barangay_population_2025 = {
        "Alang-Alang": 12251, "Bakilid": 4671, "Banilad": 19594, "Basak": 12554,
        "Cabancalan": 15818, "Cambaro": 9581, "Canduman": 24995, "Casili": 5756,
        "Casuntingan": 17956, "Centro (Poblacion)": 3171, "Cubacub": 14738, "Guizo": 7728,
        "Ibabao-Estancia": 7449, "Jagobiao": 12937, "Labogon": 21811, "Looc": 18536,
        "Maguikay": 15931, "Mantuyong": 5846, "Opao": 12798, "Pagsabungan": 21603,
        "Pakna-an": 32540, "Subangdaku": 18219, "Tabok": 20767, "Tawason": 7440,
        "Tingub": 6479, "Tipolo": 16822, "Umapad": 20011
    }

# Initialize default session state values
def init_edit_state():
    DEFAULT_FIELDS = ["rec_fname", "rec_mname", "rec_lname", "rec_sex", "rec_dob", "rec_phone", "rec_street", "rec_house", "rec_barangay"]
    for field in DEFAULT_FIELDS:
        if field not in st.session_state:
            if field == "rec_dob":
                st.session_state[field] = date(2000, 1, 1)
            elif field == "rec_sex":
                st.session_state[field] = "Male"
            else:
                st.session_state[field] = ""

# Calculate age
def calculate_age(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def has_changes(selected_case):
    """Check if any form fields have been modified"""
    original_values = {
        "rec_fname": selected_case.get("PATIENT_FNAME", ""),
        "rec_mname": selected_case.get("PATIENT_MNAME", ""),
        "rec_lname": selected_case.get("PATIENT_LNAME", ""),
        "rec_sex": selected_case.get("sex", ""),
        "rec_dob": datetime.strptime(selected_case.get("PATIENT_DOB", "2000-01-01"), "%Y-%m-%d").date(),
        "rec_phone": selected_case.get("phone", ""),
        "rec_street": selected_case.get("PATIENT_STREET", ""),
        "rec_house": selected_case.get("PATIENT_HOUSENO", ""),
        "rec_barangay": selected_case.get("PATIENT_BARANGAY", "")
    }
    
    for field, original_value in original_values.items():
        current_value = st.session_state.get(field)
        if str(current_value) != str(original_value):
            return True
    return False

def get_coordinates_from_barangay(barangay_name, show_notification, is_light=True):
    coords = mandaue_barangay_coordinates.get(barangay_name)
    if coords:
        return coords
    else:
        show_notification(f"⚠️ Coordinates for '{barangay_name}' not found.", "warning", is_light=is_light)
        return None, None

def get_age_group(age):
    """Convert numerical age to MAP_AGE_GROUP string format"""
    try:
        age_int = int(age)
        if age_int <= 14:
            return "0-14"
        elif age_int <= 24:
            return "15-24"
        elif age_int <= 64:
            return "25-64"
        else:
            return "65+"
    except (ValueError, TypeError):
        return "Unknown"
  
# Define the page as a function to be used by Home.py
def Records(is_light=True):
    init_edit_state()

    if "light_mode" not in st.session_state:
        st.session_state["light_mode"] = True  # Default theme

    if is_light is None:
        is_light = st.session_state["light_mode"]


    def fetch_cases():
        try:
            result = (
                supabase.table("RESULT_Table")
                .select("""
                    RES_DATE,
                    RES_PRESUMPTIVE,
                    RES_CONF_SCORE,
                    RES_STATUS,
                    CHEST_XRAY_Table(
                        PT_ID,
                        PATIENT_Table(
                            PT_FNAME,
                            PT_MNAME,
                            PT_LNAME,
                            PT_SEX,
                            PT_AGE,
                            PT_DOB,
                            PT_PHONE,
                            PT_HOUSENO,
                            PT_STREET,
                            PT_BRGY,
                            PT_CITY
                        )
                    )
                """)
                .order("RES_DATE", desc=True)
                .limit(1000)
                .execute()
            )

            seen_patients = set()
            latest_cases = []

            for entry in result.data:
                patient_data = entry["CHEST_XRAY_Table"]["PATIENT_Table"]
                pt_id = entry["CHEST_XRAY_Table"]["PT_ID"]

                if pt_id in seen_patients:
                    continue  

                seen_patients.add(pt_id)
                full_name = f"{patient_data['PT_FNAME']} {patient_data['PT_MNAME']} {patient_data['PT_LNAME']}".strip()
                confidence_percent = f"{int(float(entry['RES_CONF_SCORE']) * 100)}%"
                address_parts = [
                    patient_data.get('PT_HOUSENO', ''),
                    patient_data.get('PT_STREET', ''),
                    patient_data.get('PT_BRGY', ''),
                    patient_data.get('PT_CITY', '')
                ]
                full_address = ', '.join([part.strip() for part in address_parts if part and part.strip()])

                latest_cases.append({
                    "pt_id": pt_id,
                    "name": full_name,
                    "date": entry["RES_DATE"],
                    "result": entry["RES_PRESUMPTIVE"],
                    "confidence": confidence_percent,
                    "diagnosis": entry["RES_STATUS"],
                    "age": patient_data.get("PT_AGE", "N/A"),
                    "sex": patient_data.get("PT_SEX", "N/A"),
                    "phone": patient_data.get("PT_PHONE", "N/A"),
                    "address": full_address,
 
                    "PATIENT_FNAME": patient_data.get("PT_FNAME", ""),
                    "PATIENT_MNAME": patient_data.get("PT_MNAME", ""),
                    "PATIENT_LNAME": patient_data.get("PT_LNAME", ""),
                    "PATIENT_SEX": patient_data.get("PT_SEX",""),
                    "PATIENT_AGE": patient_data.get("PT_AGE", ""),
                    "PATIENT_DOB": patient_data.get("PT_DOB", "2000-01-01"),
                    "PATIENT_HOUSENO": patient_data.get("PT_HOUSENO", ""),
                    "PATIENT_STREET": patient_data.get("PT_STREET", ""),
                    "PATIENT_BARANGAY": patient_data.get("PT_BRGY", ""),
                    "PATIENT_CITY": patient_data.get("PT_CITY", ""),
                    "PATIENT_PHONE": patient_data.get("PT_PHONE", ""),
                    "PATIENT_COUNTRY":patient_data.get("PT_COUNTRY", ""),
                    "PATIENT_PROVINCE": patient_data.get("PT_PROVINCE", ""),
                })

            return latest_cases

        except Exception as e:
            show_notification(f"Error loading patient results: {e}", "error")
            return []

    cases = fetch_cases()

    all_dates = [datetime.fromisoformat(c["date"]).date() for c in cases]
    oldest_date = min(all_dates) if all_dates else date.today()


    # ---------------- Reset Trigger Handler ----------------
    if "reset_triggered" not in st.session_state:
        st.session_state["reset_triggered"] = False

    if st.session_state.reset_triggered:
        st.session_state["search_bar_records"] = ""
        st.session_state["records_status_filter"] = "All"
        st.session_state["records_presumptive_filter"] = "All"
        st.session_state["records_date_from"] = oldest_date
        st.session_state["records_date_to"] = date.today()
        st.session_state["records_page_num"] = 1
        st.session_state["reset_triggered"] = False  # Clear flag

    # Initialize all filter values before any UI access
    if "search_bar_records" not in st.session_state:
        st.session_state["search_bar_records"] = ""

    if "records_status_filter" not in st.session_state:
        st.session_state["records_status_filter"] = "All"

    if "records_presumptive_filter" not in st.session_state:
        st.session_state["records_presumptive_filter"] = "All"

    if "records_date_from" not in st.session_state:
        st.session_state["records_date_from"] = oldest_date
        
    if "records_date_to" not in st.session_state:
        st.session_state["records_date_to"] = date.today()

    if "diagnoses" not in st.session_state:
        st.session_state["diagnoses"] = {f"diagnosis_{i}": case["diagnosis"] for i, case in enumerate(cases)}

    if "records_page_num" not in st.session_state:
        st.session_state["records_page_num"] = 1

    # Ensure view mode is initialized
    if "view_mode" not in st.session_state:
        st.session_state["view_mode"] = False

    if "selected_case" not in st.session_state:
        st.session_state["selected_case"] = None

    cases_per_page = 10

    def apply_filters():
        filtered = cases
        query = st.session_state["search_bar_records"].strip().lower()
        if query:
            # Search in both patient name and patient ID
            filtered = [
                c for c in filtered 
                if (query in c["name"].lower() or 
                    query in c["pt_id"].lower() or  
                    query in str(c["pt_id"]).lower()) 
            ]

        if st.session_state["records_status_filter"] != "All":
            filtered = [c for c in filtered if c["diagnosis"] == st.session_state["records_status_filter"]]

        if st.session_state["records_presumptive_filter"] != "All":
            target = "Positive" if st.session_state["records_presumptive_filter"] == "Positive" else "Negative"
            filtered = [c for c in filtered if c["result"] == target]

        if st.session_state["records_date_from"]:
            filtered = [c for c in filtered if datetime.fromisoformat(c["date"]).date() >= st.session_state["records_date_from"]]

        if st.session_state["records_date_to"]:
            filtered = [c for c in filtered if datetime.fromisoformat(c["date"]).date() <= st.session_state["records_date_to"]]

        return filtered

    # Pagination controls
    def pagination_controls(position, total_pages):
        col1, col2, col3 = st.columns([1, 7, 1])
        with col1:
            if st.session_state.records_page_num > 1:
                if st.button("Previous", key=f"prev_{position}"):
                    st.session_state.records_page_num -= 1
                    st.rerun()
        with col2:
            st.markdown(f"<div style='text-align: center; font-weight: bold;'>Page {st.session_state.records_page_num} of {total_pages}</div>", unsafe_allow_html=True)
        with col3:
            if st.session_state.records_page_num < total_pages:
                if st.button("Next", key=f"next_{position}"):
                    st.session_state.records_page_num += 1
                    st.rerun()

    # Fetches additional metadata for X-ray from Supabase
    def fetch_xray_metadata(image_path):
        """Fetch additional metadata for X-ray: uploader, confirming doctor, dates"""
        try:
            metadata = {
                "uploader_name": None,
                "confirming_doctor": None,
                "confirmed_at": None,
                "updated_at": None
            }
            
            # Get CXR_ID and USER_ID (uploader) from CHEST_XRAY_Table
            cxr_res = (
                supabase.table("CHEST_XRAY_Table")
                .select("CXR_ID, USER_ID")
                .eq("CXR_FILE_PATH", image_path)
                .single()
                .execute()
            )
            
            if not cxr_res.data:
                return metadata
                
            cxr_id = cxr_res.data.get("CXR_ID")
            uploader_id = cxr_res.data.get("USER_ID")
            
            # Get uploader's name from USER_Table
            if uploader_id:
                uploader_res = (
                    supabase.table("USER_Table")
                    .select("USER_FNAME, USER_MNAME, USER_LNAME")
                    .eq("USER_ID", uploader_id)
                    .single()
                    .execute()
                )
                
                if uploader_res.data:
                    fname = uploader_res.data.get("USER_FNAME", "")
                    mname = uploader_res.data.get("USER_MNAME", "")
                    lname = uploader_res.data.get("USER_LNAME", "")
                    
                    # Build full name
                    name_parts = [fname]
                    if mname:
                        name_parts.append(mname)
                    name_parts.append(lname)
                    metadata["uploader_name"] = " ".join(name_parts)
            
            # Get diagnosis information (confirming doctor and dates)
            diagnosis_res = (
                supabase.table("DIAGNOSIS_Table")
                .select("USER_ID, DX_CONFIRMED_AT, DX_UPDATED_AT, DX_STATUS")
                .eq("CXR_ID", cxr_id)
                .order("DX_UPDATED_AT", desc=True)
                .limit(1)
                .execute()
            )
            
            if diagnosis_res.data:
                diag_data = diagnosis_res.data[0]
                metadata["confirmed_at"] = diag_data.get("DX_CONFIRMED_AT")
                metadata["updated_at"] = diag_data.get("DX_UPDATED_AT")
                
                # Get confirming doctor's name if status is confirmed
                dx_status = diag_data.get("DX_STATUS", "")
                confirming_user_id = diag_data.get("USER_ID")
                
                if confirming_user_id and dx_status in ["Confirmed Positive", "Confirmed Negative"]:
                    doctor_res = (
                        supabase.table("USER_Table")
                        .select("USER_FNAME, USER_MNAME, USER_LNAME")
                        .eq("USER_ID", confirming_user_id)
                        .single()
                        .execute()
                    )
                    
                    if doctor_res.data:
                        fname = doctor_res.data.get("USER_FNAME", "")
                        mname = doctor_res.data.get("USER_MNAME", "")
                        lname = doctor_res.data.get("USER_LNAME", "")
                        
                        # Build name with Dr. title
                        name_parts = ["Dr.", fname]
                        if mname:
                            name_parts.append(mname)
                        name_parts.append(lname)
                        metadata["confirming_doctor"] = " ".join(name_parts)
            
            return metadata
            
        except Exception as e:
            print(f"Error fetching X-ray metadata: {e}")
            return {
                "uploader_name": None,
                "confirming_doctor": None,
                "confirmed_at": None,
                "updated_at": None
            }

    # Fetches the doctor's name from USER_Table via DIAGNOSIS_Table
    def fetch_doctor_name(image_path):
        """Fetch the doctor's name who confirmed the diagnosis"""
        try:
            # Get CXR_ID from image path
            cxr_res = (
                supabase.table("CHEST_XRAY_Table")
                .select("CXR_ID")
                .eq("CXR_FILE_PATH", image_path)
                .single()
                .execute()
            )
            
            if not cxr_res.data:
                return None
                
            cxr_id = cxr_res.data.get("CXR_ID")
            
            # Get USER_ID from DIAGNOSIS_Table
            diagnosis_res = (
                supabase.table("DIAGNOSIS_Table")
                .select("USER_ID")
                .eq("CXR_ID", cxr_id)
                .order("DX_UPDATED_AT", desc=True)
                .limit(1)
                .execute()
            )
            
            if not diagnosis_res.data:
                return None
                
            user_id = diagnosis_res.data[0].get("USER_ID")
            
            if not user_id:
                return None
            
            # Get doctor's name from USER_Table
            user_res = (
                supabase.table("USER_Table")
                .select("USER_FNAME, USER_MNAME, USER_LNAME")
                .eq("USER_ID", user_id)
                .single()
                .execute()
            )
            
            if not user_res.data:
                return None
            
            # Build full name with "Dr." title
            fname = user_res.data.get("USER_FNAME", "")
            mname = user_res.data.get("USER_MNAME", "")
            lname = user_res.data.get("USER_LNAME", "")
            
            # Build name: Dr. FirstName MiddleName(if exists) LastName
            name_parts = ["Dr.", fname]
            if mname:
                name_parts.append(mname)
            name_parts.append(lname)
            
            return " ".join(name_parts)
            
        except Exception as e:
            print(f"Error fetching doctor name: {e}")
            return None

    # Valid chest x-ray validation (stricter)
    def is_xray_like(img):
        """
            Stricter heuristic to check if an image looks like a chest X-ray.
            - Must be grayscale-like (R≈G≈B)
            - Must have sufficient contrast and detail
            - Must have rib-like edge density
            - Must have near-square aspect ratio
            - Must have brighter center (lungs) than edges
        """
        # Convert to NumPy array (RGB)
        img_array = np.array(img)

        # Channel similarity check
        r, g, b = img_array[..., 0], img_array[..., 1], img_array[..., 2]
        mean_diff = (np.abs(r - g) + np.abs(r - b) + np.abs(g - b)).mean()

        # Convert to grayscale
        gray = np.mean(img_array, axis=-1)

        # Aspect ratio filter
        h, w = gray.shape
        aspect_ratio = w / h
        if not (0.7 <= aspect_ratio <= 1.3):
            return False

        # Contrast and entropy
        intensity_range = gray.max() - gray.min()
        contrast_std = gray.std()
        hist, _ = np.histogram(gray, bins=256, range=(0, 255), density=True)
        hist += 1e-8
        entropy = -np.sum(hist * np.log2(hist))

        # Edge density (rib cage usually creates many edges)
        edges = filters.sobel(gray)
        edge_density = (edges > 0.05).mean()

        # Center brightness
        h_mid, w_mid = h // 2, w // 2
        center_region = gray[h_mid-50:h_mid+50, w_mid-50:w_mid+50]
        center_brightness = np.mean(center_region)

        # Decision rules
        is_grayscale = mean_diff < 8
        has_contrast = intensity_range > 80
        has_detail = entropy > 5.0 and contrast_std > 40
        rib_like_edges = edge_density > 0.1
        bright_center = center_brightness > np.mean(gray)  # lungs lighter than edges

        return all([is_grayscale, has_contrast, has_detail, rib_like_edges, bright_center])

    # Valid chest x-ray validation (lighter)
    def is_xray_like_relaxed(img):
        """
            Relaxed heuristic to allow more chest X-ray images that might fail strict checks.
            Thresholds and ranges are looser compared to is_xray_like.
        """
        # Convert to NumPy array (RGB)
        img_array = np.array(img)

        # Channel similarity check
        r, g, b = img_array[..., 0], img_array[..., 1], img_array[..., 2]
        mean_diff = (np.abs(r - g) + np.abs(r - b) + np.abs(g - b)).mean()

        # Convert to grayscale
        gray = np.mean(img_array, axis=-1)

        # Aspect ratio filter (wider range)
        h, w = gray.shape
        aspect_ratio = w / h
        if not (0.6 <= aspect_ratio <= 1.4):
            return False

        # Contrast and entropy (lower thresholds)
        intensity_range = gray.max() - gray.min()
        contrast_std = gray.std()
        hist, _ = np.histogram(gray, bins=256, range=(0, 255), density=True)
        hist += 1e-8
        entropy = -np.sum(hist * np.log2(hist))

        # Edge density (rib cage)
        edges = filters.sobel(gray)
        edge_density = (edges > 0.05).mean()

        # Center brightness
        h_mid, w_mid = h // 2, w // 2
        center_region = gray[h_mid-50:h_mid+50, w_mid-50:w_mid+50]
        center_brightness = np.mean(center_region)

        # Relaxed decision rules
        is_grayscale = mean_diff < 15            # relaxed from 8
        has_contrast = intensity_range > 50      # relaxed from 80
        has_detail = entropy > 4.0 and contrast_std > 30  # relaxed from 5.0 and 40
        rib_like_edges = edge_density > 0.05     # relaxed from 0.1
        bright_center = center_brightness >= np.mean(gray)  # allow equal

        return all([is_grayscale, has_contrast, has_detail, rib_like_edges, bright_center])

    # Preprocess X-ray for prediction
    def preprocess_xray(uploaded_file):
        img = Image.open(uploaded_file).convert('RGB')
        img = img.resize(IMG_SIZE)
        img_array = keras_image.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        return img_array

    # Predict TB using model
    def predict_tb(uploaded_file):
        xray_array = preprocess_xray(uploaded_file)
        preds = model.predict(xray_array)[0][0]
        confidence = int((preds if preds > 0.5 else 1 - preds)* 100)
        label = "Positive" if preds > 0.5 else "Negative"
        return label, confidence

    def tooltip_html(date_str, tooltip_text):
        return f"""
        <span class="xrayinfo-tooltip-wrapper">
            <strong>{date_str}</strong>
            <span class="xrayinfo-tooltip-text">{tooltip_text}</span>
            <span class="xrayinfo-tooltip-icon">?</span>
        </span>
        """

    # Store x-ray
    def save_xray_to_supabase(patient_id, image_bytes, file_name, ai_result, show_notification, is_light=True):
        try:
            if not image_bytes:
                show_notification("No X-ray file found to save.", "error", is_light=is_light)
                return False

            # 1. Prepare storage path 
            selected_case = st.session_state.get("selected_case", {})
            fname = selected_case.get("PATIENT_FNAME", "")
            mname = selected_case.get("PATIENT_MNAME", "")
            lname = selected_case.get("PATIENT_LNAME", "")
            
            full_name_raw = f"{fname} {mname} {lname}"
            full_name_clean = full_name_raw.strip().upper().replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{full_name_clean}_{timestamp}.png"
            storage_path = f"patient_{patient_id}/{filename}"

            # 2. Upload to Supabase Storage
            try:
                supabase.storage.from_("xray-uploads").list()  # check bucket
            except Exception:
                show_notification("X-ray storage bucket not accessible. Please check configuration.", "error", is_light=is_light)
                return False

            upload_response = supabase.storage.from_("xray-uploads").upload(
                storage_path,
                image_bytes,
                {"content-type": "image/png"}
            )

            if not upload_response:
                show_notification("Failed to upload X-ray image to storage.", "error", is_light=is_light)
                return False

            # 3. Build public URL
            SUPABASE_URL = "https://xaxgkufwhemjoofcvtri.supabase.co"
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/xray-uploads/{storage_path}"

            # 4. Insert into CHEST_XRAY_Table
            cxr_res = supabase.table("CHEST_XRAY_Table").insert({
                "CXR_FILE_PATH": public_url,
                "CXR_UPL_DATE": datetime.now().isoformat(),
                "PT_ID": patient_id,
                "USER_ID": st.session_state.get("USER_ID")
            }).execute()

            if not cxr_res.data:
                show_notification("Failed to create X-ray record.", "error", is_light=is_light)
                return False

            cxr_id = cxr_res.data[0]["CXR_ID"]
            st.session_state["CXR_ID"] = cxr_id

            # 5. Insert into RESULT_Table
            label, confidence = ai_result.values()
            result_res = supabase.table("RESULT_Table").insert({
                "CXR_ID": cxr_id,
                "RES_PRESUMPTIVE": label,
                "RES_CONF_SCORE": confidence / 100,
                "RES_DATE": datetime.now().isoformat(),
                "RES_STATUS": "Pending"
            }).execute()

            if not result_res.data:
                show_notification("Failed to create analysis result record.", "error", is_light=is_light)
                return False
            
            return True

        except Exception as e:
            show_notification(f"Error saving X-ray data: {str(e)}", "error", is_light=is_light)
            return False
      

    # ------------------- Layout -------------------

    # --- Theme Toggle UI ---
    col_title, col_toggle = st.columns([6, 1])
    with col_title:
        st.markdown("<h4>Patient Records</h4>", unsafe_allow_html=True)
    with col_toggle:
        new_toggle = st.toggle("🌙", value=is_light, key="theme_toggle", label_visibility="collapsed")

    if new_toggle != st.session_state["light_mode"]:
        st.session_state["light_mode"] = new_toggle
        st.rerun()

    is_light = st.session_state["light_mode"]

    # ------------------- Theme-based color variables -------------------
    bg_color = "white" if is_light else "#0e0e0e"
    text_color = "black" if is_light else "white"
    header_color = "#1c1c1c" if is_light else "white"
    input_bg = "white" if is_light else "#1a1a1a"
    input_border = "black" if is_light else "white"
    placeholder_color = "#b0b0b0" if is_light else "#cccccc"
    select_bg = "white" if is_light else "#1a1a1a"
    select_hover = "#f0f0f0" if is_light else "#2a2a2a"
    calendar_dropdown_bg = "white" if is_light else "#222"
    calendar_border = "black" if is_light else "none"
    button_color = "#d32f2f"
    button_hover = "#f3a5a5"
    card_bg = "#f0f0f5" if is_light else "#1c1c1c"
    filtered_case_bg_color = "#ffe6e8" if is_light else "#6c0019"
    filtered_case_text = "#c4751a" if is_light else "#deb364"
    filtered_case_border = "#ebc68f" if is_light else "#7E6A23"
    total_cases_bg_color = "#ffe6e8" if is_light else "#6c0019"
    total_cases_text = "#ff1818" if is_light else "#fab4bc"
    total_cases_border = "#ff9191" if is_light else "#8f0700"
    theme_class = "light" if is_light else "dark"

    notification_container = st.empty()
    
    def show_notification(message, type="info", duration=4, is_light=None):  
        bg_colors = {
            "success": "#e8f5e9" if is_light else "#1b5e20",
            "error": "#ffebee" if is_light else "#b71c1c",
            "info": "#e3f2fd" if is_light else "#0d47a1",
            "warning": "#fff3e0" if is_light else "#ef6c00"
        }
        text_color = "#000000" if is_light else "white"
        icon = {
            "success": "✅",
            "error": "❌",
            "info": "ℹ️",
            "warning": "⚠️"
        }.get(type, "")

        with notification_container:
            st.markdown(f"""
            <div class="notification-container">
                <div class="notification notification-{type}">
                    <span class="notification-icon">{icon}</span> {message}
                </div>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(duration)
            notification_container.empty()

    st.markdown(f"""
    <style>
    html, body, [class*="css"] {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
        font-family: 'Arial', sans-serif;
    }}

    [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
            background-color: {bg_color} !important;
            color: {text_color} !important;
        }}

    label {{
        color: {text_color} !important;
        font-weight: 600;
    }}


    h1, h2, h3, h4, h5, h6 {{ color: {header_color} !important; }}
        html, body, [class*="css"] {{
        color: {header_color} !important;
        font-family: 'Arial', sans-serif;
        }}

    .stTextInput > div {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 25px !important;
        
    }}


    .stTextInput input {{
        background-color: {input_bg} !important;       
        color: {text_color} !important;
        caret-color: {"black" if is_light else "white"} !important;
    }}

    .stTextInput > div > div > input {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        padding-left: 10px !important;
    }}

    .stTextInput input::placeholder {{
        color: {placeholder_color} !important;
    }}

    div.stTextInput > div > div > div[data-testid="InputInstructions"],
        [data-testid="InputInstructions"] {{
            display: none !important;
        }}

    /* Date input */
    div[data-testid="stDateInput"] > div {{
        background-color: {input_bg} !important;
        border-radius: 25px !important;
        border: 1px solid {input_border} !important;
        padding: 0 10px !important;
    }}

    div[data-testid="stDateInput"] > div > div {{
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}

    div[data-testid="stDateInput"] input {{
        background-color: {input_bg} !important;
        border: none !important;
        color: {text_color} !important;
        padding: 8px 0 !important;
    }}

    div[data-testid="stDateInput"] svg {{
        color: {text_color} !important;
    }}

       div[data-testid="stDateInput"] > div:focus-within {{
        box-shadow: none !important;
    }}

    .stSelectbox div[data-baseweb="select"] > div {{
        background-color: {select_bg} !important;
        color: {text_color} !important;
        border: 1px solid {input_border} !important;
        border-radius: 25px !important;
    }}

    .stSelectbox li:hover {{
        background-color: {select_hover} !important;
    }}

    /* Make selectbox label invisible */
            .stSelectbox label {{
                display: none !important;
            }}

    .block-container {{
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }}

    .cases-table thead tr {{
        background-color: {calendar_dropdown_bg};
        color: {text_color};
    }}

    .cases-table th, .cases-table td {{
        border-bottom: 1px solid {calendar_border};
    }}

    .patient-info-card.light {{
        background-color: {card_bg};
        color: {text_color};
        padding: 20px;
        border-radius: 25px;
        margin-top: 20px;
        margin-bottom: 10px;
    }}

    .patient-info-card.dark {{
        background-color: {card_bg};
        color: {text_color};
        padding: 20px;
        border-radius: 25px;
        margin-top: 20px;
        margin-bottom: 10px;
    }}

    
    div[data-testid="stFileUploader"] {{
            background-color: transparent;
            padding: 10px;
            border-radius: 15px;
            border: none;
        }}

        div[data-testid="stFileUploader"] section {{
            background-color: transparent;
            border: 2px dashed {"#cccccc" if is_light else "#666666"};
            border-radius: 10px;
        }}

        div[data-testid="stFileUploader"] *,
        div[data-testid="stFileUploader"] > label {{
            color: {text_color} !important;
        }}

        div[data-testid="stFileUploader"] button:not(:has(svg)) {{
            background-color: {button_color} !important;
            color: white !important;
            border: none !important;
        }}

        div[data-testid="stFileUploader"] button:not(:has(svg)):hover,
        div[data-testid="stFileUploader"] button:not(:has(svg)):focus,
        div[data-testid="stFileUploader"] button:not(:has(svg)):active {{
            background-color: {button_hover} !important;
            color: white !important;
            border: none !important;
            outline: none !important;
        }}

        div[data-testid="stFileUploader"] button:has(svg) {{
            background-color: transparent !important;
            color: {text_color} !important;
            border: none !important;
            box-shadow: none !important;
        }}

        div[data-testid="stFileUploader"] button:has(svg):hover {{
            color: {button_color} !important;
        }}

    
    /* Buttons */
            
    /* 1. Reset filters button in the main table */
    [class*="st-key-reset_filters"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-reset_filters"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}
    /*[class*="st-key-reset_filters"] button:active {{
        background-color: #3357FF !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}*/

    /* 2. View button in the main table */
    [class*="st-key-view_"]:not([class*="view_mode"]) button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-view_"]:not([class*="view_mode"]) button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 3. Pagination controls in the main table */
    [class*="st-key-prev_"] button {{
        background-color: {button_color}  !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-prev_"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}
    [class*="st-key-next_"] button {{
        background-color: {button_color}  !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-next_"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 4. Back button in the patient-specific view */
    [class*="st-key-back"] button {{
        background-color: {button_color}  !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-back"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 5. Edit info button in the patient-specific view */
    [class*="st-key-edit_patient_btn"] button {{
        background-color: {button_color}  !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-edit_patient_btn"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 6. Add X-ray button in the patient-specific view */
    [class*="st-key-add_xray_btn"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-add_xray_btn"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 7. Reset filters button in the patient-specific view */
    [class*="st-key-reset_filters_view"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-reset_filters_view"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 8. View button in the patient-specific view */
    [class*="st-key-image_view_"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-image_view_"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 9. Pagination controls in the patient-specific view */
    [class*="st-key-view_prev"] button,
    [class*="st-key-view_next"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-view_prev"] button:hover,
    [class*="st-key-view_next"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 10. Cancel button in the edit info mode */
    [class*="st-key-cancel_edit_button"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-cancel_edit_button"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 11. Save button in the edit info mode */
    [class*="st-key-trigger_save_edit"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-trigger_save_edit"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 12. Yes/No buttons in the edit info mode */
    [class*="st-key-cancel_yes"] button,
    [class*="st-key-cancel_no"] button,
    [class*="st-key-save_yes"] button,
    [class*="st-key-save_no"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-cancel_yes"] button:hover,
    [class*="st-key-cancel_no"] button:hover,
    [class*="st-key-save_yes"] button:hover,
    [class*="st-key-save_no"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 13. Step 1 cancel button in the add X-ray mode */
    [class*="st-key-records_step2_cancel"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-records_step2_cancel"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 14. Step 1 next button in the add X-ray mode */
    [class*="st-key-records_step2_next"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-records_step2_next"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 15. Step 2 cancel button in the add X-ray mode */
    [class*="st-key-records_step3_cancel"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-records_step3_cancel"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 16. Step 3 next button in the add X-ray mode */
    [class*="st-key-records_step3_next"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-records_step3_next"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 17. Step 3 reupload button in the add X-ray mode */
    [class*="st-key-records_step3_reupload"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-records_step3_reupload"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 18. Step 4 back button in the add X-ray mode */
    [class*="st-key-records_step4_back"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-records_step4_back"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 19. Step 4 save button in the add X-ray mode */
    [class*="st-key-records_step4_save"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-records_step4_save"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 20. Yes/No buttons in the add X-ray mode */
    [class*="st-key-records_cancel_yes"] button,
    [class*="st-key-records_cancel_no"] button,
    [class*="st-key-records_cancel_step3_yes"] button,
    [class*="st-key-records_cancel_step3_no"] button,
    [class*="st-key-records_save_xray_yes"] button,
    [class*="st-key-records_save_xray_no"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-records_cancel_yes"] button:hover,
    [class*="st-key-records_cancel_no"] button:hover,
    [class*="st-key-records_cancel_step3_yes"] button:hover,
    [class*="st-key-records_cancel_step3_no"] button:hover,
    [class*="st-key-records_save_xray_yes"] button:hover,
    [class*="st-key-records_save_xray_no"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 21. Back button in the view X-ray in the patient-specific view */
    [class*="st-key-view_image_back"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}
    [class*="st-key-view_image_back"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 22. Download button in the view X-ray in the patient-specific view */
    div.stDownloadButton > button {{
        background-color: {button_color} !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 8px 20px !important;
        cursor: pointer !important;
        font-size: 1rem !important;
        width: 200px !important;
        white-space: nowrap !important;
        margin-left: 8px !important;
        transition: background-color 0.3s ease !important;
    }}
    div.stDownloadButton > button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

    /* 23. Segmented controls - separate styling */
    /*[class*="st-key-view_mode"] button {{
        background-color: {button_color} !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.5em 1.5em !important;
        font-weight: bold !important;
        transition: background-color 0.3s ease;
        cursor: pointer !important;
    }}*/
    /*[class*="st-key-view_mode"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}*/
    /*[class*="st-key-view_mode"] button:active {{
        background-color: #FF9A00 !important;
        color: white !important;
    }}*/

    .note-container {{
            background-color: {card_bg} !important;
            padding: 25px;
            border-radius: 15px;
            margin-top: 20px;
            color: {"black" if is_light else "white"};
        }}
    input:disabled,
            .stTextInput input:disabled,
            div[data-testid="stTextInput"] input[disabled] {{
                background-color: {"white" if is_light else "#1a1a1a"} !important;
                color: {"black" if is_light else "white"} !important;
                opacity: 1 !important;
                -webkit-text-fill-color: {"black" if is_light else "white"} !important; /* <-- for Safari */
                }}

        .stAlert {{
            color: {"black" if is_light else "white"} !important;
            border-radius: 6px;
            padding: 1rem;
            }}

        .stAlert p, .stAlert strong {{
            color: {"black" if is_light else "white"} !important;
            font-weight: 500;
        }}
        /* Notification styles - removed left border */
        .notification-container {{
            position: fixed;
            top: 30px;
            left: 60%;
            transform: translateX(-50%);
            width: 400px;
            z-index: 1000;
        }}

        .notification {{
            padding: 8px 12px;
            margin-bottom: 8px;
            border-radius: 4px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease-out;
        }}

        .notification-icon {{
            margin-right: 8px;
            font-size: 1rem;
        }}

        .notification-success {{
            background-color: #e8f5e9 !important;
            color: #000000 !important;
        }}
        .notification-error {{
            background-color: #ffebee !important;
            color: #000000 !important;
        }}
        .notification-info {{
            background-color: #e3f2fd !important;
            color: #000000 !important;
        }}
        .notification-warning {{
            background-color: #fff3e0 !important;
            color: #000000 !important;
        }}
        .custom-warning, .custom-info {{
            background-color: {'#fff9d0' if st.session_state['light_mode'] else '#332d04'} !important;
            color: {'#bd2f2f' if st.session_state['light_mode'] else '#ea7b64'} !important;
            border-left: 6px solid {'#FFC107' if st.session_state['light_mode'] else '#bead79'} !important;
            padding: 10px 15px !important;
            border-radius: 4px !important ;
            margin-bottom: 13px !important;
            font-weight: semibold !important;
        }}

        .ai-result-container {{
            background-color: {card_bg} !important;
            padding: 25px;
            border-radius: 15px;
            margin-top: 20px;
            color: {"black" if is_light else "white"};
            margin-bottom: 20px;
            
        }}

        .ai-result-container h5,
        .ai-result-container p {{
             color: {"black" if is_light else "white"};
        }}

        .step-container {{
            background-color: {"#D9D9D9" if is_light else "black"};
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            font-weight: bold;
            color: {"black" if is_light else "white"};
            border-radius: 10px;
            position: relative;
        }}
        .step {{
            display: flex;
            flex-direction: column;
            align-items: center;
            flex: 1;
            z-index: 2;
        }}
        .step span.number {{
            background-color: #ff0000;
            color: white;
            padding: 4px 12px;
            border-radius: 70%;
            margin-bottom: 5px;
        }}
        .step span.label {{
            color: #ff0000;
        }}
        .step.inactive span.number {{
            background-color: #990000;
            opacity: 0.9;
            color: gray;
        }}
        .step.inactive span.label {{
            color: #990000;
            opacity: 0.9;
        }}
        .step-line {{
            position: absolute;
            top: 20px;
            left: 16%;
            right: 16%;
            height: 1px;
            background-color: #990000;
            z-index: 1;
            opacity: 0.9;
        }}

        .highlight-red {{
            color: #f44336;
        }}

        .highlight-green {{
            color: #4caf50;
        }}

        .highlight-orange {{
            color: #e6af0a;
        }}

        .highlight-blue {{
            color: #2196F3;
        }}
        .highlight-purple {{
            color: #9C27B0;
        }}
        .highlight-gray {{
            color: #607D8B;
        }}

        /* Custom Tooltip Styles in the Main */
        .tooltip-wrapper {{
            position: relative;
            display: inline-block;
            cursor: help;
        }}

        .tooltip-wrapper .tooltip-text {{
            visibility: hidden;
            width: 250px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 10px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -123px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 14px;
            line-height: 1.4;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            pointer-events: none;
        }}

        .tooltip-wrapper .tooltip-text::after {{
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #333 transparent transparent transparent;
        }}

        .tooltip-wrapper:hover .tooltip-text {{
            visibility: visible;
            opacity: 1;
        }}

        .tooltip-icon {{
            display: inline-block;
            margin-left: 5px;
            margin-top: 2px; 
            width: 18px;
            height: 18px;
            background-color: #E53935;
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 18px;
            font-size: 12px;
            font-weight: bold;
            cursor: help;
        }}

        /* Custom Tooltip Styles for the X-Ray Info Dates */
        .xrayinfo-tooltip-wrapper {{
            position: relative;
            display: inline-block;
            margin-left: 5px;
            vertical-align: middle;
        }}

        .xrayinfo-tooltip-wrapper .xrayinfo-tooltip-text {{
            visibility: hidden;
            width: 200px;
            height: auto;
            background-color: #444;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 10px;
            position: absolute;
            z-index: 10;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 14px;
            line-height: 1.4;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            pointer-events: none;
        }}

        .xrayinfo-tooltip-wrapper .xrayinfo-tooltip-text::after {{
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #444 transparent transparent transparent;
        }}

        .xrayinfo-tooltip-wrapper:hover .xrayinfo-tooltip-text {{
            visibility: visible;
            opacity: 1;
        }}

        .xrayinfo-tooltip-icon {{
            display: inline-block;
            width: 18px;
            height: 18px;
            background-color: #E53935;
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 18px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 5px;
            cursor: help;
        }}

    </style>
    """, unsafe_allow_html=True)

    def validate_edit():
        errors = []

        # Friendly field labels
        field_labels = {
            "rec_fname": "First Name",
            "rec_mname": "Middle Name",
            "rec_lname": "Last Name",
            "rec_sex": "Sex",
            "rec_dob": "Date of Birth",
            "rec_phone": "Phone Number",
            "rec_street": "Street",
            "rec_house": "House Number"
        }

        required_fields = ["rec_fname", "rec_lname", "rec_sex", "rec_dob", "rec_phone", "rec_street", "rec_house"]

        name_pattern = re.compile(r"^[A-Za-z\s\-']+$")

        # Step 1: Check required fields
        for field in required_fields:
            value = st.session_state.get(field, "")
            if isinstance(value, str):
                value = value.strip()
            if not value:
                errors.append(f"{field_labels[field]} is required")

        # Step 2: Validate name fields
        def validate_name(field_name, required=True):
            value = st.session_state.get(field_name, "")
            if isinstance(value, str):
                value = value.strip()

            # Always validate if there is any input
            if value:
                if not name_pattern.fullmatch(value):
                    errors.append(f"{field_labels[field_name]} contains invalid characters")
                else:
                    st.session_state[field_name] = value.title()
            elif required:
                errors.append(f"{field_labels[field_name]} is required")

        validate_name("rec_fname", required=True)
        validate_name("rec_lname", required=True)
        validate_name("rec_mname", required=False)

        # Step 3: Validate phone
        phone = str(st.session_state.get("rec_phone", "")).strip()
        if phone:
            if len(phone) != 11 or not phone.startswith("09") or not phone.isdigit():
                errors.append("Phone Number must be 11 digits and start with '09'")
            else:
                st.session_state["rec_phone"] = phone
        else:
            errors.append("Phone Number is required")

        # Step 4: Clean up street input
        street = st.session_state.get("rec_street", "")
        if street:
            st.session_state["rec_street"] = street.strip().title()

        # Step 5: Validate house number
        house = st.session_state.get("rec_house", "")
        if house:
            if not str(house).isdigit():
                errors.append("House Number must be numeric")
        else:
            errors.append("House Number is required")

        # Final error check
        if errors:
            show_notification("Please check the following fields:\n- " + "\n- ".join(errors), "error")
            return False

        return True


    # Top bar (top row)
    col_back, col_spacer, col_edit, col_tooltip, col_add_xray = st.columns([1, 5, 1, 0.2, 1])

    with col_back:
        if (
            st.session_state.view_mode
            and not st.session_state.get("view_image_mode", False)
            and not st.session_state.get("edit_patient_mode", False)
            and not st.session_state.get("add_xray_mode", False)
        ):
            if st.button("Back", key="back"):
                st.session_state.view_mode = False
                st.session_state.selected_case = None
                st.session_state.view_page_num = 1
                st.session_state.view_image_mode = False
                st.session_state.image_path = None
                st.session_state["edit_patient_mode"] = False
                for key in [
                    "rec_fname", "rec_mname", "rec_lname", "rec_sex",
                    "rec_dob", "rec_phone", "rec_street", "rec_house", "rec_barangay"
                ]:
                    st.session_state.pop(key, None)
                st.rerun()

    with col_edit:
        if (
            st.session_state.view_mode
            and not st.session_state.get("view_image_mode", False)
            and not st.session_state.get("edit_patient_mode", False)
            and not st.session_state.get("add_xray_mode", False)
        ):
            if st.button("Edit Info", key="edit_patient_btn"):
                st.session_state["edit_patient_mode"] = True
                st.rerun()

    with col_tooltip:
        if (
            st.session_state.view_mode
            and not st.session_state.get("view_image_mode", False)
            and not st.session_state.get("edit_patient_mode", False)
            and not st.session_state.get("add_xray_mode", False)
        ):
            st.markdown("""
                <div class="tooltip-wrapper" style="margin-top: 8px;">
                    <span class="tooltip-icon">?</span>
                    <span class="tooltip-text">
                        Follow-up X-rays are often scheduled<br> 
                        every 6 months, but actual timing<br>
                        depends on physician assessment.
                    </span>
                </div>
            """, unsafe_allow_html=True)

    with col_add_xray:
        if (
            st.session_state.view_mode
            and not st.session_state.get("view_image_mode", False)
            and not st.session_state.get("edit_patient_mode", False)
            and not st.session_state.get("add_xray_mode", False)
        ):
            if st.button("Add X-ray", key="add_xray_btn"):
                # First check if we have a selected patient 
                if "selected_case" not in st.session_state or not st.session_state.selected_case:
                    show_notification("No patient selected", "error")
                else:
                    selected = st.session_state.selected_case
                    # Check for pending results before proceeding
                    pending_check = (
                        supabase.table("RESULT_Table")
                        .select("""
                            RES_DATE,
                            RES_STATUS,
                            CHEST_XRAY_Table!inner(
                                CXR_ID,
                                PT_ID
                            )
                        """)
                        .eq("CHEST_XRAY_Table.PT_ID", selected["pt_id"])
                        .eq("RES_STATUS", "Pending")
                        .execute()
                    )
                    
                    if pending_check.data and len(pending_check.data) > 0:
                        latest_pending = pending_check.data[0]
                        pending_date = latest_pending.get("RES_DATE")
                        pending_date_str = pending_date[:10] if pending_date else "Unknown date"
                        show_notification(f"There is a pending result from {pending_date_str}. Please update it or wait for the result before uploading a new X-ray.", "warning")
                    else:
                        st.session_state["add_xray_mode"] = True
                        st.rerun()

    

    # --- Add X-ray upload mode ---
    if st.session_state.get("add_xray_mode", False):
        selected = st.session_state.selected_case

        # Initialize X-ray upload state
        if "records_xray_step" not in st.session_state:
            st.session_state.records_xray_step = 2
            st.session_state.records_xray_uploaded = False
            st.session_state.records_analyze_triggered = False
        # Ensure uploaded file name is initialized
        if "records_uploaded_file_name" not in st.session_state:
            st.session_state["records_uploaded_file_name"] = ""

        st.markdown("<h4>Upload New Chest X-ray</h4>", unsafe_allow_html=True)

        # --- Step Navigation ---
        def step_class(display_step):
            try:
                # Map display step back to actual internal step
                internal_step = display_step + 1  # since internal starts at 2 for x-ray (1 is for the personal info)
                return "" if internal_step <= int(st.session_state.records_xray_step) else "inactive"
            except ValueError:
                return "inactive"

        st.markdown(f"""
            <div class="step-container">
                <div class="step-line"></div>
                <div class="step {step_class(1)}">
                    <span class="number">1</span>
                    <span class="label">X-ray Upload</span>
                </div>
                <div class="step {step_class(2)}">
                    <span class="number">2</span>
                    <span class="label">AI Processing & Result</span>
                </div>
                <div class="step {step_class(3)}">
                    <span class="number">3</span>
                    <span class="label">Finalize & Save</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Common patient info header
        st.markdown(f"""
        <div class="patient-info-card {theme_class}">
            <h5>Patient Information</h5>
            <table style="width:100%; border-collapse: collapse; border:none;">
                <tr style="border: none;">
                    <td style="border: none;"><strong>Patient ID:</strong> {selected['pt_id']}</td>
                    <td style="border: none;"><strong>Phone Number:</strong> {selected.get('phone', 'N/A')}</td>
                </tr>
                <tr style="border: none;">
                    <td style="border: none;"><strong>Name:</strong> {selected['name']}</td>
                    <td style="border: none;"><strong>Sex:</strong> {selected.get('sex', 'N/A')}</td>
                </tr>
                <tr style="border: none;">
                    <td style="border: none;"><strong>Age:</strong> {selected.get('age', 'N/A')}</td>
                    <td style="border: none;"><strong>Address:</strong> {selected.get('address', 'N/A')}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        # Step 2: Upload X-ray
        if st.session_state.records_xray_step == 2:
            records_uploaded = st.file_uploader("", type=["png", "jpg", "jpeg", "bmp"], 
                                    key="records_xray_uploader_step2")

            # Detect if file uploader is cleared (no file)
            if records_uploaded is None:
                st.session_state.records_xray_uploaded = False
                st.session_state.pop("records_uploaded_file_bytes", None)
                st.session_state.pop("records_uploaded_file_name", None)
                st.session_state.records_xray_warning_shown = False

            # When a file is uploaded
            if records_uploaded:
                # Check if this is a new upload by comparing file name or just reset warning flag
                if st.session_state.get("records_last_uploaded_file_name") != records_uploaded.name:
                    st.session_state.records_xray_warning_shown = False
                    st.session_state["records_last_uploaded_file_name"] = records_uploaded.name

                try:
                    img = Image.open(records_uploaded).convert("RGB")

                    # Validate before prediction with strict check
                    if not is_xray_like(img):
                        # If fails strict check, try relaxed check with warning
                        if is_xray_like_relaxed(img):
                            if not st.session_state.get("records_xray_warning_shown", False):
                                show_notification("This image deviates from standard appearance but may still represent a valid chest X-ray. Please proceed with careful analysis.", "warning")
                                st.session_state.records_xray_warning_shown = True
                            st.session_state.records_xray_uploaded = True
                        else:
                            show_notification("This image does not meet the criteria for a valid chest X-ray. Please upload a different image.", "error")
                            st.session_state.records_xray_uploaded = False
                            st.session_state.records_xray_warning_shown = False
                    else:
                        st.session_state.records_xray_uploaded = True
                        st.session_state.records_xray_warning_shown = False

                    if st.session_state.records_xray_uploaded:
                        st.session_state.records_uploaded_file_bytes = records_uploaded.getvalue()
                        st.session_state.records_uploaded_file_name = records_uploaded.name

                except Exception as e:
                    show_notification(f"Error processing image: {e}", "error")
                    st.session_state["records_xray_uploaded"] = False
                    st.session_state.records_xray_warning_shown = False

            cancel_col, next_col = st.columns([11, 1])

            if cancel_col.button("Cancel", key="records_step2_cancel"):
                st.session_state["records_cancel_upload"] = True

            if st.session_state.get("records_xray_uploaded", False):
                if next_col.button("Next", key="records_step2_next"):
                    st.session_state.records_xray_step = 3
                    st.session_state["records_analyze_triggered"] = True
                    st.rerun()

            if st.session_state.get("records_cancel_upload"):
                @st.dialog("Cancel X-ray Upload", width="small")
                def cancel_upload_dialog():
                    st.write("Are you sure you want to cancel this X-ray upload? All uploaded files and data will be permanently discarded.")

                    confirm_col, spacer, cancel_col = st.columns([1, 3.5, 1]) 

                    with confirm_col:
                        if st.button("Yes", key="records_cancel_yes"):
                            # Exit upload mode
                            st.session_state["add_xray_mode"] = False
                            # Clear ALL temporary data
                            cleanup_keys = [
                                "records_uploaded_file_bytes", "records_uploaded_file_name",
                                "records_xray_uploaded", "records_cancel_upload",
                                "records_AI_RESULT", "records_analyze_triggered",
                                "records_xray_step", "records_cancel_upload_step3",
                                "records_confirm_save"
                            ]
                            for key in cleanup_keys:
                                st.session_state.pop(key, None)
                            st.rerun()

                    with cancel_col:
                        if st.button("No", key="records_cancel_no"):
                            st.session_state["records_cancel_upload"] = False
                            st.rerun()

                cancel_upload_dialog()

        # Step 3: Analysis
        elif st.session_state.records_xray_step == 3:
            
            if st.session_state.get("records_analyze_triggered"):
                if "records_uploaded_file_bytes" in st.session_state and st.session_state.records_uploaded_file_bytes:
                    # Show spinner
                    spinner_html = """
                    <div style='
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 300px;
                    '>
                        <div style='text-align: center;'>
                            <div class='loader' style='
                                border: 6px solid #f3f3f3;
                                border-top: 6px solid #ff4b4b;
                                border-radius: 50%;
                                width: 60px;
                                height: 60px;
                                animation: spin 1s linear infinite;
                                margin: auto;
                            '></div>
                            <p style='margin-top: 20px; font-size: 22px;'>Analyzing X-ray...</p>
                        </div>
                    </div>
                    <style>
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                    </style>
                    """
                    st.markdown(spinner_html, unsafe_allow_html=True)

                    # Perform prediction
                    uploaded_file = io.BytesIO(st.session_state.records_uploaded_file_bytes)
                    label, confidence = predict_tb(uploaded_file)
                    st.session_state["records_AI_RESULT"] = {"label": label, "confidence": confidence}
                    st.session_state["records_analyze_triggered"] = False
                    st.rerun()

            col_img, col_result = st.columns([3, 2])

            # Left: X-ray Image
            with col_img:
                if "records_uploaded_file_bytes" in st.session_state and st.session_state.records_uploaded_file_bytes:
                    image = Image.open(io.BytesIO(st.session_state.records_uploaded_file_bytes))

                    st.markdown(
                    """
                    <div style="margin: 10px 0 -80px 0;">
                        &nbsp; Zoom &nbsp;&nbsp;&nbsp;&nbsp; View
                    </div>
                    """,
                    unsafe_allow_html=True
                    )
                    view_mode = st.segmented_control(
                        label="", 
                        options=["   🔍   ", "   🖼️   "], 
                        default="   🖼️   ",
                        key= "view_mode1_rec"
                    )

                    if view_mode == "   🔍   ":
                        from streamlit_image_zoom import image_zoom
                        image_zoom(image, zoom_factor=2)

                    elif view_mode == "   🖼️   ":
                        st.image(image, width='content')

                    else:
                        st.image(image, width='content')

                else:
                    st.markdown("No image uploaded.")

            # Right: AI Result
            with col_result:
                # Only show results if analysis is complete
                if "records_AI_RESULT" in st.session_state:
                    label, confidence = st.session_state.records_AI_RESULT.values()

                    def presumptive_result_color_class(presumptive_result_value):
                        presumptive_result_value_lower = presumptive_result_value.lower()
                        if presumptive_result_value_lower == "positive":
                            return "highlight-red"
                        elif presumptive_result_value_lower == "negative":
                            return "highlight-green"
                        return ""
                    
                    presumptive_class = presumptive_result_color_class(label)

                    def confidence_color_class(presumptive_result_value, confidence_result_value):
                        try:
                            conf_num = float(confidence_result_value)
                        except ValueError:
                            return ""  # fallback if confidence isn't a number

                        presumptive_result_lower = presumptive_result_value.lower()

                        # Define zones
                        if conf_num >= 80:
                            zone = "high"
                        elif 50 <= conf_num < 80:
                            zone = "medium"
                        else:  # conf_num < 50
                            zone = "low"

                        # Assign colors based on prediction and confidence zone
                        if presumptive_result_lower == "positive":
                            if zone == "high":
                                return "highlight-red"      # high chance of true positive
                            elif zone == "medium":
                                return "highlight-orange"   # middle zone
                            else:  # low
                                return "highlight-green"    # likely false positive
                        elif presumptive_result_lower == "negative":
                            if zone == "high":
                                return "highlight-green"    # high chance of true negative
                            elif zone == "medium":
                                return "highlight-orange"   # middle zone
                            else:  # low
                                return "highlight-red"      # likely false negative
                        return ""  # fallback for unknown labels

                    confidence_class = confidence_color_class(label, confidence)

                    st.markdown(f"""
                        <div class="ai-result-container">
                            <h5>AI Analysis Result</h5>
                            <p>Presumptive TB Result: <strong class="{presumptive_class}">{label}</strong></p>
                            <p>AI Confidence Level: <strong class="{confidence_class}">{confidence}%</strong></p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div class="ai-result-container">
                            <h5>AI Analysis Result</h5>
                            <p>Analysis in progress...</p>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                col_spacer, col_button = st.columns([1, 3])
                with col_button:
                    if st.button("🔄 Reupload X-ray", key="records_step3_reupload"):
                        st.session_state.records_xray_step = 2
                        # Clear analysis results when reuploading
                        for key in ["records_uploaded_file_bytes", "records_uploaded_file_name", 
                                "records_AI_RESULT", "records_xray_uploaded"]:
                            st.session_state.pop(key, None)
                        st.rerun()

            # Navigation buttons
            cancel_col, next_col = st.columns([11, 1])
            
            if cancel_col.button("Cancel", key="records_step3_cancel"):
                st.session_state["records_cancel_upload_step3"] = True
                st.rerun()
            
            # Only show Next button if analysis is complete
            if "records_AI_RESULT" in st.session_state:
                if next_col.button("Next", key="records_step3_next"):
                    st.session_state.records_xray_step = 4
                    st.rerun()
            
            # Cancel confirmation dialog
            if st.session_state.get("records_cancel_upload_step3"):
                @st.dialog("Cancel X-ray Upload", width="small")
                def cancel_upload_dialog():
                    st.write("Are you sure you want to cancel this X-ray upload? All uploaded files and analysis results will be permanently discarded.")

                    confirm_col, spacer, cancel_col = st.columns([1, 3.5, 1]) 

                    with confirm_col:
                        if st.button("Yes", key="records_cancel_step3_yes"):
                            # Exit upload mode
                            st.session_state["add_xray_mode"] = False
                            # Clear ALL temporary data
                            cleanup_keys = [
                                "records_uploaded_file_bytes", "records_uploaded_file_name", 
                                "records_xray_uploaded", "records_cancel_upload_step3",
                                "records_AI_RESULT", "records_analyze_triggered",
                                "records_xray_step", "records_cancel_upload",
                                "records_confirm_save"
                            ]
                            for key in cleanup_keys:
                                st.session_state.pop(key, None)
                            st.rerun()

                    with cancel_col:
                        if st.button("No", key="records_cancel_step3_no"):
                            st.session_state["records_cancel_upload_step3"] = False
                            st.rerun()

                cancel_upload_dialog()

        # Step 4: Review and Save
        elif st.session_state.records_xray_step == 4:
      
            col_img, col_result = st.columns([3, 2])

            # Left: X-ray Image
            with col_img:
                if "records_uploaded_file_bytes" in st.session_state and st.session_state.records_uploaded_file_bytes:
                    image = Image.open(io.BytesIO(st.session_state.records_uploaded_file_bytes))

                    st.markdown(
                    """
                    <div style="margin: 10px 0 -80px 0;">
                        &nbsp; Zoom &nbsp;&nbsp;&nbsp;&nbsp; View
                    </div>
                    """,
                    unsafe_allow_html=True
                    )
                    view_mode = st.segmented_control(
                        label="", 
                        options=["   🔍   ", "   🖼️   "], 
                        default="   🖼️   ",
                        key= "view_mode2_rec"
                    )

                    if view_mode == "   🔍   ":
                        from streamlit_image_zoom import image_zoom
                        image_zoom(image, zoom_factor=2)

                    elif view_mode == "   🖼️   ":
                        st.image(image, width='content')

                    else:
                        st.image(image, width='content')

                else:
                    st.markdown("No image uploaded.")

            # Right: AI Result
            with col_result:
                if "records_AI_RESULT" in st.session_state:
                    label, confidence = st.session_state.records_AI_RESULT.values()

                    def presumptive_result_color_class(presumptive_result_value):
                        presumptive_result_value_lower = presumptive_result_value.lower()
                        if presumptive_result_value_lower == "positive":
                            return "highlight-red"
                        elif presumptive_result_value_lower == "negative":
                            return "highlight-green"
                        return ""
                    
                    presumptive_result_class = presumptive_result_color_class(label)

                    def confidence_color_class(presumptive_result_value, confidence_result_value):
                        try:
                            conf_num = float(confidence_result_value)
                        except ValueError:
                            return ""  # fallback if confidence isn't a number

                        presumptive_result_lower = presumptive_result_value.lower()

                        # Define zones
                        if conf_num >= 80:
                            zone = "high"
                        elif 50 <= conf_num < 80:
                            zone = "medium"
                        else:  # conf_num < 50
                            zone = "low"

                        # Assign colors based on prediction and confidence zone
                        if presumptive_result_lower == "positive":
                            if zone == "high":
                                return "highlight-red"      # high chance of true positive
                            elif zone == "medium":
                                return "highlight-orange"   # middle zone
                            else:  # low
                                return "highlight-green"    # likely false positive
                        elif presumptive_result_lower == "negative":
                            if zone == "high":
                                return "highlight-green"    # high chance of true negative
                            elif zone == "medium":
                                return "highlight-orange"   # middle zone
                            else:  # low
                                return "highlight-red"      # likely false negative
                        return ""  # fallback for unknown labels

                    confidence_class = confidence_color_class(label, confidence)

                    st.markdown(f"""
                        <div class="ai-result-container">
                            <h5>AI Analysis Result</h5>
                            <p>X-Ray Date: <strong>{datetime.now().strftime('%m-%d-%Y')}</strong></p>
                            <p>Presumptive TB Result: <strong class="{presumptive_result_class}">{label}</strong></p>
                            <p>AI Confidence Level: <strong class="{confidence_class}">{confidence}%</strong></p>
                            <p>Status: <strong class="highlight-orange">Pending</strong></p>
                        </div>
                    """, unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

            # Navigation buttons
            back_col, save_col = st.columns([11, 1])
            if back_col.button("Back", key="records_step4_back"):
                st.session_state.records_xray_step = 3
                st.rerun()
                
            if save_col.button("Save", key="records_step4_save"):
                st.session_state["records_confirm_save"] = True
                st.rerun()
                
            # Save confirmation dialog
            if st.session_state.get("records_confirm_save"):
                @st.dialog("Confirm Save X-ray", width="small")
                def confirm_save_dialog():
                    st.write("Are you sure you want to save this X-ray and its analysis results?")

                    col_yes, spacer, col_no = st.columns([1, 3.5, 1])

                    with col_yes:
                        if st.button("Yes", key="records_save_xray_yes"):    
                            try:
                                # Save to Supabase
                                save_success = save_xray_to_supabase(
                                    patient_id=selected["pt_id"],
                                    image_bytes=st.session_state["records_uploaded_file_bytes"],
                                    file_name=st.session_state["records_uploaded_file_name"],
                                    ai_result=st.session_state["records_AI_RESULT"],
                                    show_notification=show_notification,
                                    is_light=is_light
                                )
                                
                                if save_success:
                                    st.session_state["records_confirm_save"] = False
                                    
                                    st.session_state["add_xray_mode"] = False
                                    cleanup_keys = [
                                        "records_uploaded_file_bytes", "records_uploaded_file_name", 
                                        "records_AI_RESULT", "records_xray_uploaded", 
                                        "records_analyze_triggered", "records_confirm_save",
                                        "records_xray_step", "records_cancel_upload",
                                        "records_cancel_upload_step3"
                                    ]
                                    for key in cleanup_keys:
                                        st.session_state.pop(key, None)
                                    
                                    show_notification("X-ray saved successfully!", "success")
                                    
                                    st.rerun()
                                else:
                                    show_notification("Failed to save X-ray. Please try again.", "error")
                                    
                            except Exception as e:
                                show_notification(f"Error saving X-Ray: {str(e)}", "error")

                    with col_no:
                        if st.button("No", key="records_save_xray_no"):
                            st.session_state["records_confirm_save"] = False
                            st.rerun()

                confirm_save_dialog()
                
        st.stop()
            
    # If NOT in view mode:
    if not st.session_state.view_mode:

        # Search 
        new_search = st.text_input("Search", value=st.session_state["search_bar_records"], placeholder="Enter a patient's name or ID", key="search_input")
        if new_search != st.session_state["search_bar_records"]:
            st.session_state["search_bar_records"] = new_search
            st.session_state.records_page_num = 1
            st.rerun()

        # --- Filters ---
        col_status, col_presumptiveTB, col_date_from, col_date_to, col_reset = st.columns([2, 2, 2, 2, 1.5])

        # Status Filter
        with col_status:
            st.markdown('<div class="filter-label">Status</div>', unsafe_allow_html=True)
            prev_status = st.session_state.get("records_status_filter", "All")
            selected_status = st.selectbox(
                "",
                ["All", "Pending", "Confirmed Positive", "Confirmed Negative"],
                index=["All", "Pending", "Confirmed Positive", "Confirmed Negative"].index(prev_status),
                key="records_status_filter_select"
            )
            if selected_status != prev_status:
                st.session_state["records_status_filter"] = selected_status
                st.session_state.records_page_num = 1
                st.rerun()

        # Presumptive TB
        with col_presumptiveTB:
            st.markdown('<div class="filter-label">Presumptive TB</div>', unsafe_allow_html=True)
            prev_presumptive = st.session_state.get("records_presumptive_filter", "All")
            selected_presumptive = st.selectbox(
                "", 
                ["All", "Positive", "Negative"],
                index=["All", "Positive", "Negative"].index(st.session_state.records_presumptive_filter),
                key="records_presumptive_filter_select"
            )
            if selected_presumptive != prev_presumptive:
                st.session_state["records_presumptive_filter"] = selected_presumptive
                st.session_state.records_page_num = 1
                st.rerun()

        # Date From
        with col_date_from:
            st.markdown('<div class="filter-label">Date From</div>', unsafe_allow_html=True)
            prev_date_from = st.session_state.get("records_date_from")
            selected_from = st.date_input(
                "Start Date", 
                value=st.session_state.records_date_from, 
                key="records_date_from_input", 
                label_visibility="collapsed"
            )
            if selected_from != prev_date_from:
                st.session_state["records_date_from"] = selected_from
                st.session_state.records_page_num = 1
                st.rerun()

        # Date To
        with col_date_to:
            st.markdown('<div class="filter-label">Date To</div>', unsafe_allow_html=True)
            prev_date_to = st.session_state.get("records_date_to")
            selected_to = st.date_input(
                "End Date", 
                value=st.session_state.records_date_to, 
                key="records_date_to_input", 
                label_visibility="collapsed"
            )
            if selected_to != prev_date_to:
                st.session_state["records_date_to"] = selected_to
                st.session_state.records_page_num = 1
                st.rerun()


        with col_reset:
            st.markdown('<div class="filter-label">&nbsp;</div>', unsafe_allow_html=True)
            if st.button("Reset Filters", key="reset_filters"):
                st.session_state["reset_triggered"] = True
                st.rerun()
                

        # --- Display Filtered Results ---
        filtered_cases = apply_filters()
        
        # Determine if any filters are active
        filters_active = (
            st.session_state["records_status_filter"] != "All" or
            st.session_state["records_presumptive_filter"] != "All" or
            st.session_state["records_date_from"] != oldest_date or
            st.session_state["records_date_to"] != date.today() or
            st.session_state["search_bar_records"].strip() != ""
        )

        # Create columns for the total number badges
        col_center = st.columns([1])[0]

        with col_center:
            if filters_active:
                st.markdown(f"""
                <div style="
                    position: relative;
                    top: -15px;
                    color: {filtered_case_text};
                    padding: 1px 1px;
                    border-radius: 12px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-weight: 700;
                    border: none;
                    text-align: center;
                    background-color: none; 
                    margin-top: 10px;       
                ">
                    <span style="margin-right: -2px;"></span>
                    Filtered Cases: {len(filtered_cases)}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="
                    position: relative;
                    top: -15px;
                    color: {total_cases_text};
                    padding: 1px 1px;
                    border-radius: 12px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-weight: 700;
                    border: none;
                    text-align: center;
                    background-color: none;
                    margin-top: 10px;
                ">
                    <span style="margin-right: -2px;"></span>
                    Total Cases: {len(cases)}
                </div>
                """, unsafe_allow_html=True)

        total_pages = (len(filtered_cases) - 1) // cases_per_page + 1
        current_page = st.session_state.records_page_num
        start_idx = (current_page - 1) * cases_per_page
        end_idx = start_idx + cases_per_page
        cases_to_display = filtered_cases[start_idx:end_idx]

        if not cases_to_display:
            st.markdown("<div style='text-align: center; padding: 2rem; font-weight: bold;'>No matching records have been found.</div>", unsafe_allow_html=True)
            return
        
        # Render Table Header (as columns so it aligns with body)
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 2])
            
            col1.markdown(f"<div style='text-align: left; font-weight: bold;margin-bottom: 20px;'>Patient Name</div>", unsafe_allow_html=True)
            col2.markdown(f"<div style='text-align: left; font-weight: bold; margin-bottom: 20px;'>X-Ray Date</div>", unsafe_allow_html=True)
            col3.markdown(f"<div style='text-align: left; font-weight: bold;margin-bottom: 20px;'>Presumptive TB</div>", unsafe_allow_html=True)
            col4.markdown(f"<div style='text-align: left; font-weight: bold;margin-bottom: 20px;'>AI Confidence</div>", unsafe_allow_html=True)
            col5.markdown(f"<div style='text-align: left; font-weight: bold;margin-bottom: 20px;'>Status</div>", unsafe_allow_html=True)
            col6.markdown(f"<div style='text-align: left; font-weight: bold;margin-bottom: 20px;'>Action</div>", unsafe_allow_html=True)

        current_page = st.session_state.records_page_num
        start_idx = (current_page - 1) * cases_per_page
        end_idx = start_idx + cases_per_page
        cases_to_display = filtered_cases[start_idx:end_idx]

        for i, case in enumerate(cases_to_display, start=start_idx):
            cols = st.columns([2, 2, 2, 2, 2, 2])
            with cols[0]:
                st.write(case['name'])
            with cols[1]:
                display_date = datetime.fromisoformat(case['date']).date().isoformat()
                st.write(display_date)
            with cols[2]:
                st.write(case['result'])
            with cols[3]:
                st.write(case['confidence'])
            with cols[4]:
                status = case['diagnosis']
                color = "#ffc107" if status == "Pending" else "#4caf50" if status == "Confirmed Negative" else "#f44336"
                st.markdown(f"<div style='font-weight: bold; color: {color};'>{status}</div>", unsafe_allow_html=True)
            with cols[5]:
                if st.button("View", key=f"view_{i}"):
                    st.session_state.selected_case = case
                    st.session_state.view_mode = True
                    st.rerun()

        pagination_controls("bottom", total_pages)

    # If in view mode: show patient details and filtered records table with pagination
    else:
        selected = st.session_state.selected_case

        # Ensure view_cases is always available in view mode
        def fetch_all_cases_for_patient(pt_id):
            try:
                response = (
                    supabase.table("RESULT_Table")
                    .select("""
                        RES_DATE,
                        RES_PRESUMPTIVE,
                        RES_CONF_SCORE,
                        RES_STATUS,
                        CHEST_XRAY_Table!inner(
                            CXR_ID,
                            PT_ID,
                            CXR_FILE_PATH
                        )
                    """)
                    .eq("CHEST_XRAY_Table.PT_ID", pt_id)
                    .order("RES_DATE", desc=True)
                    .execute()
                )

                patient_cases = []
                for entry in response.data:
                    chest = entry.get("CHEST_XRAY_Table")
                    if not chest:
                        continue

                    confidence_percent = f"{int(float(entry['RES_CONF_SCORE']) * 100)}%"

                    # Include CXR_ID and PT_ID for later use
                    patient_cases.append({
                        "date": entry["RES_DATE"],
                        "result": entry["RES_PRESUMPTIVE"],
                        "confidence": confidence_percent,
                        "diagnosis": entry["RES_STATUS"],
                        "image_path": chest.get("CXR_FILE_PATH", None),
                        "CXR_ID": chest.get("CXR_ID"),
                        "PT_ID": chest.get("PT_ID")
                    })

                return patient_cases

            except Exception as e:
                show_notification("🚨 Failed to fetch patient x-ray records.", "error")
                st.exception(e)
                return []

        pt_id = st.session_state.selected_case["pt_id"]
        view_cases = fetch_all_cases_for_patient(pt_id)
 
        # --- Fetch TB treatment details for a specific X-Ray ---
        def fetch_patient_treatment_info(cxr_id=None):
            if not cxr_id:
                return None

            resp = supabase.table("TREATMENT_Table").select(
                """
                TR_STATUS,
                TR_OUTCOME,
                TR_START_DATE,
                PT_ID,
                CXR_ID,
                TR_EXPECTED_END_DATE,
                TR_ACTUAL_END_DATE,
                TR_UPDATED_AT,
                TR_NOTES,
                UPDATED_BY_USER_ID
                """
            ).eq("CXR_ID", cxr_id).execute()

            data = resp.data or []
            if not data:
                return None

            latest_treatment = sorted(
                data,
                key=lambda x: x.get("TR_START_DATE", ""),
                reverse=True
            )[0]

            # Get user who enrolled the treatment (first creator)
            enrolled_by = None
            first_treatment_resp = supabase.table("TREATMENT_Table").select(
                "UPDATED_BY_USER_ID"
            ).eq("CXR_ID", cxr_id).order("TR_CREATED_AT", desc=False).limit(1).execute()
            
            if first_treatment_resp.data:
                enrolled_by_user_id = first_treatment_resp.data[0].get("UPDATED_BY_USER_ID")
                if enrolled_by_user_id:
                    user_res = supabase.table("USER_Table").select(
                        "USER_FNAME, USER_MNAME, USER_LNAME"
                    ).eq("USER_ID", enrolled_by_user_id).single().execute()
                    
                    if user_res.data:
                        fname = user_res.data.get("USER_FNAME") or ""
                        mname = user_res.data.get("USER_MNAME") or ""
                        lname = user_res.data.get("USER_LNAME") or ""
                        enrolled_by = f"{fname} {mname + ' ' if mname else ''}{lname}".strip()

            return {
                "enrolled": "Yes" if latest_treatment.get("TR_STATUS") else "No",
                "enrolled_by": enrolled_by or "N/A",
                "start_date": latest_treatment.get("TR_START_DATE", "N/A"),
                "status": latest_treatment.get("TR_STATUS", "N/A"),
                "outcome": latest_treatment.get("TR_OUTCOME", "N/A"),
                "expected_end_date": latest_treatment.get("TR_EXPECTED_END_DATE"),
                "actual_end_date": latest_treatment.get("TR_ACTUAL_END_DATE"),
                "last_modified": latest_treatment.get("TR_UPDATED_AT"),
                "treatment_note": latest_treatment.get("TR_NOTES", ""),
                "updated_by_user_id": latest_treatment.get("UPDATED_BY_USER_ID")
            }

        # --- If viewing image only ---
        if st.session_state.get("view_image_mode"):
            image_path = st.session_state.get("image_path")
            
            # Back button above the title
            if st.button("Back", key="view_image_back"):
                st.session_state["view_image_mode"] = False
                st.session_state["image_path"] = None
                st.rerun()
            
            st.markdown("<h4>Chest X-Ray Viewer</h4>", unsafe_allow_html=True)

            # --- Fetch diagnosis note using image_path ---
            def fetch_diagnosis_note(image_path):
                try:
                    cxr_res = (
                        supabase.table("CHEST_XRAY_Table")
                        .select("CXR_ID")
                        .eq("CXR_FILE_PATH", image_path)
                        .single()
                        .execute()
                    )
                    cxr_id = cxr_res.data.get("CXR_ID") if cxr_res.data else None
                    if not cxr_id:
                        return "No diagnosis note recorded."

                    diagnosis_res = (
                        supabase.table("DIAGNOSIS_Table")
                        .select("DX_NOTES")
                        .eq("CXR_ID", cxr_id)
                        .order("DX_UPDATED_AT", desc=True)
                        .limit(1)
                        .execute()
                    )
                    return diagnosis_res.data[0]["DX_NOTES"] if diagnosis_res.data else "No diagnosis note recorded."
                except Exception as e:
                    return f"Error fetching notes: {e}"

            diagnosis_note = fetch_diagnosis_note(image_path)
            
            # --- Find case info for this image ---
            case_info = next((case for case in view_cases if case.get("image_path") == image_path), None)
            
            # --- Determine layout based on diagnosis ---
            if case_info:
                current_diagnosis = case_info.get("diagnosis", "Pending")
                is_confirmed_case = current_diagnosis in ["Confirmed Positive", "Confirmed Negative"]
                
                if is_confirmed_case:
                    # 3-column layout for confirmed cases
                    col_img, col_xray, col_treatment = st.columns([2, 1.5, 1.5])
                else:
                    # 2-column layout for pending cases
                    col_img, col_xray = st.columns([2, 1.5])
            else:
                # Default to 2 columns if no case info
                col_img, col_xray = st.columns([2, 1.5])
                is_confirmed_case = False
            
            # --- Image Column (Left) ---
            with col_img:
                if image_path:
                    try:
                        if image_path.startswith("http"):
                            response = requests.get(image_path)
                            response.raise_for_status()
                            image = Image.open(BytesIO(response.content))
                        else:
                            image = Image.open(image_path)

                        st.markdown(
                            """
                            <div style="margin: 10px 0 -80px 0;">
                                &nbsp; Zoom &nbsp;&nbsp;&nbsp;&nbsp; View
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        view_mode = st.segmented_control(
                            label="", 
                            options=["   🔍   ", "   🖼️   "], 
                            default="   🖼️   ",
                            key="view_mode3_rec"
                        )

                        if view_mode == "   🔍   ":
                            from streamlit_image_zoom import image_zoom
                            image_zoom(image, zoom_factor=2)
                        else:
                            st.image(image, width='content')
                            
                        # --- Download X-Ray Report Button ---

                        # Fetch all necessary data for PDF
                        if case_info and selected:
                            try:
                                # Fetch diagnosis notes
                                diagnosis_notes = fetch_diagnosis_note(image_path) if image_path else "No diagnosis note recorded"
                                
                                # Fetch doctor's name if case is confirmed
                                doctor_name = None
                                status = case_info.get("diagnosis", "Pending")
                                if status in ["Confirmed Positive", "Confirmed Negative"]:
                                    doctor_name = fetch_doctor_name(image_path)
                                
                                # Fetch additional metadata
                                metadata = fetch_xray_metadata(image_path)
                                
                                # Format dates for PDF
                                formatted_confirmation_date = None
                                formatted_last_modified = None
                                
                                if metadata["confirmed_at"]:
                                    formatted_confirmation_date = datetime.fromisoformat(metadata["confirmed_at"]).strftime('%m-%d-%Y, %I:%M %p')
                                
                                if metadata["updated_at"]:
                                    formatted_last_modified = datetime.fromisoformat(metadata["updated_at"]).strftime('%m-%d-%Y, %I:%M %p')
                                
                                # Fetch Treatment Info if confirmed positive
                                treatment_info = None
                                if status.lower() == "confirmed positive":
                                    treatment_info = fetch_patient_treatment_info(case_info.get("CXR_ID"))
                                
                                # Format treatment dates for PDF
                                formatted_start_date = None
                                formatted_expected_end = None
                                formatted_actual_end = None
                                formatted_last_modified = None
                                updated_by_name = None
                                
                                if treatment_info:
                                    if treatment_info.get("start_date"):
                                        formatted_start_date = datetime.fromisoformat(treatment_info["start_date"]).strftime('%m-%d-%Y, %I:%M %p')
                                    if treatment_info.get("expected_end_date"):
                                        formatted_expected_end = datetime.fromisoformat(treatment_info["expected_end_date"]).strftime('%m-%d-%Y, %I:%M %p')
                                    if treatment_info.get("actual_end_date"):
                                        formatted_actual_end = datetime.fromisoformat(treatment_info["actual_end_date"]).strftime('%m-%d-%Y, %I:%M %p')
                                    if treatment_info.get("last_modified"):
                                        formatted_last_modified = datetime.fromisoformat(treatment_info["last_modified"]).strftime('%m-%d-%Y, %I:%M %p')
                                    if treatment_info.get("updated_by_user_id"):
                                        # Fetch full name
                                        user_res = supabase.table("USER_Table").select(
                                            "USER_FNAME, USER_MNAME, USER_LNAME"
                                        ).eq("USER_ID", treatment_info["updated_by_user_id"]).single().execute()
                                        
                                        if user_res.data:
                                            fname = user_res.data.get("USER_FNAME") or ""
                                            mname = user_res.data.get("USER_MNAME") or ""
                                            lname = user_res.data.get("USER_LNAME") or ""
                                            updated_by_name = f"{fname} {mname + ' ' if mname else ''}{lname}".strip()

                                # Generate PDF
                                pdf_bytes = generate_patient_pdf(
                                    selected,
                                    datetime.fromisoformat(case_info['date']).strftime('%m-%d-%Y, %I:%M %p'),
                                    case_info['result'],
                                    case_info['confidence'],
                                    status,
                                    diagnosis_notes,
                                    image_path=image_path,
                                    doctor_name=doctor_name,
                                    uploaded_by=metadata["uploader_name"],
                                    confirmation_date=formatted_confirmation_date,
                                    confirmed_by=metadata["confirming_doctor"],
                                    last_modified=formatted_last_modified,
                                    treatment_info={
                                        "enrolled": treatment_info.get("enrolled") if treatment_info else None,
                                        "enrolled_by": treatment_info.get("enrolled_by") if treatment_info else None,
                                        "start_date": formatted_start_date,
                                        "status": treatment_info.get("status") if treatment_info else None,
                                        "outcome": treatment_info.get("outcome") if treatment_info else None,
                                        "expected_end_date": formatted_expected_end,
                                        "actual_end_date": formatted_actual_end,
                                        "last_modified": formatted_last_modified,
                                        "updated_by": updated_by_name,
                                        "treatment_note": treatment_info.get("treatment_note", "") if treatment_info else ""
                                    } if treatment_info else None
                                )
                                
                                filename = f"PT_Report_{selected['name'].replace(' ', '_')}_{datetime.fromisoformat(case_info['date']).strftime('%Y%m%d')}.pdf"
                                
                                # Download button
                                col_download, col_spacer = st.columns([1, 2])
                                with col_download:
                                    st.download_button(
                                        label="Download X-Ray Report",
                                        data=pdf_bytes,
                                        file_name=filename,
                                        mime="application/pdf",
                                        width='stretch'
                                    )
                                
                            except Exception as e:
                                show_notification(f"Failed to generate PDF report: {e}", "error")
                        
                    except Exception as e:
                        show_notification(f"❌ Failed to open image: {e}", "error")
                else:
                    show_notification("❌ Image not found.", "error")
            
            # --- X-Ray Information Column (Middle) ---
            with col_xray:
                if case_info:
                    xray_date = datetime.fromisoformat(case_info['date']).strftime('%m-%d-%Y, %I:%M %p')
                    result = case_info['result']
                    confidence = case_info['confidence']
                    status = case_info['diagnosis']
                    
                    metadata = fetch_xray_metadata(image_path)
                    
                    def assign_color_class(value, field):
                        value_lowercase = value.lower()
                        if field == "result":
                            if value_lowercase == "positive":
                                return "highlight-red"
                            elif value_lowercase == "negative":
                                return "highlight-green"
                        elif field == "status":
                            if value_lowercase == "confirmed positive":
                                return "highlight-red"
                            elif value_lowercase == "confirmed negative":
                                return "highlight-green"
                            elif value_lowercase == "pending":
                                return "highlight-orange"
                        return ""
                    
                    presumptive_class = assign_color_class(result, "result")
                    status_class = assign_color_class(status, "status")
                    
                    info_html = f"""
                    <div class="ai-result-container">
                        <h5>X-Ray Information</h5>
                        <p>X-Ray Date: {tooltip_html(xray_date, "This is the timestamp when the X-Ray was uploaded to the system.")}</p>
                    """
                    
                    if metadata["uploader_name"]:
                        info_html += f"<p>Uploaded By: <strong>{metadata['uploader_name']}</strong></p>"
                    
                    info_html += f"""
                        <p>Presumptive TB Result: <strong class="{presumptive_class}">{result}</strong></p>
                        <p>AI Confidence Level: <strong>{confidence}</strong></p>
                    """
                    
                    if metadata["confirmed_at"] and status.lower() in ["Confirmed Positive", "Confirmed Negative"]:
                        confirmed_date = datetime.fromisoformat(metadata["confirmed_at"]).strftime('%m-%d-%Y, %I:%M %p')
                        info_html += f"<p>Confirmation Date: {tooltip_html(confirmed_date, 'This is the timestamp when the X-Ray was confirmed by the doctor.')}</p>"
                    
                    if metadata["confirming_doctor"] and status.lower() in ["Confirmed Positive", "Confirmed Negative"]:
                        info_html += f"<p>Confirmed By: <strong>{metadata['confirming_doctor']}</strong></p>"
                    
                    if metadata["updated_at"]:
                        updated_date = datetime.fromisoformat(metadata["updated_at"]).strftime('%m-%d-%Y, %I:%M %p')
                        info_html += f"<p>Last Modified: {tooltip_html(updated_date, 'This is the latest timestamp on which the X-Ray details were updated, showing any changes to the status, notes, or both.')}</p>"
                        
                        try:
                            # Get CXR_ID from image path
                            cxr_res = (
                                supabase.table("CHEST_XRAY_Table")
                                .select("CXR_ID")
                                .eq("CXR_FILE_PATH", image_path)
                                .single()
                                .execute()
                            )
                            
                            if cxr_res.data:
                                cxr_id = cxr_res.data.get("CXR_ID")
                                diagnosis_res = (
                                    supabase.table("DIAGNOSIS_Table")
                                    .select("""
                                        USER_ID,
                                        USER_Table(
                                            USER_FNAME,
                                            USER_MNAME,
                                            USER_LNAME
                                        )
                                    """)
                                    .eq("CXR_ID", cxr_id)
                                    .order("DX_UPDATED_AT", desc=True)
                                    .limit(1)
                                    .execute()
                                )
                                
                                if diagnosis_res.data:
                                    user_data = diagnosis_res.data[0].get("USER_Table", {})
                                    if user_data:
                                        fname = user_data.get("USER_FNAME", "").strip()
                                        mname = user_data.get("USER_MNAME", "").strip()
                                        lname = user_data.get("USER_LNAME", "").strip()
                                        if mname:
                                            last_modified_by = f"{fname} {mname} {lname}"
                                        else:
                                            last_modified_by = f"{fname} {lname}"
                                        info_html += f"<p>Last Modified By: <strong>{last_modified_by}</strong></p>"
                        except Exception as e:
                            print(f"Error fetching last modified by: {e}")
                    
                    info_html += "</div>"
                    st.markdown(info_html, unsafe_allow_html=True)
                    
                    # Add View button under X-ray information
                    if is_confirmed_case:
                        # 3-column layout
                        col1, col2, col3 = st.columns([1, 1, 1])
                        with col2:
                            if st.button("View DX", key="view_xray_info"):
                                st.session_state[f"show_view_xray_info_modal"] = True
                    else:
                        # 2-column layout
                        col1, col2, col3 = st.columns([1, 1, 1])
                        with col2:
                            if st.button("View DX", key="view_xray_info", width='stretch'):
                                st.session_state[f"show_view_xray_info_modal"] = True
                    
                    # View X-ray Info Modal
                    if st.session_state.get(f"show_view_xray_info_modal"):
                        @st.dialog("View X-Ray Diagnosis")
                        def show_view_xray_info_modal():
                            # Assign color class to status
                            status_class = assign_color_class(status, "status")
                            
                            st.markdown(f'Final Diagnosis Status: <strong><span class="{status_class}">{status}</span></strong>', unsafe_allow_html=True)
                            st.markdown(f"Final Diagnosis Note: <strong>{diagnosis_note if diagnosis_note else 'No notes recorded.'}</strong>", unsafe_allow_html=True)
                            
                            col1, col2, col3 = st.columns([1, 1, 1])
                            with col2:
                                if st.button("Back", key="back_view_xray_info", width='stretch'):
                                    st.session_state[f"show_view_xray_info_modal"] = False
                                    st.rerun()
                        
                        show_view_xray_info_modal()

            # Function to assign color classes for treatment status and outcome
            def assign_treatment_color_class(value, field):
                if not value or not isinstance(value, str):
                    return ""
                
                value_lowercase = value.lower()
                if field == "status":
                    if "ongoing" in value_lowercase:
                        return "highlight-blue"  
                    elif "interrupted" in value_lowercase:
                        return "highlight-orange"
                    elif "lost to follow-up" in value_lowercase:
                        return "highlight-purple" 
                    elif "transferred out" in value_lowercase:
                        return "highlight-gray" 
                    elif "failed" in value_lowercase:
                        return "highlight-red"
                    elif "completed" in value_lowercase:
                        return "highlight-green"
                elif field == "outcome":
                    if "cured" in value_lowercase:
                        return "highlight-green"
                    elif "completed" in value_lowercase:
                        return "highlight-orange"
                return ""
            
            # --- Treatment Information Column (Right - Only for confirmed cases) ---
            if is_confirmed_case:
                with col_treatment:
                    if status.lower() == "confirmed positive":
                        treatment_info = fetch_patient_treatment_info(case_info.get("CXR_ID"))
                        if treatment_info:
                            # Build treatment info HTML
                            treatment_html = """
                            <div class="ai-result-container">
                                <h5>Treatment Information</h5>
                            """

                            # Always show enrolled, start date, status, outcome
                            treatment_html += f"<p>Enrolled: <strong>{treatment_info.get('enrolled', 'No')}</strong></p>"

                            # Add Enrolled By
                            treatment_html += f"<p>Enrolled By: <strong>{treatment_info.get('enrolled_by', 'N/A')}</strong></p>"

                            # Format and add tooltip to Start Date
                            if treatment_info.get('start_date'):
                                formatted_start_date = datetime.fromisoformat(treatment_info['start_date']).strftime('%m-%d-%Y, %I:%M %p')
                                treatment_html += f"<p>Start Date: {tooltip_html(formatted_start_date, 'This is the timestamp when the treatment officially began for the patient.')}</p>"
                            else:
                                treatment_html += f"<p>Start Date: <strong>N/A</strong></p>"

                            # Add color code to Current Status
                            current_status = treatment_info.get('status', 'N/A')
                            status_color_class = assign_treatment_color_class(current_status, "status")
                            treatment_html += f'<p>Current Status: <strong class="{status_color_class}">{current_status}</strong></p>'

                            # Conditionally display optional fields with tooltips
                            if treatment_info.get("expected_end_date"):
                                expected_end = datetime.fromisoformat(treatment_info["expected_end_date"]).strftime('%m-%d-%Y, %I:%M %p')
                                treatment_html += f"<p>Expected End Date: {tooltip_html(expected_end, 'This is the anticipated completion timestamp for the treatment protocol (typically 6 months from start date).')}</p>"

                            if treatment_info.get("actual_end_date"):
                                actual_end = datetime.fromisoformat(treatment_info["actual_end_date"]).strftime('%m-%d-%Y, %I:%M %p')
                                treatment_html += f"<p>Actual End Date: {tooltip_html(actual_end, 'This is the actual timestamp when the treatment was completed or ended.')}</p>"

                            # Add Last Modified on with tooltip
                            if treatment_info.get("last_modified"):
                                last_modified_date = datetime.fromisoformat(treatment_info["last_modified"]).strftime('%m-%d-%Y, %I:%M %p')
                                treatment_html += f"<p>Last Modified on: {tooltip_html(last_modified_date, 'This is the latest timestamp when the treatment details were updated.')}</p>"

                            if treatment_info.get("updated_by_user_id"):
                                # Fetch first, middle, last names from USER_Table
                                user_res = supabase.table("USER_Table").select(
                                    "USER_FNAME, USER_MNAME, USER_LNAME"
                                ).eq("USER_ID", treatment_info["updated_by_user_id"]).single().execute()
                                
                                if user_res.data:
                                    fname = user_res.data.get("USER_FNAME") or ""
                                    mname = user_res.data.get("USER_MNAME") or ""
                                    lname = user_res.data.get("USER_LNAME") or ""
                                    
                                    # Construct full name (skip middle if empty)
                                    full_name = f"{fname} {mname + ' ' if mname else ''}{lname}".strip()
                                    if full_name:
                                        treatment_html += f"<p>Last Modified By: <strong>{full_name}</strong></p>"

                            treatment_html += "</div>"
                            st.markdown(treatment_html, unsafe_allow_html=True)
                            
                            # Add View button under Treatment information
                            col1, col2, col3 = st.columns([1, 1, 1])
                            with col2:
                                if st.button("View TX", key="view_treatment_info"):
                                    st.session_state[f"show_view_treatment_info_modal"] = True
                            
                            # View Treatment Info Modal
                            if st.session_state.get(f"show_view_treatment_info_modal"):
                                @st.dialog("View Treatment Information")
                                def show_view_treatment_info_modal():
                                    # Get treatment note and outcome
                                    treatment_note = treatment_info.get('treatment_note', 'No treatment note recorded.')
                                    outcome = treatment_info.get('outcome', 'N/A')
                                    
                                    # Assign color class to outcome
                                    outcome_color_class = assign_treatment_color_class(outcome, "outcome")
                                    
                                    st.markdown(f'Final Outcome: <strong><span class="{outcome_color_class}">{outcome}</span></strong>', unsafe_allow_html=True)
                                    st.markdown(f"Treatment Note: <strong>**{treatment_note}**</strong>", unsafe_allow_html=True)
                                    
                                    col1, col2, col3 = st.columns([1, 1, 1])
                                    with col2:
                                        if st.button("Back", key="back_view_treatment_info", width='stretch'):
                                            st.session_state[f"show_view_treatment_info_modal"] = False
                                            st.rerun()
                                
                                show_view_treatment_info_modal()
                        else:
                            # No treatment info available for confirmed positive
                            st.markdown(f"""
                            <div class="ai-result-container">
                                <h5>Treatment Information</h5>
                                <p style="text-align: center;"><em>No treatment information recorded for this confirmed positive case.</em></p>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        # For confirmed negative cases
                        st.markdown(f"""
                        <div class="ai-result-container">
                            <h5>Treatment Information</h5>
                            <p style="text-align: center;"><em>Treatment information is only applicable for confirmed positive cases.</em></p>
                        </div>
                        """, unsafe_allow_html=True)

            st.stop()  # Prevent rest of the page from showing

        # --- Show Patient Info Card (only when not in edit mode) ---
        if not st.session_state.get("edit_patient_mode", False):
            st.markdown(f"""
                <div class="patient-info-card {theme_class}">
                    <h4>Patient Information</h4>
                    <table style="width:100%; border-collapse: collapse; border:none;">
                        <tr style="border: none;">
                            <td style="border: none;"><strong>Patient ID:</strong> {selected['pt_id']}</td>
                            <td style="border: none;"><strong>Phone Number:</strong> {selected.get('phone', 'N/A')}</td>
                        </tr>
                        <tr style="border: none;">
                            <td style="border: none;"><strong>Name:</strong> {selected['name']}</td>
                            <td style="border: none;"><strong>Sex:</strong> {selected.get('sex', 'N/A')}</td>
                        </tr>
                        <tr style="border: none;">
                            <td style="border: none;"><strong>Age:</strong> {selected.get('age', 'N/A')}</td>
                            <td style="border: none;"><strong>Address:</strong> {selected.get('address', 'N/A')}</td>
                        </tr>
                    </table>
                </div>
            """, unsafe_allow_html=True)

        # --- Editable Form ---
        else:
            # --- Prefill form fields when entering edit mode ---
            if st.session_state.get("edit_patient_mode"):
                selected = st.session_state.selected_case
                st.session_state.rec_fname = selected.get("PATIENT_FNAME", "")
                st.session_state.rec_mname = selected.get("PATIENT_MNAME", "")
                st.session_state.rec_lname = selected.get("PATIENT_LNAME", "")
                st.session_state.rec_sex = selected.get("sex", "")
                st.session_state.rec_dob = datetime.strptime(selected.get("PATIENT_DOB", "2000-01-01"), "%Y-%m-%d").date()
                st.session_state.rec_phone = selected.get("phone", "")
                st.session_state.rec_street = selected.get("PATIENT_STREET", "")
                st.session_state.rec_house = selected.get("PATIENT_HOUSENO", "")
                st.session_state.rec_barangay = selected.get("PATIENT_BARANGAY", "")

             
            st.markdown("### Edit Patient Information")

            col1, col2, col3, col4 = st.columns([1, 3, 3, 3])
            with col1:
                st.markdown("<p style='margin-top: 35px;'>Name:</p>", unsafe_allow_html=True)
            with col2:
                st.session_state.rec_fname = col2.text_input("", placeholder="First Name", value=st.session_state.rec_fname)
            with col3:
                st.session_state.rec_mname = col3.text_input("", placeholder="Middle Name", value=st.session_state.rec_mname)
            with col4:
                st.session_state.rec_lname = col4.text_input("", placeholder="Last Name", value=st.session_state.rec_lname)

            col1, col2, col3, col4, col5, col6 = st.columns([1, 4, 2, 4, 1, 3])
            with col1:
                st.markdown("<p style='margin-top: 35px;'>Sex:</p>", unsafe_allow_html=True)
            with col2:
                st.markdown('<div>&nbsp;</div>', unsafe_allow_html=True)
                st.session_state.rec_sex = col2.selectbox("", ["Male", "Female"], index=["Male", "Female"].index(st.session_state.rec_sex))
            with col3:
                st.markdown("<p style='margin-top: 35px;'>Date of Birth:</p>", unsafe_allow_html=True)
            with col4:
                st.session_state.rec_dob  = col4.date_input("", value=st.session_state.rec_dob, min_value=date(1800, 1, 1), max_value=date.today())
            with col5:
                st.markdown("<p style='margin-top: 35px;'>Age:</p>", unsafe_allow_html=True)
            with col6:
                st.text_input("", value=str(calculate_age(st.session_state.rec_dob)), disabled=True)

            col1, col2, col3 = st.columns([1, 3, 3])
            with col1:
                st.markdown("<p style='margin-top: 35px;'>Phone Number:</p>", unsafe_allow_html=True)
            with col2:
                st.session_state.rec_phone = st.text_input("", placeholder="09XXXXXXXXX", max_chars=11, value=st.session_state.rec_phone)
            with col3:
                st.markdown("<p style='margin-top: 35px;'></p>", unsafe_allow_html=True)

            col1, col2, col3 = st.columns([3, 3, 3])
            with col1:
                st.text_input("Country", value="Philippines", disabled=True)
            with col2:
                st.text_input("Province", value="Cebu", disabled=True)
            with col3:
                st.text_input("City", value="Mandaue City", disabled=True)

            col1, col2, col3, col4 = st.columns([3, 3, 3, 3])
            with col1:
                st.session_state.rec_street = st.text_input("Street", placeholder="Street Name", value=st.session_state.rec_street)
            with col2:
                st.session_state.rec_house = st.text_input("House Number", placeholder="House Number", value=st.session_state.rec_house)
            with col3:
                st.markdown("<div style='font-size: 14px; padding-bottom: 5px;'>Barangay</div>", unsafe_allow_html=True)
                barangay_index = mandaue_barangays.index(st.session_state.rec_barangay) if st.session_state.rec_barangay in mandaue_barangays else 0
                st.session_state.rec_barangay = st.selectbox("Barangay", mandaue_barangays, index=barangay_index)
            with col4:
                st.text_input("ZIP Code", value="6014", disabled=True)

            # Save / Cancel Buttons
            col_cancel, spacer, col_save = st.columns([1, 6, 1])

            # Cancel button triggers confirmation
            with col_cancel:
                if st.button("Cancel", key="cancel_edit_button"):
                    st.session_state["cancel_edit"] = True
                    st.session_state["save_edit"] = False  # Ensure save prompt doesn't conflict

            # Only show Save button if there are changes
            with col_save:
                if has_changes(selected):
                    if st.button("Save", key="trigger_save_edit"):
                        st.session_state["cancel_edit"] = False  # Clear cancel
                        if not validate_edit():
                            st.session_state["save_edit"] = False  
                        else:
                            st.session_state["save_edit"] = True 
                else:
                    # Empty space to maintain layout when button is hidden
                    st.empty()
                

            # --- CANCEL Confirmation Prompt ---
            if st.session_state.get("cancel_edit"):

                @st.dialog("Discard Changes", width="small")
                def cancel_edit_dialog():
                    st.write("Are you sure you want to discard your changes? Your edits will be lost.")

                    col_yes, spacer, col_no = st.columns([1, 3.5, 1]) 

                    with col_yes:
                        if st.button("Yes", key="cancel_yes"):
                            st.session_state["edit_patient_mode"] = False
                            st.session_state.pop("form_prefilled", None)
                            st.session_state["cancel_edit"] = False
                            st.rerun()

                    with col_no:
                        if st.button("No", key="cancel_no"):
                            st.session_state["cancel_edit"] = False
                            st.rerun()

                cancel_edit_dialog()

            # --- SAVE Confirmation Prompt ---
            elif st.session_state.get("save_edit"):

                @st.dialog("Confirm Save", width="small")
                def save_edit_dialog():
                    st.write("Are you sure you want to save your changes?")

                    col_yes, spacer, col_no = st.columns([1, 3.5, 1]) 

                    with col_yes:
                        if st.button("Yes", key="save_yes"):
                            try:
                                patient_id = st.session_state.selected_case["pt_id"]
                                
                                # Calculate age from DOB
                                age_from_dob = calculate_age(st.session_state.rec_dob)
                                
                                supabase.table("PATIENT_Table").update({
                                    "PT_FNAME": st.session_state.rec_fname.strip().title(),
                                    "PT_MNAME": st.session_state.rec_mname.strip().title(),
                                    "PT_LNAME": st.session_state.rec_lname.strip().title(),
                                    "PT_SEX": st.session_state.rec_sex,
                                    "PT_DOB": st.session_state.rec_dob.isoformat(),
                                    "PT_AGE": age_from_dob,  
                                    "PT_PHONE": st.session_state.rec_phone.strip(),
                                    "PT_HOUSENO": st.session_state.rec_house.strip(),
                                    "PT_STREET": st.session_state.rec_street.strip().title(),
                                    "PT_BRGY": st.session_state.rec_barangay.strip(),
                                    "PT_UPDATED_AT": datetime.now().isoformat()
                                }).eq("PT_ID", patient_id).execute()

                                # Refresh updated data
                                updated_patient = supabase.table("PATIENT_Table").select("*").eq("PT_ID", patient_id).single().execute().data
                                updated_patient["name"] = f"{updated_patient.get('PT_FNAME', '')} {updated_patient.get('PT_MNAME', '')} {updated_patient.get('PT_LNAME', '')}".strip()
                                updated_patient["age"] = age_from_dob  
                                updated_patient["address"] = f"{updated_patient.get('PT_HOUSENO', '')}, {updated_patient.get('PT_STREET', '')}, {updated_patient.get('PT_BRGY', '')}, Mandaue City"

                                st.session_state.selected_case.update({
                                    "PATIENT_FNAME": updated_patient.get("PT_FNAME", ""),
                                    "PATIENT_MNAME": updated_patient.get("PT_MNAME", ""),
                                    "PATIENT_LNAME": updated_patient.get("PT_LNAME", ""),
                                    "PATIENT_DOB": updated_patient.get("PT_DOB", ""),
                                    "PATIENT_AGE": updated_patient.get("PT_AGE", ""),
                                    "PATIENT_PHONE": updated_patient.get("PT_PHONE", ""),
                                    "PATIENT_HOUSENO": updated_patient.get("PT_HOUSENO", ""),
                                    "PATIENT_STREET": updated_patient.get("PT_STREET", ""),
                                    "PATIENT_BARANGAY": updated_patient.get("PT_BRGY", ""),
                                    "PATIENT_CITY": "Mandaue City",
                                    "name": updated_patient["name"],
                                    "age": updated_patient["age"],
                                    "address": updated_patient["address"],
                                    "sex": updated_patient.get("PT_SEX", ""),
                                    "phone": updated_patient.get("PT_PHONE", "")
                                })

                                # Update Heatmap data for linked CXR records 
                                cxr_records = supabase.table("CHEST_XRAY_Table").select("CXR_ID").eq("PT_ID", patient_id).execute()
                                if cxr_records.data:
                                    age_group = get_age_group(age_from_dob)
                                    barangay_name = updated_patient.get("PT_BRGY", "")
                                    
                                    for cxr in cxr_records.data:
                                        cxr_id = cxr["CXR_ID"]
                                        
                                        # Find any DIAGNOSIS records for this CXR
                                        diagnosis_response = supabase.table("DIAGNOSIS_Table").select("DX_ID").eq("CXR_ID", cxr_id).execute()
                                        
                                        if diagnosis_response.data:
                                            for diagnosis in diagnosis_response.data:
                                                dx_id = diagnosis["DX_ID"]
                                                
                                                # Check if a HEATMAP record exists for this DX_ID
                                                heatmap_check = supabase.table("HEATMAP_Table").select("MAP_ID").eq("DX_ID", dx_id).execute()
                                                
                                                if heatmap_check.data:
                                                    # Update the existing heatmap
                                                    update_data = {
                                                        "MAP_BRGY": barangay_name,
                                                        "MAP_AGE_GROUP": age_group,
                                                        "MAP_SEX": updated_patient.get("PT_SEX", ""),
                                                        "MAP_UPDATED_AT": datetime.now().isoformat()
                                                    }
                                                    
                                                    # Add coordinates if available
                                                    if barangay_name in mandaue_barangay_coordinates:
                                                        lat, lng = mandaue_barangay_coordinates[barangay_name]
                                                        update_data["MAP_LAT"] = lat
                                                        update_data["MAP_LANG"] = lng
                                                    
                                                    supabase.table("HEATMAP_Table").update(update_data).eq("DX_ID", dx_id).execute()
                                
                                st.session_state["edit_patient_mode"] = False
                                st.session_state.pop("form_prefilled", None)
                                st.session_state["save_edit"] = False
                                show_notification(" Patient record updated successfully.", "success")
                                st.rerun()

                            except Exception as e:
                                st.session_state["save_edit"] = False
                                st.session_state["show_save_error"] = f"Error saving changes: {e}"
                                st.rerun()

                    with col_no:
                        if st.button("No", key="save_no"):
                            st.session_state["save_edit"] = False
                            st.rerun()

                save_edit_dialog()
             
        # Fetch all chest X-ray records for the selected patient
        def fetch_all_cases_for_patient(pt_id):
            try:
                response = (
                    supabase.table("RESULT_Table")
                    .select("""
                        RES_DATE,
                        RES_PRESUMPTIVE,
                        RES_CONF_SCORE,
                        RES_STATUS,
                        CHEST_XRAY_Table!inner(
                            CXR_ID,
                            PT_ID,
                            CXR_FILE_PATH
                        )
                    """)
                    .eq("CHEST_XRAY_Table.PT_ID", pt_id)
                    .order("RES_DATE", desc=True)
                    .execute()
                )

                patient_cases = []
                for entry in response.data:
                    chest = entry.get("CHEST_XRAY_Table")
                    if not chest:
                        continue

                    confidence_percent = f"{int(float(entry['RES_CONF_SCORE']) * 100)}%"
                    patient_cases.append({
                        "date": entry["RES_DATE"],
                        "result": entry["RES_PRESUMPTIVE"],
                        "confidence": confidence_percent,
                        "diagnosis": entry["RES_STATUS"],
                        "image_path": chest.get("CXR_FILE_PATH", None)
                    })

                return patient_cases

            except Exception as e:
                show_notification("🚨 Failed to fetch patient x-ray records.", "error")
                st.exception(e)
                return []

            
        # Load all cases related to selected patient
        pt_id = st.session_state.selected_case["pt_id"]
        view_cases = fetch_all_cases_for_patient(pt_id)
            
        view_all_dates = [datetime.fromisoformat(c["date"]).date() for c in view_cases]
        view_oldest_date = min(view_all_dates) if view_all_dates else date.today()

        def reset_view_filters(view_oldest_date):
            st.session_state["view_status_filter"] = "All"
            st.session_state["view_presumptive_filter"] = "All"
            st.session_state["view_date_from"] = view_oldest_date
            st.session_state["view_date_to"] = date.today()
            st.session_state["view_page_num"] = 1
        
        if "last_viewed_pt_id" not in st.session_state or st.session_state.last_viewed_pt_id != pt_id:
            reset_view_filters(view_oldest_date)
            st.session_state.last_viewed_pt_id = pt_id


        # ---------------- Reset Trigger Handler ----------------
        if "view_reset_triggered" not in st.session_state:
            st.session_state["view_reset_triggered"] = False

        
        if st.session_state.view_reset_triggered:
            reset_view_filters(view_oldest_date)
            st.session_state.view_reset_triggered = False
            
        # Initialize all filter values before any UI access

        if "view_status_filter" not in st.session_state:
            st.session_state["view_status_filter"] = "All"

        if "view_presumptive_filter" not in st.session_state:
            st.session_state["view_presumptive_filter"] = "All"

        if "view_date_from" not in st.session_state:
            st.session_state["view_date_from"] = view_oldest_date
            
        if "view_date_to" not in st.session_state:
            st.session_state["view_date_to"] = date.today()

        st.session_state["view_diagnoses"] = {
            f"view_diagnosis_{i}": case["diagnosis"] for i, case in enumerate(view_cases)
        }

        if "view_page_num" not in st.session_state:
            st.session_state.view_page_num = 1

        def apply_view_filters():
            filtered = view_cases

            # Status
            if st.session_state["view_status_filter"] != "All":
                filtered = [c for c in filtered if c["diagnosis"] == st.session_state["view_status_filter"]]

            # Presumptive TB
            if st.session_state["view_presumptive_filter"] != "All":
                target = st.session_state["view_presumptive_filter"]
                filtered = [c for c in filtered if c["result"] == target]

            # Date From
            if st.session_state["view_date_from"]:
                filtered = [c for c in filtered if datetime.fromisoformat(c["date"]).date() >= st.session_state["view_date_from"]]

            # Date To
            if st.session_state["view_date_to"]:
                filtered = [c for c in filtered if datetime.fromisoformat(c["date"]).date() <= st.session_state["view_date_to"]]

            return filtered

        filtered_view_cases = apply_view_filters()

        st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)


        
        if not st.session_state.get("edit_patient_mode", False):
            
            col_status, col_presumptiveTB, col_date_from, col_date_to, col_reset = st.columns([2, 2, 2, 2, 1.5])

            # Status Filter
            with col_status:
                st.markdown('<div class="filter-label">Status</div>', unsafe_allow_html=True)
                prev_status = st.session_state.get("view_status_filter", "All")
                selected_status = st.selectbox(
                    "",
                    ["All", "Pending", "Confirmed Positive", "Confirmed Negative"],
                    index=["All", "Pending", "Confirmed Positive", "Confirmed Negative"].index(prev_status),
                    key="view_status_filter_select"
                )
                if selected_status != prev_status:
                    st.session_state["view_status_filter"] = selected_status
                    st.session_state.view_page_num = 1
                    st.rerun()

            # Presumptive TB
            with col_presumptiveTB:
                st.markdown('<div class="filter-label">Presumptive TB</div>', unsafe_allow_html=True)
                prev_presumptive = st.session_state.get("view_presumptive_filter", "All")
                selected_presumptive = st.selectbox(
                    "", 
                    ["All", "Positive", "Negative"],
                    index=["All", "Positive", "Negative"].index(prev_presumptive),
                    key="view_presumptive_filter_select"
                )
                if selected_presumptive != prev_presumptive:
                    st.session_state["view_presumptive_filter"] = selected_presumptive
                    st.session_state.view_page_num = 1
                    st.rerun()

            # Date From
            with col_date_from:
                st.markdown('<div class="filter-label">Date From</div>', unsafe_allow_html=True)
                prev_date_from = st.session_state.get("view_date_from")
                selected_from = st.date_input(
                    "Start Date", 
                    value=st.session_state.view_date_from, 
                    key="view_date_from_input", 
                    label_visibility="collapsed"
                )
                if selected_from != prev_date_from:
                    st.session_state["view_date_from"] = selected_from
                    st.session_state.view_page_num = 1
                    st.rerun()

            # Date To
            with col_date_to:
                st.markdown('<div class="filter-label">Date To</div>', unsafe_allow_html=True)
                prev_date_to = st.session_state.get("view_date_to")
                selected_to = st.date_input(
                    "End Date", 
                    value=st.session_state.view_date_to, 
                    key="view_date_to_input", 
                    label_visibility="collapsed"
                )
                if selected_to != prev_date_to:
                    st.session_state["view_date_to"] = selected_to
                    st.session_state.view_page_num = 1
                    st.rerun()

            with col_reset:
                st.markdown('<div class="filter-label">&nbsp;</div>', unsafe_allow_html=True)
                if st.button("Reset Filters", key="reset_filters_view"):
                    st.session_state["view_reset_triggered"] = True
                    st.rerun()

            # Display table header for patient's x-ray records
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            col1.markdown("**X-Ray Date**")
            col2.markdown("**Presumptive TB**")
            col3.markdown("**AI Confidence**")
            col4.markdown("**Status**")
            col5.markdown("**Image**")

            # Pagination inside view mode
            view_cases_per_page = 5
            view_total_cases = len(filtered_view_cases)
            view_total_pages = max(1, (view_total_cases - 1) // view_cases_per_page + 1)

            # Ensure current page is valid
            if st.session_state.view_page_num > view_total_pages:
                st.session_state.view_page_num = view_total_pages

            view_current_page = st.session_state.view_page_num
            view_start_idx = (view_current_page - 1) * view_cases_per_page
            view_end_idx = view_start_idx + view_cases_per_page
            cases_to_display = filtered_view_cases[view_start_idx:view_end_idx]

            if not cases_to_display:
                st.markdown("<div style='text-align: center; padding: 2rem; font-weight: bold;'>No matching records found.</div>", unsafe_allow_html=True)
                return

            for i, case in enumerate(cases_to_display):
                cols = st.columns([2, 2, 2, 2, 1])
                with cols[0]:
                    view_display_date = datetime.fromisoformat(case['date']).date().isoformat()
                    st.write(view_display_date)
                with cols[1]:
                    st.write(case['result'])
                with cols[2]:
                    st.write(case['confidence'])
                with cols[3]:
                    status = case['diagnosis']
                    color = "#ffc107" if status == "Pending" else "#4caf50" if status == "Confirmed Negative" else "#f44336"
                    st.markdown(f"<div style='font-weight: bold; color: {color};'>{status}</div>", unsafe_allow_html=True)
                with cols[4]:
                    if st.button("View", key=f"image_view_{case['date']}_{i}"):
                        st.session_state["image_path"] = case["image_path"]  # save image path
                        st.session_state["view_image_mode"] = True
                        st.rerun()
            
            # Pagination controls for view mode table
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.session_state.view_page_num > 1:
                    if st.button("Previous", key="view_prev"):
                        st.session_state.view_page_num -= 1
                        st.rerun()
            with col2:
                st.markdown(f"<div style='text-align: center; font-weight: bold;'>Page {st.session_state.view_page_num} of {view_total_pages}</div>", unsafe_allow_html=True)
            with col3:
                if st.session_state.view_page_num < view_total_pages:
                    if st.button("Next", key="view_next"):
                        st.session_state.view_page_num += 1
                        st.rerun()