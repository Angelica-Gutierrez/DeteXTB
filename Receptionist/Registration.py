# Registration.py

import streamlit as st
import io
import numpy as np
import re
import uuid
import time
from datetime import datetime, date
from PIL import Image, ImageOps
from skimage import filters
from Supabase import supabase
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image as keras_image


IMG_SIZE = (512, 512)

model = st.session_state.model

# --- Constants Initialization ---

# Incidence Rate -> Incidence Rate = (Number of New Cases / Population) * Multiplier
# incidence_rate = 0.00539

# Total city-wide TB cases for 2023
# total_tb_cases_2023 = 2463

# Mandaue City Barangays
mandaue_reg_barangays = [
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


# Initialize default session state values
def init_registration_state():
    DEFAULT_FIELDS = ["reg_first_name", "reg_middle_name", "last_name", "reg_sex", "reg_dob", "reg_phone", "reg_street", "reg_house", "reg_barangay"]
    for field in DEFAULT_FIELDS:
        if field not in st.session_state:
            if field == "reg_dob":
                st.session_state[field] = date(2000, 1, 1)
            elif field == "reg_sex":
                st.session_state[field] = "Male"
            else:
                st.session_state[field] = ""

    st.session_state.setdefault("step", 1)
    st.session_state.setdefault("registration_AI_RESULT", {})
    st.session_state.setdefault("reg_barangay", "Alang-Alang")
    st.session_state.setdefault("light_mode", True)


# Calculate age
def calculate_age(reg_dob):
    today = date.today()
    return today.year - reg_dob.year - ((today.month, today.day) < (reg_dob.month, reg_dob.day))

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

def format_name(name):
    return name.strip().title() if name else ""

def get_formatted_full_name():
    fname = format_name(st.session_state.get("reg_first_name", ""))
    mname = format_name(st.session_state.get("reg_middle_name", ""))
    lname = format_name(st.session_state.get("last_name", ""))
    return f"{fname} {mname} {lname}".strip()

def get_coordinates_from_reg_barangay(reg_barangay_name, show_notification, is_light=True):
    coords = mandaue_barangay_coordinates.get(reg_barangay_name)
    if coords:
        return coords
    else:
        show_notification(f"⚠️ Coordinates for '{reg_barangay_name}' not found.", "warning", is_light=is_light)
        return None, None

# Save or update patient info
def save_patient_info(show_notification, is_light=True):
    try:
        
        fname = format_name(st.session_state.reg_first_name)
        mname = format_name(st.session_state.reg_middle_name)
        lname = format_name(st.session_state.last_name)

        reg_dob = st.session_state.reg_dob
        patient_data = {
            "PT_FNAME": fname,
            "PT_MNAME": mname,
            "PT_LNAME": lname,
            "PT_SEX": st.session_state.reg_sex,
            "PT_DOB": reg_dob.isoformat(),
            "PT_AGE": calculate_age(reg_dob),
            "PT_PHONE": st.session_state.reg_phone,
            "PT_COUNTRY": "Philippines",
            "PT_PROVINCE": "Cebu",
            "PT_CITY": "Mandaue City",
            "PT_BRGY": st.session_state.reg_barangay,
            "PT_STREET": st.session_state.reg_street,
            "PT_HOUSENO": st.session_state.reg_house,
            "PT_ZIPCODE": "6014",
            "USER_ID": st.session_state.get("USER_ID"),
            
        }

        patient_id = st.session_state.get("PATIENT_ID")
        if patient_id:
            # Add PT_UPDATED_AT only when updating
            patient_data["PT_UPDATED_AT"] = datetime.now().isoformat()
            supabase.table("PATIENT_Table").update(patient_data).eq("PT_ID", patient_id).execute()
        else:
            
            now = datetime.now()
            custom_id = f"PT-{now.year}-{now.strftime('%m%d')}-{now.strftime('%H%M%S')}"
            patient_data["PT_ID"] = custom_id
            patient_data["PT_CREATED_AT"] = now.isoformat()
            st.session_state["PATIENT_ID"] = custom_id

            supabase.table("PATIENT_Table").insert(patient_data).execute()

        return st.session_state["PATIENT_ID"]

    except Exception as e:
        show_notification(f"Failed to save patient info: {e}", "error", is_light=is_light)
        return None


# Save all data to Supabase
def save_to_supabase(show_notification, is_light=True):
    try:
        if not st.session_state.get("confirm_save"):
            st.session_state["save_prompt"] = True
            return
        
        # Save patient info (new or update)
        patient_id = save_patient_info(show_notification, is_light=is_light)
        if not patient_id:
            show_notification("Failed to save patient info.", "error", is_light=is_light)
            return

        patient_id = st.session_state.get("PATIENT_ID")

        # Save uploaded file to disk and insert CXR record
        uploaded_bytes = st.session_state.get("registration_uploaded_file_bytes")
        if uploaded_bytes:
            full_name_raw = f"{st.session_state.get('reg_first_name', '')} {st.session_state.get('reg_middle_name', '')} {st.session_state.get('last_name', '')}"
            full_name_clean = full_name_raw.strip().upper().replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{full_name_clean}_{timestamp}.png"
            storage_path = f"patient_{patient_id}/{filename}"

            # Upload to Supabase Storage
            supabase.storage.from_("xray-uploads").upload(
                storage_path,
                uploaded_bytes,
                {"content-type": "image/png"}
            )
            SUPABASE_URL = "https://xaxgkufwhemjoofcvtri.supabase.co"

            public_url = f"{SUPABASE_URL}/storage/v1/object/public/xray-uploads/{storage_path}"

            # Insert into CHEST_XRAY_Table
            cxr_res = supabase.table("CHEST_XRAY_Table").insert({
                "CXR_FILE_PATH": public_url,
                "CXR_UPL_DATE": datetime.now().isoformat(),
                "PT_ID": patient_id,
                "USER_ID": st.session_state.get("USER_ID")
            }).execute()

            cxr_id = cxr_res.data[0]["CXR_ID"]
            st.session_state["CXR_ID"] = cxr_id
        else:
            show_notification("No X-ray file found to save.", "error", is_light=is_light)
            return

        # Save Result now that we have a valid CXR_ID
        label, confidence = st.session_state.registration_AI_RESULT.values()
        supabase.table("RESULT_Table").insert({
            "CXR_ID": st.session_state["CXR_ID"],
            "RES_PRESUMPTIVE": label,
            "RES_CONF_SCORE": confidence / 100,
            "RES_DATE": datetime.now().isoformat(),
            "RES_STATUS": "Pending"
        }).execute()

        show_notification("Patient record successfully saved.", "success", is_light=is_light )
        keys_to_clear = [
            "reg_first_name", "reg_middle_name", "last_name", "reg_sex", "reg_dob", "reg_phone",
            "reg_street", "reg_house", "reg_barangay", "PATIENT_ID", "CXR_ID",
            "uploaded_file", "registration_uploaded_file_bytes", "registration_uploaded_file_name",
            "registration_AI_RESULT", "step", "confirm_save", "save_prompt"
        ]
        for key in keys_to_clear:
            st.session_state.pop(key, None)

        st.session_state["saved"] = True
        st.session_state["step"] = 1
        st.rerun()

    except Exception as e:
        show_notification(f"Failed to save record: {e}", "error", is_light=is_light)


def Registration(is_light=True):
    init_registration_state() 
    st.session_state.setdefault("step", 1)
    st.session_state.setdefault("reg_barangay", "Alang-Alang")
    
    if is_light is None:
        is_light = st.session_state["light_mode"]

    # --- Theme-based color variables ---
    bg_color = "white" if is_light else "#0e0e0e"
    text_color = "black" if is_light else "white"
    header_color = "#1c1c1c" if is_light else "white"
    input_bg = "white" if is_light else "#1a1a1a"
    input_border = "black" if is_light else "white"
    placeholder_color = "#b0b0b0" if is_light else "#cccccc"
    select_bg = "white" if is_light else "#1a1a1a"
    select_hover = "#f0f0f0" if is_light else "#2a2a2a"
    card_bg = "#f0f0f5" if is_light else "#1c1c1c"
    calendar_dropdown_bg = "white" if is_light else "#222"
    calendar_border = "black" if is_light else "none"
    button_color = "#d32f2f"
    button_hover = "#f3a5a5"

    notification_container = st.empty()
    
    def show_notification(message, type="info",is_light=True, duration=6):
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

    [data-testid="stDialog"] button[aria-label="Close"] {{
        display: none !important;
        }}

    [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
            background-color: {bg_color} !important;
            color: {text_color} !important;
        }}

    
    label {{
        color: {text_color} !important;
        font-weight: 600;
    }}

    .block-container {{
            padding-top: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }}


    h1, h2, h3, h4, h5, h6 {{ color: {header_color} !important; }}
        html, body, [class*="css"] {{
        color: {header_color} !important;
        font-family: 'Arial', sans-serif;
        }}

    .stTextInput > div {{
            background-color: {input_bg} !important;
            border-radius: 25px !important;
            border: 1px solid {input_border} !important;
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
        caret-color: {"black" if is_light else "white"} !important;
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
        caret-color: {"black" if is_light else "white"} !important;
    }}

    .stSelectbox li:hover {{
        background-color: {select_hover} !important;
    }}

    /* Ensure Next buttons are aligned right */
        .st-key-go_step_2,
        .st-key-step2_next,
        .st-key-step3_next {{
            text-align: right;
        }}

    /* Custom button styling ONLY for main content, NOT sidebar */
        .block-container div[data-testid="stButton"] > button,
        .block-container div[data-testid^="FormSubmitter"] button,
        div[data-testid="stDialog"] div[data-testid="stButton"] > button,
        div[data-testid="stDialog"] div[data-testid^="FormSubmitter"] button {{
            background-color: {button_color} !important;
            color: white !important;
            border: none !important;
            border-radius: 25px !important;
            padding: 0.5em 1.5em !important;
            font-weight: bold !important;
            transition: background-color 0.3s ease;
            cursor: pointer !important;
        }}

        .block-container div[data-testid="stButton"] > button:hover,
        .block-container div[data-testid^="FormSubmitter"] button:hover,
        div[data-testid="stDialog"] div[data-testid="stButton"] > button:hover,
        div[data-testid="stDialog"] div[data-testid^="FormSubmitter"] button:hover {{
            background-color: {button_hover} !important;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
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
            left: 12%;
            right: 12%;
            height: 1px;
            background-color: #990000;
            z-index: 1;
            opacity: 0.9;
        }}

        .upload-xray-container {{
            background-color: {card_bg};
            padding: 10px;
            border-radius: 15px;
            color: {"black" if is_light else "white"};
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


                      
        .ai-result-container {{
            background-color: {card_bg};
            padding: 25px;
            border-radius: 15px;
            margin-top: 20px;
            color: {"black" if is_light else "white"};
        }}

        .ai-result-container h5,
        .ai-result-container p {{
             color: {"black" if is_light else "white"};
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

</style>

""", unsafe_allow_html=True)
      
    
    # Theme toggle
    col_title, col_toggle = st.columns([6, 1])
    with col_title:
        st.markdown(
            "<h4 style='margin-bottom: 15px;'>Patient Registration & X-ray Upload</h4>",
            unsafe_allow_html=True
        )
    with col_toggle:
        new_toggle = st.toggle("🌙", value=st.session_state["light_mode"], key="theme_toggle", label_visibility="collapsed")
        if new_toggle != st.session_state["light_mode"]:
            st.session_state["query_input"] = st.session_state.get("query_input", "")
            st.session_state["light_mode"] = new_toggle
            st.rerun()

    def validate_step1():
        errors = []
        warnings = []

        field_labels = {
            "reg_first_name": "First Name",
            "reg_middle_name": "Middle Name",
            "last_name": "Last Name",
            "reg_sex": "Sex",
            "reg_dob": "Date of Birth",
            "reg_phone": "Phone Number",
            "reg_street": "Street",
            "reg_house": "House Number"
        }

        required_fields = ["reg_first_name", "last_name", "reg_sex", "reg_dob", "reg_phone", "reg_street", "reg_house"]

        name_pattern = re.compile(r"^[A-Za-z\s\-']+$")

        # --- 1. Check required fields ---
        for field in required_fields:
            value = st.session_state.get(field, "")
            if isinstance(value, str):
                value = value.strip()
            if not value:
                errors.append(f"{field_labels[field]} is required")

        # --- 2. Name validation ---
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

        validate_name("reg_first_name", required=True)
        validate_name("last_name", required=True)
        validate_name("reg_middle_name", required=False)

        # --- 3. Phone validation ---
        reg_phone = str(st.session_state.get("reg_phone", "")).strip()
        if reg_phone:
            if len(reg_phone) != 11 or not reg_phone.startswith("09") or not reg_phone.isdigit():
                errors.append("Phone Number must be 11 digits and start with '09'")
            else:
                st.session_state["reg_phone"] = reg_phone
        else:
            errors.append("Phone Number is required")

        # --- 4. Street formatting ---
        reg_street = st.session_state.get("reg_street", "")
        if reg_street:
            st.session_state["reg_street"] = reg_street.strip().title()

        # --- 5. House number validation ---
        reg_house = st.session_state.get("reg_house", "")
        if reg_house:
            if not str(reg_house).isdigit():
                errors.append("House Number must be numeric")
        else:
            errors.append("House Number is required")

        # --- 6. Duplicate checks ---
        if not st.session_state.get("PATIENT_ID"):
            fname = format_name(st.session_state.reg_first_name)
            mname = format_name(st.session_state.reg_middle_name)
            lname = format_name(st.session_state.last_name)
            dob = st.session_state.reg_dob.isoformat() if st.session_state.get("reg_dob") else None

            if dob:
                try:
                    # 6.1 Full match: First + Middle + Last + DOB
                    full_query = (
                        supabase.table("PATIENT_Table")
                        .select("PT_ID")
                        .ilike("PT_FNAME", fname)
                        .ilike("PT_LNAME", lname)
                        .eq("PT_DOB", dob)
                    )

                    # Only include middle name in full match if it's > 1 char (not an initial)
                    if mname and len(mname.replace(".", "")) > 1:
                        full_query = full_query.ilike("PT_MNAME", mname)
                    else:
                        full_query = full_query.ilike("PT_MNAME", "")  # Treat blank as blank

                    full_result = full_query.execute()

                    if full_result.data:
                        errors.append("⚠️ A patient with the same full name and date of birth already exists.")
                    else:
                        # 6.2 Near match: First + Last + DOB (ignore middle name)
                        near_match_query = (
                            supabase.table("PATIENT_Table")
                            .select("PT_ID, PT_FNAME, PT_MNAME, PT_LNAME")
                            .ilike("PT_FNAME", fname)
                            .ilike("PT_LNAME", lname)
                            .eq("PT_DOB", dob)
                        )

                        near_result = near_match_query.execute()
                        if near_result.data:
                            warnings.append("⚠ Possible duplicate: Same first, last name and birth date, but different middle name.")

                except Exception as e:
                    errors.append(f"Error checking for duplicate patient: {e}")

        # --- 7. Show messages ---
        if errors:
            show_notification("Please check the following fields:\n- " + "\n- ".join(errors), "error")
            return False

        if warnings:
            show_notification("\n".join(warnings), "warning")

        return True

    # --- Step Navigation ---
    def step_class(n):
        try:
            return "" if int(n) <= int(st.session_state.step) else "inactive"
        except ValueError:
            return "inactive"

    st.markdown(f"""
        <div class="step-container">
            <div class="step-line"></div>
            <div class="step {step_class(1)}">
                <span class="number">1</span>
                <span class="label">Patient Information</span>
            </div>
            <div class="step {step_class(2)}">
                <span class="number">2</span>
                <span class="label">X-ray Upload</span>
            </div>
            <div class="step {step_class(3)}">
                <span class="number">3</span>
                <span class="label">AI Processing & Result</span>
            </div>
            <div class="step {step_class(4)}">
                <span class="number">4</span>
                <span class="label">Finalize & Save</span>
            </div>
        </div>
    """, unsafe_allow_html=True)


    if "registration_xray_uploaded" not in st.session_state:
        st.session_state["registration_xray_uploaded"] = False


    # Step 1: Form
    if st.session_state.step == 1:
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 3, 3, 3])

            with col1:
                st.markdown("<p style='margin-top: 35px;'>Name:</p>", unsafe_allow_html=True)
            with col2:
                st.session_state.reg_first_name = col2.text_input("", placeholder="First Name", value=st.session_state.reg_first_name)
            with col3:
                st.session_state.reg_middle_name = col3.text_input("", placeholder="Middle Name", value=st.session_state.reg_middle_name)
            with col4:
                st.session_state.last_name = col4.text_input("", placeholder="Last Name", value=st.session_state.last_name)

            col1, col2, col3, col4, col5, col6 = st.columns([1, 4, 2, 4, 1, 3])
            with col1:
                st.markdown("<p style='margin-top: 35px;'>Sex:</p>", unsafe_allow_html=True)
            with col2:
                st.session_state.reg_sex = col2.selectbox("", ["Male", "Female"], index=["Male", "Female"].index(st.session_state.reg_sex))
            with col3:
                st.markdown("<p style='margin-top: 35px;'>Date of Birth:</p>", unsafe_allow_html=True)
            with col4:
                st.session_state.reg_dob = col4.date_input("", value=st.session_state.reg_dob, min_value=date(1800, 1, 1), max_value=date.today())
            with col5:
                st.markdown("<p style='margin-top: 35px;'>Age:</p>", unsafe_allow_html=True)
            with col6:
                st.text_input("", value=str(calculate_age(st.session_state.reg_dob)), disabled=True)

            col1, col2, col3 = st.columns([1, 3, 3])
            with col1:
                st.markdown("<p style='margin-top: 35px;'>Phone Number:</p>", unsafe_allow_html=True)
            with col2:
                st.session_state.reg_phone = st.text_input("", placeholder="09XXXXXXXXX",max_chars=11, value=st.session_state.reg_phone)
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
                st.session_state.reg_street = st.text_input("Street", placeholder="Street Name", value=st.session_state.reg_street)
            with col2:
                st.session_state.reg_house = st.text_input("House Number", placeholder="House Number", value=st.session_state.reg_house)
            with col3:
                reg_barangay_index = mandaue_reg_barangays.index(st.session_state.reg_barangay) if st.session_state.reg_barangay in mandaue_reg_barangays else 0
                st.session_state.reg_barangay = st.selectbox("Barangay", mandaue_reg_barangays, index=reg_barangay_index)
            with col4:
                st.text_input("ZIP Code", value="6014", disabled=True)

            cancel_col, next_col = st.columns([11, 1])
            
            # Check if any fields are filled before showing cancel
            has_input = any([
                st.session_state.get("reg_first_name", "").strip(),
                st.session_state.get("reg_middle_name", "").strip(),
                st.session_state.get("last_name", "").strip(),
                st.session_state.get("reg_phone", "").strip(),
                st.session_state.get("reg_street", "").strip(),
                st.session_state.get("reg_house", "").strip(),
                st.session_state.get("reg_barangay", "").strip() and st.session_state.get("reg_barangay") != mandaue_reg_barangays[0]
            ])

            # --- Cancel & Next buttons (conditionally shown) ---
            if has_input:
                if cancel_col.button("Cancel", key="step1_cancel"):
                    st.session_state["cancel_prompt"] = True

                if next_col.button("Next", key="step1_next"):
                    if validate_step1():
                        # Check if there's already an uploaded file
                        if "registration_uploaded_file_bytes" in st.session_state and st.session_state.registration_uploaded_file_bytes:
                            st.session_state.step = 3  # Skip directly to Step 3 if there is
                            st.session_state["registration_analyze_triggered"] = True
                        else:
                            st.session_state.step = 2  # Go to Step 2 if not yet
                        st.rerun()


    # --- Cancel confirmation dialog ---
    if st.session_state.get("cancel_prompt"):

        @st.dialog("Confirm Cancel")
        def cancel_dialog():
            st.write("Are you sure you want to cancel this patient’s record? All entered information or uploaded files will be lost.")

            col1, spacer, col2 = st.columns([1, 3.5, 1]) 

            with col1:
                if st.button("Yes", key="confirm_cancel_yes"):
                    # Clear Step 1 fields
                    for key in [
                        "reg_first_name", "reg_middle_name", "last_name", "reg_sex", "reg_dob",
                        "reg_phone", "reg_street", "reg_house", "reg_barangay", "PATIENT_ID"
                    ]:
                        st.session_state.pop(key, None)
                    st.session_state["cancel_prompt"] = False
                    st.rerun()

            with col2:
                if st.button("No", key="confirm_cancel_no"):
                    st.session_state["cancel_prompt"] = False
                    st.rerun()

        cancel_dialog()

    # Step 2
    elif st.session_state.step == 2:
        st.markdown("<br>", unsafe_allow_html=True)

        full_name = get_formatted_full_name()
        age = str(calculate_age(st.session_state.get("reg_dob", date.today())))
        reg_sex = st.session_state.get("reg_sex", "N/A")
        reg_phone = st.session_state.get("reg_phone", "N/A")

        st.markdown(f"""
        <div class="upload-xray-container">
            <div style="display: flex; flex-wrap: wrap; gap: 40px;">
                <p style="margin: 10px;">Upload X-ray for:</p>
                <p style="margin: 10px;"><strong>{full_name}</strong></p>
                <p style="margin: 10px;"><strong>{age}</strong></p>
                <p style="margin: 10px;"><strong>{reg_sex}</strong></p>
                <p style="margin: 10px;"><strong>{reg_phone}</strong></p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if "registration_xray_warning_shown" not in st.session_state:
            st.session_state.registration_xray_warning_shown = False

        # File uploader
        registration_uploaded = st.file_uploader("", type=["png", "jpg", "jpeg", "bmp"], 
                                    key="registration_xray_uploader_step2")

        # Detect if the uploader was cleared
        if registration_uploaded is None:
            st.session_state.registration_xray_uploaded = False
            st.session_state.registration_xray_warning_shown = False
            st.session_state.pop("registration_uploaded_file_bytes", None)

        # When a file is uploaded
        if registration_uploaded:
            # Reset warning for new upload
            if st.session_state.get("registration_last_uploaded_file_name") != registration_uploaded.name:
                st.session_state.registration_xray_warning_shown = False
                st.session_state["registration_last_uploaded_file_name"] = registration_uploaded.name

            try:
                img = Image.open(registration_uploaded).convert("RGB")

                # Strict validation
                if is_xray_like(img):
                    st.session_state.registration_xray_uploaded = True
                    st.session_state.registration_uploaded_file_bytes = registration_uploaded.getvalue()
                    st.session_state.registration_xray_warning_shown = False
                else:
                    # Relaxed validation with warning
                    if is_xray_like_relaxed(img):
                        if not st.session_state.registration_xray_warning_shown:
                            show_notification("This image deviates from standard appearance but may still represent a valid chest X-ray. Please proceed with careful analysis.", "warning")
                            st.session_state.registration_xray_warning_shown = True
                        st.session_state.registration_xray_uploaded = True
                        st.session_state.registration_uploaded_file_bytes = registration_uploaded.getvalue()
                    else:
                        # If the image fails to fit in the validations
                        show_notification("This image does not meet the criteria for a valid chest X-ray. Please upload a different image.", "error")
                        st.session_state.registration_xray_uploaded = False
                        st.session_state.registration_xray_warning_shown = False
                        st.session_state.pop("registration_uploaded_file_bytes", None)

            except Exception as e:
                show_notification(f"Error processing image: {e}", "error")
                st.session_state.registration_xray_uploaded = False
                st.session_state.registration_xray_warning_shown = False
                st.session_state.pop("registration_uploaded_file_bytes", None)

        # Back and Next buttons
        back_col, next_col = st.columns([11, 1])
        if back_col.button("Back", key="step2_back"):
            st.session_state.step = 1
            st.rerun()

        # Show Next button only if a valid or relaxed X-ray is uploaded
        if st.session_state.get("registration_xray_uploaded", False):
            if next_col.button("Next", key="step2_next"):
                st.session_state.step = 3
                st.session_state.registration_analyze_triggered = True
                st.rerun()
                          

   # Step 3
    elif st.session_state.step == 3:
        st.markdown("<br>", unsafe_allow_html=True)

        full_name = get_formatted_full_name()
        st.markdown(f"""
            <div class="upload-xray-container">
                <div style="display: flex; flex-wrap: wrap; gap: 40px;">
                    <p style="margin: 10px 20px 10px 5px;">Patient:</p>
                    <p style="margin: 10px 20px 10px 0px;"><strong>{full_name}</strong></p>
                    <p style="margin: 10px 20px 10px 0px;"><strong>{calculate_age(st.session_state.get('reg_dob', date.today()))}</strong></p>
                    <p style="margin: 10px 20px 10px 0px;"><strong>{st.session_state.get('reg_sex', '')}</strong></p>
                    <p style="margin: 10px 20px 10px 0px;"><strong>{st.session_state.get('reg_phone', '')}</strong></p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- Only analyze the first time ---
        if st.session_state.get("registration_analyze_triggered"):
            if "registration_uploaded_file_bytes" in st.session_state and st.session_state.registration_uploaded_file_bytes:
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

                uploaded_file = io.BytesIO(st.session_state.registration_uploaded_file_bytes)
                label, confidence = predict_tb(uploaded_file)
                st.session_state["registration_AI_RESULT"] = {"label": label, "confidence": confidence}
                st.session_state["registration_analyze_triggered"] = False
                st.rerun()       

        # --- After analysis ---
        label, confidence = st.session_state.registration_AI_RESULT.values()

        col_img, col_result = st.columns([3, 2])

        # --- Left: X-ray Image ---
        with col_img:
            if "registration_uploaded_file_bytes" in st.session_state and st.session_state.registration_uploaded_file_bytes:
                image = Image.open(io.BytesIO(st.session_state.registration_uploaded_file_bytes))
                
                
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
                    key= "view_mode1_reg"
                )

                if view_mode == "   🔍   ":
                    from streamlit_image_zoom import image_zoom
                    image_zoom(image, zoom_factor=2)

                elif view_mode == "   🖼️   ":
                    st.image(image, use_container_width=False)

                else:
                    st.image(image, use_container_width=False)


            else:
                st.markdown("No image uploaded.")

        # --- Right: AI Result ---
        with col_result:
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
                    <p>Presumptive TB Result: <strong class="{presumptive_result_class}">{label}</strong></p>
                    <p>AI Confidence Level: <strong class="{confidence_class}">{confidence}%</strong></p>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            col_spacer, col_button = st.columns([1, 3])
            with col_button:
                if st.button("🔄 Reupload X-ray", key="step3_reupload"):
                    st.session_state.pop("registration_uploaded_file_bytes", None)
                    st.session_state.pop("registration_uploaded_file_name", None)
                    st.session_state.pop("registration_AI_RESULT", None)
                    st.session_state["registration_xray_uploaded"] = False
                    st.session_state.step = 2
                    st.rerun()

        # Navigation buttons
        back_col, next_col = st.columns([11, 1])
        if back_col.button("Back", key="step3_back"):
            st.session_state.step = 1
            st.rerun()
        if next_col.button("Next", key="step3_next"):
            st.session_state.step = 4
            st.rerun()


    # Step 4
    elif st.session_state.step == 4:
        st.markdown("<br>", unsafe_allow_html=True)

        full_name = get_formatted_full_name()

        st.markdown(f"""
            <div class="upload-xray-container">
                <div style="display: flex; flex-wrap: wrap; gap: 40px;">
                    <p style="margin: 10px 20px 10px 5px;">Patient:</p>
                    <p style="margin: 10px 20px 10px 0px;"><strong>{full_name}</strong></p>
                    <p style="margin: 10px 20px 10px 0px;"><strong>{calculate_age(st.session_state.get('reg_dob', date.today()))}</strong></p>
                    <p style="margin: 10px 20px 10px 0px;"><strong>{st.session_state.get('reg_sex', '')}</strong></p>
                    <p style="margin: 10px 20px 10px 0px;"><strong>{st.session_state.get('reg_phone', '')}</strong></p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        

        col_img, col_result = st.columns([3, 2])

        # --- Left Side ---
        with col_img:
            if "registration_uploaded_file_bytes" in st.session_state and st.session_state.registration_uploaded_file_bytes:
                uploaded_file = io.BytesIO(st.session_state.registration_uploaded_file_bytes)
                image = Image.open(uploaded_file)

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
                    key= "view_mode2_reg"
                )

                if view_mode == "   🔍   ":
                    from streamlit_image_zoom import image_zoom
                    image_zoom(image, zoom_factor=2)

                elif view_mode == "   🖼️   ":
                    st.image(image, use_container_width=False)
                
                else:
                    st.image(image, use_container_width=False)
                    
            else:
                st.markdown("No image uploaded.")

            st.markdown("</div>", unsafe_allow_html=True)


        # --- Right Side: AI Result ---
        label, confidence = st.session_state.registration_AI_RESULT.values()

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

        with col_result:
            st.markdown(f"""
                <div class="ai-result-container">
                    <p>X-Ray Date: <strong>{datetime.now().strftime('%m-%d-%Y')}</strong></p>
                    <p>Presumptive TB Result: <strong class="{presumptive_result_class}">{label}</strong></p>
                    <p>AI Confidence Level: <strong class="{confidence_class}">{confidence}%</strong></p>
                    <p>Status: <strong class="highlight-orange">Pending</strong></p>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

        back_col, save_col = st.columns([11, 1])
        if back_col.button("Back", key="step4_back"):
            st.session_state.step = 3
            st.rerun()
        if save_col.button("Save", key="step4_save"):
            st.session_state["save_prompt"] = True 

    # Confirm save dialog
    if st.session_state.get("save_prompt"):
        @st.dialog("Confirm Save", width="small")
        def confirm_save_dialog():
            st.write("Are you sure you want to save this patient\'s record?")

            confirm_col, spacer, cancel_col = st.columns([1, 3.5, 1]) 

            with confirm_col:
                if st.button("Yes", key="confirm_yes"):
                    st.session_state["confirm_save"] = True
                    st.session_state["save_prompt"] = False
                    save_to_supabase(show_notification, is_light)
                    st.rerun()

            with cancel_col:
                if st.button("No", key="confirm_no"):
                    st.session_state["confirm_save"] = False
                    st.session_state["save_prompt"] = False
                    st.rerun()
        
        confirm_save_dialog()