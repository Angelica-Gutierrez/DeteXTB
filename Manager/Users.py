import streamlit as st
import time
from datetime import datetime, date
from Supabase import supabase
import re

def Users(is_light=True):
    # --- Session State Initialization ---
    if "light_mode" not in st.session_state:
        st.session_state["light_mode"] = True

    if is_light is None:
        is_light = st.session_state["light_mode"]

    if "search_bar" not in st.session_state:
        st.session_state.search_bar = ""

    if "show_form" not in st.session_state:
        st.session_state["show_form"] = False

    if 'page_num' not in st.session_state:
        st.session_state.page_num = 1

    if 'prev_search' not in st.session_state:
        st.session_state.prev_search = ""


    # --- Declare global color variables ---
    bg_color = "white" if is_light else "#0e0e0e"
    text_color = "black" if is_light else "white"
    input_bg = "white" if is_light else "#1a1a1a"
    border_color = "black" if is_light else "white"
    header_bg = "#f0f2f6" if is_light else "#222"
    hover_bg = "#f0f0f0" if is_light else "#2a2a2a"
    placeholder_color = "#b0b0b0" if is_light else "#cccccc"
    button_color = "#d32f2f"
    button_hover = "#f3a5a5"
    error_text = "#b71c1c" if is_light else "#ff8a80"
    pwIcon_color = "#0F0F0F" if is_light else "white"
    
    notification_container = st.empty()
    
    def show_notification(message, type="info", duration=4):
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

    # --- Styles ---
    st.markdown (f"""<style>
    .stApp {{ padding-top: 0rem !important; }}
        .block-container {{
            padding-top: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }}
        h1, h2, h3, h4, h5, h6 {{ color: {text_color} !important; }}
        html, body, [class*="css"] {{
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

        .stTextInput > div {{
            background-color: {input_bg} !important;
            border-radius: 25px !important;
            border: 1px solid {border_color} !important;
        }}

        .stTextInput input {{
            background-color: {input_bg} !important;       
            color: {text_color} !important;
            caret-color: {"black" if is_light else "white"} !important;
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
            border: 1px solid {border_color} !important;
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
            background-color: {input_bg} !important;
            border: 1px solid {border_color} !important;
            color: {text_color} !important;
            border-radius: 25px !important;
        }}

        .stSelectbox div[role="listbox"] {{
            background-color: {input_bg} !important;
            border: 1px solid {border_color} !important;
            color: {text_color} !important;
        }}

        .stSelectbox li:hover {{
            background-color: {hover_bg} !important;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
        }}

    
        /* Scrollbar styling */
        .table-scroll-container::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        .table-scroll-container::-webkit-scrollbar-thumb {{
            background-color: #CD0000;
            border-radius: 4px;
        }}
        
        .table-scroll-container::-webkit-scrollbar-track {{
            background-color: transparent;
        }}
    
        div[data-testid="column"] > div {{
            padding-top: 0rem !important;
            margin-top: -1rem !important;
        }}
        .stMarkdown label {{ 
            color: {text_color} !important; 
            font-weight: bold; 
            margin-bottom: 0.5rem; 
            display: block; 
        }}

        div[data-testid="stForm"] {{
            border: 'white' !important;
            border-radius: 8px !important;
            padding: 0rem !important;
            margin-top: -1rem !important;
            margin-bottom: 1rem !important;
            position: relative;
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
        }}

        div[data-testid="stAlert"] {{  
            border-radius: 10px !important;
            padding: 1rem 1.2rem !important;
            margin-top: 1rem;
        }}

        /* Ensure text color inside alert box is styled */
        div[data-testid="stAlert"] * {{
            color: {error_text} !important;
            font-weight: 500 !important;
        }}

        /* Password toggle */
        div[data-baseweb="input"] button {{
            background-color: {'white' if is_light else '#0F0F0F'} !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 0 !important;
        }}

        div[data-baseweb="input"] button > svg {{
            background-color: {'white' if is_light else '#0F0F0F'} !important;
            fill: {pwIcon_color} !important;
            width: 1.2rem !important;
            height: 1.2rem !important;
        }}

        input:disabled,
            .stTextInput input:disabled,
            div[data-testid="stTextInput"] input[disabled] {{
            background-color: {"white" if is_light else "#1a1a1a"} !important;
            color: {"black" if is_light else "white"} !important;
            opacity: 1 !important;
            -webkit-text-fill-color: {"black" if is_light else "white"} !important; /* <-- for Safari */
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
        
    </style>""", unsafe_allow_html=True)


    # --- Helper Functions applied ----

    # --- Definining the Barangays per City ---
    barangays_per_city = {
        "Mandaue City": ["Alang-alang", "Bakilid", "Banilad", "Basak", "Cabancalan", "Cambaro", "Canduman", "Casili", "Casuntingan", "Centro (Poblacion)", "Cubacub", "Guizo", "Ibabao-Estancia", "Jagobiao", "Labogon", "Looc", "Maguikay", "Mantuyong", "Opao", "Pakna-an", "Pagsabungan", "Subangdaku", "Tabok", "Tawason", "Tingub", "Tipolo", "Umapad"],
        "Lapu-Lapu City": ["Agus", "Babag", "Bankal", "Baring", "Basak", "Buaya", "Calawisan", "Canjulao", "Caubian", "Caw-oy", "Cawhagan", "Gun-ob", "Ibo", "Looc", "Mactan", "Maribago", "Marigondon", "Pajac", "Pajo", "Pangan-an", "Poblacion", "Punta Engaño", "Pusok", "Sabang", "San Vicente", "Santa Rosa", "Subabasbas", "Talima", "Tingo", "Tungasan"],
        "Cebu City": ["Adlaon", "Agsungot", "Apas", "Babag", "Bacayan", "Banilad", "Basak Pardo", "Basak San Nicolas", "Binaliw", "Bonbon", "Budlaan", "Buhisan", "Bulacao", "Busay", "Calamba", "Cambinocot", "Capitol Site", "Carreta", "Central", "Cogon Pardo", "Cogon Ramos", "Day-as", "Duljo Fatima", "Ermita", "Guadalupe", "Guba", "Hipodromo", "Inayawan", "Kalubihan", "Kamagayan", "Kamputhaw", "Kasambagan", "Kinasang-an", "Lahug", "Libertad", "Lisbon", "Lorega-San Miguel", "Luz", "Mabini", "Mabolo", "Malubog", "Mambaling", "Pahina Central", "Pahina San Nicolas", "Pamutan", "Pari-an", "Paril", "Pasil", "Pit-os", "Poblacion Pardo", "Pulangbato", "Sambag I", "Sambag II", "San Antonio", "San Jose", "San Nicolas Central", "San Roque", "Santa Cruz", "Santo Niño", "Sapangdaku", "Sawang Calero", "Sinait", "Sirao", "Suba", "Suba Poblacion", "Sudlon I", "Sudlon II", "Tagba-o", "Talamban", "Taptap", "Tejero", "Tinago", "Tisa", "To-ong", "T. Padilla", "Zapatera"]
    }

    # --- Definining the ZIP Codes per City ---
    zip_codes_per_city = {
        "Mandaue City": "6014",
        "Lapu-Lapu City": "6015",
        "Cebu City": "6000"
    }

    # Function to fetch receptionists
    def get_receptionist_db():
        resp = supabase.table("USER_Table") \
                         .select("*") \
                         .eq("USER_ROLE", "Receptionist") \
                         .execute()
        return resp.data or []

    # Function to delete receptionists
    def delete_receptionist_db(user_id):
        supabase.table("USER_Table").delete().eq("USER_ID", user_id).execute()
        show_notification("Receptionist deleted.", "success")
        st.rerun()

    # Function to add receptionists
    def add_receptionist_db(record):
        supabase.table("USER_Table").insert(record).execute()
        show_notification("New receptionist added!", "success")
        st.session_state.show_form = False
        st.session_state.pop("step1_data", None)
        st.session_state.pop("step2_data", None)
        st.rerun()

    # Function to confirm update cancellation
    def cancel_confirmation(flag_key: str, on_confirm_callback=None):
        @st.dialog("Cancel Confirmation")
        def cancel_dialog():
            st.write("Are you sure you want to cancel this user's record? All entered information will be lost.")

            confirm_col, spacer, cancel_col = st.columns([1, 3.5, 1]) 

            with confirm_col:
                if st.button("Yes", key=f"{flag_key}_yes"):
                    st.session_state[flag_key] = False
                    if on_confirm_callback:
                        on_confirm_callback()
                    st.rerun()
            with cancel_col:
                if st.button("No", key=f"{flag_key}_no"):
                    st.session_state[flag_key] = False
                    st.rerun()

        cancel_dialog()

    def cancel_form():
        st.session_state.show_form = False
        st.session_state.form_step = 1
        keys_to_clear = [
            "fname", "mname", "lname", "sex", "username", "password",
            "dob_input", "phone", "email", "country", "province", "city",
            "barangay", "street", "house_number", "zip_code", "step1_data", "step2_data"
        ]
        for key in keys_to_clear:
            st.session_state.pop(key, None)

    # Function to confirm save action
    def save_confirmation(flag_key: str, on_confirm_callback=None):
        @st.dialog("Save Confirmation")
        def save_dialog():
            st.write("Are you sure you want to save this user’s record?")

            confirm_col, spacer, cancel_col = st.columns([1, 3.5, 1])  

            with confirm_col:
                if st.button("Yes", key=f"{flag_key}_yes"):
                    st.session_state[flag_key] = False
                    if on_confirm_callback:
                        on_confirm_callback()
            with cancel_col:
                if st.button("No", key=f"{flag_key}_no"):
                    st.session_state[flag_key] = False
                    st.rerun()
        save_dialog()

    def process_user_creation():
        step1 = st.session_state.step1_data
        dob = st.session_state.get("dob_input")
        phone = st.session_state.get("phone", "").strip()
        email = st.session_state.get("email", "").strip()
        city = st.session_state.get("city", "")
        barangay = st.session_state.get("barangay", "")
        street = st.session_state.get("street", "").strip().title()
        house_number = st.session_state.get("house_number", "").strip()
        zip_code = zip_codes_per_city.get(city, "")
        age = calculate_age(dob)

        user_data = {
            "USER_FNAME": step1["fname"],
            "USER_MNAME": step1["mname"],
            "USER_LNAME": step1["lname"],
            "USER_SEX": step1["sex"],
            "USER_DOB": dob.isoformat(),
            "USER_AGE": age,
            "USER_COUNTRY": "Philippines",
            "USER_PROVINCE": "Cebu",
            "USER_CITY": city,
            "USER_BRGY": barangay,
            "USER_STREET": street,
            "USER_HOUSENO": house_number,
            "USER_ZIPCODE": zip_code,
            "USER_PHONE": phone,
            "USER_EMAIL": email,
            "USER_USERNAME": step1["username"],
            "USER_ROLE": step1["role"],
            "USER_PASSWORD": step1["password"],
        }

        # Validation
        missing_fields = []
        for field_name, val in [
            ("Phone Number", phone),
            ("Email Address", email),
            ("City", city),
            ("Barangay", barangay),
            ("Street", street),
            ("House Number", house_number),
            ("ZIP Code", zip_code),
        ]:
            if not val:
                missing_fields.append(field_name)

        if missing_fields:
            show_notification(f"Please fill all required fields: {', '.join(missing_fields)}", "error")
        elif not is_valid_phone(phone):
            show_notification("Phone number must start with '09' and be exactly 11 digits (e.g., 09XXXXXXXXX).", "error")
        elif not is_valid_email(email):
            show_notification("Please enter a valid email address (e.g., example@domain.com).", "error")
        elif not house_number.isdigit():
            show_notification("House Number must contain digits only.", "error")
        elif not is_valid_zip(zip_code):
            show_notification("ZIP Code must be exactly 4 digits.", "error")
        else:
            try:
                email_check = supabase.table("USER_Table").select("USER_EMAIL").eq("USER_EMAIL", email).execute()
                if email_check.data:
                    show_notification("The entered email is already registered. Please use a different email.", "error")
                else:
                    add_receptionist_db(user_data)
            except Exception as e:
                show_notification(f"Failed to add receptionist: {e}", "error")

    # Function to validate Step 2 inputs
    def validate_step2_inputs():
        dob = st.session_state.get("dob_input")
        phone = st.session_state.get("phone", "").strip()
        email = st.session_state.get("email", "").strip()
        city = st.session_state.get("city", "")
        barangay = st.session_state.get("barangay", "")
        street = st.session_state.get("street", "").strip()
        house_number = st.session_state.get("house_number", "").strip()
        zip_code = zip_codes_per_city.get(city, "")

        # Required fields check
        missing_fields = []
        for field_name, val in [
            ("Phone Number", phone),
            ("Email Address", email),
            ("City", city),
            ("Barangay", barangay),
            ("Street", street),
            ("House Number", house_number),
            ("ZIP Code", zip_code),
        ]:
            if not val:
                missing_fields.append(field_name)

        if missing_fields:
            show_notification(f"Please fill all required fields: {', '.join(missing_fields)}", "error")
            return False

        if not is_valid_phone(phone):
            show_notification("Phone number must start with '09' and be exactly 11 digits (e.g., 09XXXXXXXXX).", "error")
            return False

        if not is_valid_email(email):
            show_notification("Please enter a valid email address (e.g., example@domain.com).", "error")
            return False

        if not house_number.isdigit():
            show_notification("House Number must contain digits only.", "error")
            return False

        if not is_valid_zip(zip_code):
            show_notification("ZIP Code must be exactly 4 digits.", "error")
            return False

        # Check for duplicate email & phone number
        try:
            email_check = supabase.table("USER_Table").select("USER_EMAIL").eq("USER_EMAIL", email).execute()
            phonenum_check = supabase.table("USER_Table").select("USER_PHONE").eq("USER_PHONE", phone).execute()
            if email_check.data:
                show_notification("The entered email is already registered. Please use a different email.", "error")
                return False
            elif phonenum_check.data:
                show_notification("The entered phone number is already registered. Please use a different phone number.", "error")
                return False
        except Exception as e:
            show_notification(f"Error checking email/phone number: {e}", "error")
            return False

        return True
    
    # Function to handle pagination controls
    def pagination_controls(position):
                col1, col2, col3 = st.columns([1, 5, 1])
                with col1:
                    if st.session_state.page_num > 1:
                        if st.button("Previous", key=f"prev_{position}"):
                            st.session_state.page_num -= 1
                with col2:
                    st.markdown(f"<div style='text-align: center; font-weight: bold;'>Page {st.session_state.page_num} of {total_pages}</div>", unsafe_allow_html=True)
                with col3:
                    if st.session_state.page_num < total_pages:
                        if st.button("Next", key=f"next_{position}"):
                            st.session_state.page_num += 1

    # DOB and Age restrictions
    def calculate_age(born):
        today = date.today()
        return today.year - born.year - (
            (today.month, today.day) < (born.month, born.day)
        )

    # Function to validate names and ensure they're in the right format
    def validate_name(name):
        return bool(re.match(r"^[A-Za-z\s\-']+$", name.strip()))

    # Function to validate password to ensure it follows the requirements
    def validate_password(pw):
        return len(pw) >= 8
    
    # Function to validate phone
    def is_valid_phone(p):
        return re.match(r"^09\d{9}$", p.strip()) is not None

    # Function to validate email
    def is_valid_email(e):
        return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", e.strip()) is not None

    # Function to validate ZIP code
    def is_valid_zip(z):
        return re.match(r"^\d{4}$", z.strip()) is not None

    
    # --- Header Section ---
    col1, col2 = st.columns([6, 1])
    with col1:
        if not st.session_state.show_form:
            if st.button("Add New Receptionist"):
                st.session_state.show_form = True
                st.session_state.form_step = 1
                st.rerun()
        else:
            if st.button("Cancel", key="cancel_step1"):
                st.session_state.confirm_cancel_step1 = True

    if st.session_state.get("confirm_cancel_step1"):
        cancel_confirmation("confirm_cancel_step1", lambda: cancel_form())
    with col2:
        new_toggle = st.toggle("", value=is_light, key="theme_toggle")
        if new_toggle != is_light:
            st.session_state["search_bar"] = st.session_state.get("search_bar", "")
            st.session_state["light_mode"] = new_toggle
            st.rerun()


    # --- RECEPTIONIST DISPLAY ---

    # --- Main table ---
    if not st.session_state.show_form:
        st.markdown("## Current Receptionists")

        # --- Search ---
        search_col = st.columns([1])[0]
        search_input = search_col.text_input(
            "Search", 
            placeholder="Enter a name or an email to search",
            label_visibility="visible",
            key="search_bar"
        )

        # Reset page number on new search/if search changes
        if search_input != st.session_state.prev_search:
            st.session_state.page_num = 1

            # If previously there was input, and now it's cleared, this refreshes to show full list
            if st.session_state.prev_search.strip() and not search_input.strip():
                st.session_state.prev_search = ""
                st.rerun()
            else:
                st.session_state.prev_search = search_input

        all_receptionists = get_receptionist_db()

        if search_input:
            search_lower = re.sub(r"\s+", "", search_input.lower())
            filtered_receptionists = [
                r for r in all_receptionists
                if search_lower in re.sub(r"\s+", "", r["USER_FNAME"].lower())
                or search_lower in re.sub(r"\s+", "", (r["USER_MNAME"] or "").lower())
                or search_lower in re.sub(r"\s+", "", r["USER_LNAME"].lower())
                or search_lower in re.sub(r"\s+", "", r["USER_EMAIL"].lower())
                or search_lower in re.sub(r"\s+", "", r["USER_PHONE"].lower())
                or search_lower in re.sub(r"\s+", "", r["USER_USERNAME"].lower())
            ]
        else:
            filtered_receptionists = all_receptionists

        # Sort before paginating
        filtered_receptionists = sorted(
            filtered_receptionists,
            key=lambda x: x.get("USER_UPDATED_AT") or x.get("USER_CREATED_AT"),
            reverse=True
        )

        @st.dialog("Confirm Deletion")
        def confirm_delete_dialog(user_id):
            st.write("Are you sure you want to delete this user? This action cannot be undone.")
            confirm_col, spacer, cancel_col = st.columns([1, 3.5, 1])                    
                
            if confirm_col.button("Yes", key=f"confirm_{user_id}"):
                delete_receptionist_db(user_id)
                st.session_state["confirm_delete_id"] = None
                st.rerun()
            if cancel_col.button("No", key=f"cancel_{user_id}"):
                st.session_state["confirm_delete_id"] = None
                st.rerun()

        if not filtered_receptionists:
            show_notification("No receptionist/s found matching your search.", "warning")

        else:
            receptionists_per_page = 10
            total_receptionists = len(filtered_receptionists)
            total_pages = (total_receptionists - 1) // receptionists_per_page + 1

            current_page = st.session_state.page_num
            start_idx = (current_page - 1) * receptionists_per_page
            end_idx = start_idx + receptionists_per_page
            paged_receptionists = filtered_receptionists[start_idx:end_idx]

            header = st.columns([3, 3.5, 2, 1.5])
            for col, txt in zip(header, ["**Name**", "**Email**", "**Last Active**", "**Action**"]):
                col.markdown(txt)

            for r in paged_receptionists:
                full_name = " ".join([r["USER_FNAME"], r["USER_MNAME"] or "", r["USER_LNAME"]]).strip()
                email = r["USER_EMAIL"]
                dt = r.get("USER_LAST_ACTIVE") or r.get("USER_CREATED_AT")
                last_active = datetime.fromisoformat(dt).strftime("%B %d, %Y at %I:%M %p") if dt else "—"

                row = st.columns([3, 3.5, 2, 1.5])
                row[0].write(full_name)
                row[1].write(email)
                row[2].write(last_active)

                user_id = r["USER_ID"]

                if row[3].button("Delete", key=f"del_{user_id}"):
                    st.session_state["confirm_delete_id"] = user_id
                    confirm_delete_dialog(user_id)

            pagination_controls("receptionists")


    # --- ADD RECEPTIONIST FORM ---

    # --- Step 1 ---
    elif st.session_state.form_step == 1:
        st.markdown("""
            <style>
                div[data-baseweb="select"], 
                .stSelectbox {
                    max-width: 400px !important;
                }
            </style>
        """, unsafe_allow_html=True)

        st.markdown("### Add New Receptionist")

        saved_step1 = st.session_state.get("step1_data", {})

        # --- Name Fields ---
        col1, col2, col3 = st.columns(3)
        fname = col1.text_input("First Name", placeholder="First Name", key="fname", value=saved_step1.get("fname", ""))
        mname = col2.text_input("Middle Name", placeholder="Middle Name", key="mname", value=saved_step1.get("mname", ""))
        lname = col3.text_input("Last Name", placeholder="Last Name", key="lname", value=saved_step1.get("lname", ""))

        # --- Sex and Role (fixed role) ---
        sex = col1.selectbox("Sex", ["Male", "Female"], index=["Male", "Female"].index(saved_step1.get("sex", "Male")), key="sex")
        role = "Receptionist"
        col2.text_input("Role", value=role, disabled=True, key="role")

        # --- Username and Password ---
        username = st.text_input("Username", placeholder="Choose a username", key="username", value=saved_step1.get("username", ""))
        password = st.text_input("Temporary Password", placeholder="Enter at least 8 characters", type="password", key="password", value=saved_step1.get("password", ""))

        # --- Next Button ---
        _, next_col = st.columns([10, 1])
        if next_col.button("Next", key="step1_next"):

            # --- General Empty Field Check ---
            missing_fields = []
            for label, value in [
                ("First Name", fname),
                ("Last Name", lname),
                ("Username", username),
                ("Password", password)
            ]:
                if not value.strip():
                    missing_fields.append(label)

            # --- Handle Missing Fields First ---
            if missing_fields:
                show_notification(f"Please fill all required fields: {', '.join(missing_fields)}", "error")

            # --- Field-Specific Validation ---
            elif not validate_name(fname):
                show_notification("First name must only contain letters, spaces, hyphens, or apostrophes.", "error")
            elif mname and not validate_name(mname):
                show_notification("Middle name must only contain letters, spaces, hyphens, or apostrophes.", "error")
            elif not validate_name(lname):
                show_notification("Last name must only contain letters, spaces, hyphens, or apostrophes.", "error")
            elif not validate_password(password):
                show_notification("Password must be at least 8 characters long.", "error")
            else:
                # --- Check Username Uniqueness ---
                try:
                    username_check = supabase.table("USER_Table").select("USER_USERNAME").eq("USER_USERNAME", username.strip()).execute()
                    if username_check.data:
                        show_notification("This username is already taken. Please choose another.", "error")
                    else:
                        st.session_state.step1_data = {
                            "fname": fname.strip().title(),
                            "mname": mname.strip().title() if mname else "",
                            "lname": lname.strip().title(),
                            "sex": sex,
                            "role": role,
                            "username": username.strip(),
                            "password": password
                        }
                        st.session_state.form_step = 2
                        st.rerun()
                except Exception as e:
                    show_notification(f"Error checking username: {e}", "error")

    # --- Step 2 ---
    elif st.session_state.form_step == 2:
        st.markdown("### Add New Receptionist")
        today = date.today()
        min_birthdate = date(today.year - 100, today.month, today.day)
        max_birthdate = date(today.year - 18, today.month, today.day)

        saved_data = st.session_state.get("step2_data", {})

        # --- Date of birth ---
        col1, col2 = st.columns(2)
        dob_default = saved_data.get("dob_input", max_birthdate)
        dob = col1.date_input("Date of Birth", min_value=min_birthdate, max_value=max_birthdate, value=dob_default, key="dob_input")

        # --- Age ---
        age = calculate_age(dob)
        col2.text_input("Age", value=str(age), disabled=True)

        # --- Contact details ---
        col1, col2 = st.columns(2)
        phone = col1.text_input("Phone Number", placeholder="09XXXXXXXXX", max_chars=11, value=saved_data.get("phone", ""), key="phone")
        email = col2.text_input("Email Address", placeholder="Email Address", value=saved_data.get("email", ""), key="email")

        # --- Address Part 1  (Country, Province, and City) ---
        c1, c2, c3 = st.columns(3)
        country = c1.text_input("Country", value="Philippines", disabled=True, key="country")
        province = c2.text_input("Province", value="Cebu", disabled=True, key="province")
        city = c3.selectbox("City", ["Mandaue City", "Lapu-Lapu City", "Cebu City"], index=["Mandaue City", "Lapu-Lapu City", "Cebu City"].index(saved_data.get("city", "Mandaue City")), key="city")

        # --- Address Part 2 (Barangay, Street, House Number, and ZIP Code) ---
        c1, c2, c3, c4 = st.columns(4)
        if city in barangays_per_city:
            barangay_options = barangays_per_city[city]
            default_barangay = saved_data.get("barangay")
            if default_barangay in barangay_options:
                default_index = barangay_options.index(default_barangay)
            else:
                default_index = 0  # fallback to the first barangay

            barangay = c1.selectbox("Barangay", barangay_options, index=default_index, key="barangay")
        else:
            barangay = c1.selectbox("Barangay", ["Choose a city first"], index=0, disabled=True, key="barangay")

        street = c2.text_input("Street", placeholder="Street", value=saved_data.get("street", ""), key="street")
        house_number = c3.text_input("House Number", placeholder="House Number", value=saved_data.get("house_number", ""), key="house_number")
        zip_code_value = zip_codes_per_city.get(city, "")
        zip_code = c4.text_input("ZIP Code", value=zip_code_value, disabled=True, key="zip_code")

        back_col, create_col = st.columns([11, 2])
        with back_col:
            if st.button("Back", key="step2_back"):
                st.session_state.step2_data = {
                    "dob_input": dob,
                    "phone": phone,
                    "email": email,
                    "city": city,
                    "barangay": barangay,
                    "street": street,
                    "house_number": house_number,
                }
                st.session_state.form_step = 1
                st.rerun()

        with create_col:
            if st.button("Create User", key="create_user"):
                if validate_step2_inputs():
                    st.session_state.confirm_save_user = True  # show confirmation
                else:
                    st.session_state.confirm_save_user = False  # skip confirmation

        if st.session_state.get("confirm_save_user"):
            save_confirmation("confirm_save_user", lambda: process_user_creation())