# Account.py for the manager

import streamlit as st
import base64
import os
import re
import time
from datetime import date
from Supabase import supabase


def Account(is_light=True):
    # --- Session State + Form Initialization ---
    if "light_mode" not in st.session_state:
        st.session_state["light_mode"] = True

    if is_light is None:
        is_light = st.session_state["light_mode"]

    if "show_form" not in st.session_state:
        st.session_state["show_form"] = False

    # --- Dynamic Theme Variables ---
    is_light = st.session_state["light_mode"]
    bg_color = "white" if is_light else "#0e0e0e"
    text_color = "black" if is_light else "white"
    input_bg = "white" if is_light else "#1a1a1a"
    border_color = "black" if is_light else "white"
    header_bg = "#f0f2f6" if is_light else "#222"
    card_bg = "#f0f2f6" if is_light else "#222"
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

    # --- CSS Styling ---
    st.markdown(f"""
        <style>
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
                background-color: {'white' if is_light else '#1a1a1a'} !important;
                border: none !important;
                border-radius: 0 !important;
                box-shadow: none !important;
                padding: 0 !important;
            }}
            div[data-baseweb="input"] button > svg {{
                background-color: {'white' if is_light else '#1a1a1a'} !important;
                fill: {'black' if is_light else 'white'} !important;
                width: 1.2rem !important;
                height: 1.2rem !important;
            }}
            input:disabled,
            .stTextInput input:disabled,
            div[data-testid="stTextInput"] input[disabled] {{
                background-color: {"white" if is_light else "#1a1a1a"} !important;
                color: {"black" if is_light else "white"} !important;
                opacity: 1 !important;
                -webkit-text-fill-color: {"black" if is_light else "white"} !important;
            }}
            .custom-button {{
                background-color: {button_color} !important;
                color: white !important;
                border: none !important;
                border-radius: 25px !important;
                padding: 0.5em 1.5em !important;
                font-weight: bold !important;
                transition: background-color 0.3s ease;
                cursor: pointer !important;
                font-size: 0.9rem !important;
                min-width: 100px !important;
                text-align: center !important;
                margin: 0.2rem 0 !important;
            }}
            .custom-button:hover {{
                background-color: {button_hover} !important;
            }}
            .cancel-button {{
                background-color: {bg_color} !important;
                color: {button_color} !important;
                border: 1px solid {button_color} !important;
            }}
            .cancel-button:hover {{
                background-color: {hover_bg} !important;
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
    

    # --- Helper Functions ---

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

    # Function to update username/password info
    def update_user_credential_info(user_id, record):
        try:
            supabase.table("USER_Table").update(record).eq("USER_ID", user_id).execute()
            if "user_data" in st.session_state:
                st.session_state["user_data"]["username"] = record.get("USER_USERNAME", st.session_state["user_data"].get("username"))
                st.session_state["user_data"]["USER_USERNAME"] = record.get("USER_USERNAME", st.session_state["user_data"].get("USER_USERNAME"))
                st.session_state["user_data"]["USER_PASSWORD"] = record.get("USER_PASSWORD", st.session_state["user_data"].get("USER_PASSWORD"))
            show_notification("Credential information updated successfully.", "success")
            st.session_state["show_form_credential"] = False
            st.rerun()
        except Exception as e:
            show_notification(f"Update failed: {e}", "error")

    # Function to update personal info
    def update_user_personal_info(user_id, record):
        try:
            supabase.table("USER_Table").update(record).eq("USER_ID", user_id).execute()
            
            # Update session state with new name data for real-time sidebar update
            if "user_data" in st.session_state:
                st.session_state["user_data"]["fname"] = record.get("USER_FNAME", st.session_state["user_data"].get("fname"))
                st.session_state["user_data"]["mname"] = record.get("USER_MNAME", st.session_state["user_data"].get("mname"))
                st.session_state["user_data"]["lname"] = record.get("USER_LNAME", st.session_state["user_data"].get("lname"))
                # Also update the combined "name" field if used elsewhere
                fname = record.get("USER_FNAME", "")
                lname = record.get("USER_LNAME", "")
                st.session_state["user_data"]["name"] = f"{fname} {lname}"
            
            show_notification("Personal information updated successfully.", "success")
            st.session_state["show_form_personal"] = False
            st.rerun()
        except Exception as e:
            show_notification(f"Update failed: {e}", "error")

    # Function to update address info
    def update_user_address_info(user_id, record):
        try:
            supabase.table("USER_Table").update(record).eq("USER_ID", user_id).execute()
            show_notification("Address information updated successfully.", "success")
            st.session_state["show_form_address"] = False
            st.rerun()
        except Exception as e:
            show_notification(f"Update failed: {e}", "error")

    # Function to confirm update cancellation
    def cancel_confirmation(flag_key: str, on_confirm_callback=None):
        @st.dialog("Discard Changes?")
        def _dialog():
            st.write("Are you sure you want to discard your changes? Your edits will be lost.")

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
        _dialog()

    # Function to confirm save action
    def save_confirmation(flag_key: str, on_confirm_callback=None):
        @st.dialog("Save Changes?")
        def _dialog():
            st.write("Are you sure you want to save your changes?")

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
        _dialog()

    # DOB and Age restrictions
    def calculate_age(born):
        today = date.today()
        return today.year - born.year - (
            (today.month, today.day) < (born.month, born.day)
        )

    # Function to validate names and ensure they're in the right format
    def validate_name(name):
        return bool(re.match(r"^[A-Za-z\s\-']+$", name.strip()))
    
    # Function to validate phone
    def is_valid_phone(p):
        return re.match(r"^09\d{9}$", p.strip()) is not None

    # Function to validate email
    def is_valid_email(e):
        return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", e.strip()) is not None

    # Function to check if credentials have changed
    def credentials_changed(current_username, current_password, new_username, new_password):
        if new_username != current_username:
            return True
        if new_password and new_password != current_password:
            return True
        return False

    # Function to check if personal info has changed
    def personal_info_changed(user_data, new_data):
        fields_to_check = [
            "USER_FNAME", "USER_MNAME", "USER_LNAME", 
            "USER_SEX", "USER_DOB", "USER_EMAIL", 
            "USER_PHONE"
        ]
        for field in fields_to_check:
            if field == "USER_DOB":
                if str(new_data[field]) != str(user_data.get(field, "")):
                    return True
            elif new_data.get(field, "") != user_data.get(field, ""):
                return True
        return False

    # Function to check if address info has changed
    def address_info_changed(user_data, new_data):
        fields_to_check = [
            "USER_CITY", "USER_BRGY", "USER_STREET", 
            "USER_HOUSENO"
        ]
        for field in fields_to_check:
            if new_data.get(field, "") != user_data.get(field, ""):
                return True
        return False


    # --- Theme Toggle ---
    col_title, col_toggle = st.columns([6, 1])
    with col_title:
        st.markdown("<h4>My Account</h4>", unsafe_allow_html=True)
    with col_toggle:
        def toggle_theme():
            st.session_state["light_mode"] = not st.session_state["light_mode"]

        st.toggle("🌙", value=st.session_state["light_mode"], key="theme_toggle", label_visibility="collapsed", on_change=toggle_theme)


    # --- Load Icon ---
    def load_icon(relative_path):
        base_dir = os.path.dirname(__file__)  # This gives: Receptionist/
        abs_path = os.path.join(base_dir, relative_path)
        with open(abs_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    account_icon = load_icon("../images/account.png")


    st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)


    # --- Account Info Header ---

    # Fetch fresh user info
    user_info = st.session_state.get("user_data", {})
    user_id = user_info.get("id") or user_info.get("USER_ID")

    if user_id:
        header_response = supabase.table("USER_Table").select("USER_FNAME, USER_MNAME, USER_LNAME, USER_ROLE, USER_USERNAME, USER_PASSWORD").eq("USER_ID", user_id).single().execute()
        if header_response.data:
            header_data = header_response.data
            # Construct full name
            fname = header_data.get("USER_FNAME", "")
            mname = header_data.get("USER_MNAME", "")
            lname = header_data.get("USER_LNAME", "")
            
            # Build full name
            full_name_parts = [fname]
            if mname:
                full_name_parts.append(mname)
            full_name_parts.append(lname)
            full_name = " ".join(full_name_parts) if full_name_parts else "Account Name"
            
            role = header_data.get("USER_ROLE", "Role").capitalize()
            username = header_data.get("USER_USERNAME", "Username")
            
            # Update user_info with fresh password if updated
            if not user_info.get("USER_PASSWORD"):
                user_info["USER_PASSWORD"] = header_data.get("USER_PASSWORD", "")
        else:
            full_name = "Account Name"
            role = "Role"
            username = "Username"
    else:
        full_name = "Account Name"
        role = "Role" 
        username = "Username"

    with st.container():
        col1, col2 = st.columns([1, 20])
        # Icon
        with col1:
            st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; width: 150%;">
                <img src="data:image/png;base64,{account_icon}" style="width: 60px; height: 60px; margin-right: 1rem;" />
            </div>
            """, unsafe_allow_html=True)

        with col2:
            # Top row: Full name and username
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 1.2rem; font-weight: bold; color: {text_color};">{full_name}</div>
                <div style="font-size: 1.1rem; color: {text_color}; margin-bottom: 10px;">
                    Username: <strong>{username}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Bottom row: Role and edit credential button
            col_role, col_button = st.columns([5.6, 1])
            with col_role:
                st.markdown(f"""
                <div style="font-size: 1rem; color: {text_color}; margin-top: 10px;">{role}</div>
                """, unsafe_allow_html=True)

            with col_button:
                if not st.session_state.get("show_form_credential", False):
                    if st.button("Edit ✎", key="edit_credential_button"):
                        st.session_state["show_form_credential"] = True
                        st.rerun()

    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)

    # Edit credential form in edit mode
    if st.session_state.get("show_form_credential", False):
        # Username input
        new_username = st.text_input(
            "Username",
            value=st.session_state.get("new_username", username),
            key="new_username"
        )

        # Password inputs
        col1, col2 = st.columns(2)
        with col1:
            new_password = st.text_input(
                "New Password",
                type="password",
                key="new_password"
            )
        with col2:
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="confirm_password"
            )

        # Check if credentials have changed
        credentials_have_changed = credentials_changed(
            username,
            user_info.get("USER_PASSWORD", ""),
            new_username.strip(),
            new_password
        )

        # Cancel and Save buttons in account credentials form
        col_cancel, col_spacer, col_save = st.columns([1, 6, 1])

        with col_cancel:
            if st.button("Cancel", key="cancel_credential_button"):
                st.session_state["confirm_cancel_credential"] = True

        with col_save:
            if credentials_have_changed:
                if st.button("Save", key="save_credential_button"):
                    errors = []
                    new_username_val = new_username.strip()
                    new_password_val = new_password
                    confirm_password_val = confirm_password

                    if not new_username_val:
                        errors.append("Username cannot be empty.")

                    if new_password_val or confirm_password_val:
                        if new_password_val != confirm_password_val:
                            errors.append("Passwords do not match.")
                        elif len(new_password_val) < 8:
                            errors.append("Password must be at least 8 characters.")
                        elif new_password_val == user_info.get("USER_PASSWORD", ""):
                            errors.append("New password must be different from the current password.")

                    existing = supabase.table("USER_Table").select("USER_ID").eq("USER_USERNAME", new_username_val).neq("USER_ID", user_id).execute()
                    if existing.data:
                        errors.append("The entered username is already in use. Please choose a different one.")

                    if errors:
                        for err in errors:
                            show_notification(err, "error")
                    else:
                        st.session_state["validated_credential_data"] = {
                            "USER_USERNAME": new_username_val,
                            "USER_PASSWORD": new_password_val if new_password_val else user_info.get("USER_PASSWORD", "")
                        }
                        st.session_state["confirm_save_credential"] = True
                        st.rerun()
                        

           
        if st.session_state.get("confirm_cancel_credential", False):
            cancel_confirmation(
                "confirm_cancel_credential",
                lambda: st.session_state.update({"show_form_credential": False})
            )
        
        if st.session_state.get("confirm_save_credential", False):
            save_confirmation(
                "confirm_save_credential",
                lambda: update_user_credential_info(user_id, st.session_state["validated_credential_data"])
            )


    # --- Fetch logged-in user data ---
    user_id = st.session_state.get("user_data", {}).get("id")
    user_data = None

    if user_id:
        response = supabase.table("USER_Table").select("*").eq("USER_ID", user_id).single().execute()
        user_data = response.data if response.data else None
    else:
        show_notification("You are not logged in.", "warning")


    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)


    if user_data:
        # --- PERSONAL INFO CARD ---
        with st.container():
            # Section Header: Personal Information title + Edit button
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"""
                    <div style="display: flex; align-items: center; height: 100%;">
                        <h3 style="color: {text_color}; margin: 0;">Personal Information</h3>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                # Edit button + edit form
                if not st.session_state.get("show_form_personal"):
                    st.markdown("<div style='margin-top: 0.2rem;'>", unsafe_allow_html=True)
                    if st.button("Edit ✎", key="edit_personal_button"):
                        st.session_state["show_form_personal"] = True
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.get("show_form_personal"):
                # Row 1: First Name, Middle Name, and Last Name
                col1, col2, col3 = st.columns(3)
                with col1:
                    fname = st.text_input(
                        "First Name",
                        value=st.session_state.get("fname", user_data["USER_FNAME"]),
                        key="fname",
                    )
                with col2:
                    mname = st.text_input(
                        "Middle Name",
                        value=st.session_state.get("mname", user_data.get("USER_MNAME", "")),
                        key="mname",
                    )
                with col3:
                    lname = st.text_input(
                        "Last Name",
                        value=st.session_state.get("lname", user_data["USER_LNAME"]),
                        key="lname",
                    )

                # Row 2: Sex, Date of Birth, and Age
                col4, col5, col6 = st.columns(3)
                with col4:
                    sex = st.selectbox(
                        "Sex",
                        options=["Male", "Female"],
                        index=["Male", "Female"].index(st.session_state.get("sex", user_data["USER_SEX"])),
                        key="sex",
                    )
                with col5:
                    max_valid_dob = date.today().replace(year=date.today().year - 18)
                    dob = st.date_input(
                        "Date of Birth",
                        value=st.session_state.get("dob", user_data["USER_DOB"]),
                        max_value=max_valid_dob,
                        key="dob",
                    )
                with col6:
                    age = calculate_age(st.session_state.get("dob", user_data["USER_DOB"]))
                    st.text_input("Age", value=str(age), disabled=True)

                # Row 3: Email Address, Phone Number, and Role (fixed)
                col7, col8, col9 = st.columns(3)
                with col7:
                    email = st.text_input(
                        "Email Address",
                        value=st.session_state.get("email", user_data["USER_EMAIL"]),
                        key="email",
                    )
                with col8:
                    phone = st.text_input(
                        "Phone Number", max_chars=11,
                        value=st.session_state.get("phone", user_data["USER_PHONE"]),
                        key="phone",
                    )
                with col9:
                    st.text_input(
                        "User Role",
                        value=user_data["USER_ROLE"],
                        key="role",
                        disabled=True,
                    )

                # Check if personal info has changed
                current_personal_data = {
                    "USER_FNAME": user_data["USER_FNAME"],
                    "USER_MNAME": user_data.get("USER_MNAME", ""),
                    "USER_LNAME": user_data["USER_LNAME"],
                    "USER_SEX": user_data["USER_SEX"],
                    "USER_DOB": str(user_data["USER_DOB"]),
                    "USER_EMAIL": user_data["USER_EMAIL"],
                    "USER_PHONE": user_data["USER_PHONE"],
                }

                new_personal_data = {
                    "USER_FNAME": fname.strip().title(),
                    "USER_MNAME": mname.strip().title(),
                    "USER_LNAME": lname.strip().title(),
                    "USER_SEX": sex,
                    "USER_DOB": str(dob),
                    "USER_EMAIL": email.strip(),
                    "USER_PHONE": phone.strip(),
                }

                personal_info_has_changed = personal_info_changed(current_personal_data, new_personal_data)

                # Cancel and buttons in personal info form
                col_cancel, col_spacer, col_save = st.columns([1, 6, 1])

                with col_cancel:
                    if st.button("Cancel", key="cancel_personal_button"):
                        st.session_state["confirm_cancel_personal"] = True

                with col_save:
                    if personal_info_has_changed:
                        if st.button("Save", key="save_personal_button"):
                            errors = []

                            fname = st.session_state.get("fname", "").strip().title()
                            mname = st.session_state.get("mname", "").strip().title()
                            lname = st.session_state.get("lname", "").strip().title()
                            dob = st.session_state.get("dob")
                            email = st.session_state.get("email", "").strip()
                            phone = st.session_state.get("phone", "").strip()
                            age = calculate_age(dob)

                            missing_fields = []
                            for field_name, val in [
                                ("First Name", fname),
                                ("Last Name", lname),
                                ("Date of Birth", dob),
                                ("Email Address", email),
                                ("Phone Number", phone),
                            ]:
                                if not val:
                                    missing_fields.append(field_name)

                            if missing_fields:
                                errors.append(f"Please fill all required fields: {', '.join(missing_fields)}")
                            elif not validate_name(fname):
                                errors.append("First name must only contain letters, spaces, hyphens, or apostrophes.")
                            elif mname and not validate_name(mname):
                                errors.append("Middle name must only contain letters, spaces, hyphens, or apostrophes.")
                            elif not validate_name(lname):
                                errors.append("Last name must only contain letters, spaces, hyphens, or apostrophes.")
                            elif not is_valid_email(email):
                                errors.append("Please enter a valid email address (e.g., example@domain.com).")
                            elif not is_valid_phone(phone):
                                errors.append("Phone number must start with '09' and be exactly 11 digits (e.g., 09XXXXXXXXX).")
                            else:
                                existing = supabase.table("USER_Table").select("USER_ID").eq("USER_EMAIL", email).neq("USER_ID", user_id).execute()
                                if existing.data:
                                    errors.append("The entered email is already registered. Please use a different email.")

                            if errors:
                                for err in errors:
                                    show_notification(err, "error")
                            else:
                                st.session_state["validated_personal_info"] = {
                                    "USER_FNAME": fname,
                                    "USER_MNAME": mname,
                                    "USER_LNAME": lname,
                                    "USER_SEX": st.session_state.get("sex"),
                                    "USER_DOB": str(dob),
                                    "USER_AGE": age,
                                    "USER_EMAIL": email,
                                    "USER_PHONE": phone,
                                }
                                st.session_state["confirm_save_personal"] = True
                                st.rerun()
                               

                if st.session_state.get("confirm_cancel_personal", False):
                    cancel_confirmation("confirm_cancel_personal",lambda: st.session_state.update({"show_form_personal": False}))

                if st.session_state.get("confirm_save_personal", False):
                    save_confirmation("confirm_save_personal",lambda: update_user_personal_info(user_id, st.session_state["validated_personal_info"]))
                

            else:
                # Display view-only personal details
                st.markdown(f"""
                    <div style="margin-top: -1rem; background-color: {card_bg}; border-radius: 12px; padding: 1.5rem;">
                        <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; font-size: 0.9rem; color: {text_color};">
                            <div><div>First Name</div><div style="font-weight: bold;">{user_data["USER_FNAME"]}</div></div>
                            <div><div>Middle Name</div><div style="font-weight: bold;">{user_data.get("USER_MNAME", "")}</div></div>
                            <div><div>Last Name</div><div style="font-weight: bold;">{user_data["USER_LNAME"]}</div></div>
                            <div><div>Sex</div><div style="font-weight: bold;">{user_data["USER_SEX"]}</div></div>
                            <div><div>Date of Birth</div><div style="font-weight: bold;">{user_data["USER_DOB"]}</div></div>
                            <div><div>Age</div><div style="font-weight: bold;">{user_data["USER_AGE"]}</div></div>
                            <div><div>Email Address</div><div style="font-weight: bold;">{user_data["USER_EMAIL"]}</div></div>
                            <div><div>Phone Number</div><div style="font-weight: bold;">(+63) {user_data["USER_PHONE"][1:]}</div></div>
                            <div><div>User Role</div><div style="font-weight: bold;">{user_data["USER_ROLE"]}</div></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)


        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)


        # --- ADDRESS INFO CARD ---
        with st.container():
            # Section Header: Address title + Edit button
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"""
                    <div style="display: flex; align-items: center; height: 100%;">
                        <h3 style="color: {text_color}; margin: 0;">Address</h3>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                # Edit button + edit form
                if not st.session_state.get("show_form_address"):
                    st.markdown("<div style='margin-top: 0.2rem;'>", unsafe_allow_html=True)
                    if st.button("Edit ✎", key="edit_address_button"):
                        st.session_state["show_form_address"] = True
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.get("show_form_address"):
                # Row 1: Country, Province, and City
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.text_input("Country", value=user_data["USER_COUNTRY"], key="country", disabled=True)
                with col2:
                    st.text_input("Province", value=user_data["USER_PROVINCE"], key="province", disabled=True)
                with col3:
                    city_options = ["Mandaue City", "Lapu-Lapu City", "Cebu City"]
                    city = st.selectbox("City", options=city_options, index=city_options.index(st.session_state.get("city", user_data["USER_CITY"])), key="city")

                # Update barangay options based on selected city
                filtered_barangays = barangays_per_city[city]

                # Row 2: Barangay and Street
                col4, col5 = st.columns(2)
                with col4:
                    brgy = st.selectbox(
                        "Barangay",
                        options=filtered_barangays,
                        index=filtered_barangays.index(
                            st.session_state.get("brgy", user_data["USER_BRGY"])
                        ) if st.session_state.get("brgy", user_data["USER_BRGY"]) in filtered_barangays else 0,
                        key="brgy"
                    )
                with col5:
                    street = st.text_input("Street", value=st.session_state.get("street", user_data["USER_STREET"]), key="street")

                # Row 3: House Number and Postal Code
                col6, col7 = st.columns(2)
                with col6:
                    house_no = st.text_input("House Number", value=st.session_state.get("house_no", user_data["USER_HOUSENO"]), key="house_no")
                with col7:
                    zip_code_value = zip_codes_per_city.get(city, "")
                    st.text_input("Postal Code", value=zip_code_value, key="zip", disabled=True)

                # Check if address info has changed
                current_address_data = {
                    "USER_CITY": user_data["USER_CITY"],
                    "USER_BRGY": user_data["USER_BRGY"],
                    "USER_STREET": user_data["USER_STREET"],
                    "USER_HOUSENO": user_data["USER_HOUSENO"],
                }

                new_address_data = {
                    "USER_CITY": city,
                    "USER_BRGY": brgy,
                    "USER_STREET": street.strip().title(),
                    "USER_HOUSENO": house_no.strip(),
                }

                address_info_has_changed = address_info_changed(current_address_data, new_address_data)

                # Cancel and Save buttons in address form
                col_cancel, col_spacer, col_save = st.columns([1, 6, 1])

                with col_cancel:
                    if st.button("Cancel", key="cancel_address_button"):
                        st.session_state["confirm_cancel_address"] = True
                        st.rerun()

                    

                with col_save:
                    if address_info_has_changed:
                        if st.button("Save", key="save_address_button"):
                            street = st.session_state["street"].strip().title()
                            house_no = st.session_state["house_no"].strip()
                            city = st.session_state["city"]
                            brgy = st.session_state["brgy"]

                            errors = []

                            missing_fields = []
                            for field_name, val in [
                                ("Street", street),
                                ("House Number", house_no),
                                ("City", city),
                                ("Barangay", brgy),
                            ]:
                                if not val:
                                    missing_fields.append(field_name)

                            if missing_fields:
                                errors.append(f"Please fill all required fields: {', '.join(missing_fields)}")
                            elif not house_no.isdigit():
                                errors.append("House Number must contain digits only.")

                            if errors:
                                for err in errors:
                                    show_notification(err, "error")
                            else:
                                st.session_state["validated_address_info"] = {
                                    "USER_CITY": city,
                                    "USER_BRGY": brgy,
                                    "USER_STREET": street,
                                    "USER_HOUSENO": house_no,
                                    "USER_ZIPCODE": zip_codes_per_city.get(city, ""),
                                }
                                st.session_state["confirm_save_address"] = True
                                st.rerun()

                if st.session_state.get("confirm_cancel_address", False):
                    cancel_confirmation("confirm_cancel_address", lambda: st.session_state.update({"show_form_address": False}))

                if st.session_state.get("confirm_save_address", False):
                    save_confirmation("confirm_save_address", lambda: update_user_address_info(user_id, st.session_state["validated_address_info"]))    

            else:
                # Display view-only address details
                st.markdown(f"""
                    <div style="margin-top: -1rem; background-color: {card_bg}; border-radius: 12px; padding: 1.5rem;">
                        <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; font-size: 0.9rem; color: {text_color};">
                            <div><div>Country</div><div style="font-weight: bold;">{user_data["USER_COUNTRY"]}</div></div>
                            <div><div>Province</div><div style="font-weight: bold;">{user_data["USER_PROVINCE"]}</div></div>
                            <div><div>City</div><div style="font-weight: bold;">{user_data["USER_CITY"]}</div></div>
                            <div><div>Barangay</div><div style="font-weight: bold;">{user_data["USER_BRGY"]}</div></div>
                            <div><div>Street</div><div style="font-weight: bold;">{user_data["USER_STREET"]}</div></div>
                            <div><div>House Number</div><div style="font-weight: bold;">{user_data["USER_HOUSENO"]}</div></div>
                            <div><div>Postal Code</div><div style="font-weight: bold;">{user_data["USER_ZIPCODE"]}</div></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)