# Dashboard.py for Manager

import streamlit as st
import time
from datetime import datetime, timedelta
from Supabase import supabase  # Your Supabase client


def Dashboard(is_light=True):
    # --- Session State Initialization ---
    if "light_mode" not in st.session_state:
        st.session_state["light_mode"] = True

    if is_light is None:
        is_light = st.session_state["light_mode"]

    is_light = st.session_state["light_mode"]

    # --- Page Routing ---
    if st.session_state.get("active_page") == "Privacy":
        from Manager import Privacy
        Privacy.Privacy(is_light=is_light)
        return  # Stop dashboard rendering when in Privacy page

    # --- Privacy Check ---
    user_id = st.session_state.get("USER_ID")
    show_dialog = False
    db_ack_until = None

    # Fetch DB value
    if user_id:
        try:
            resp = (
                supabase.table("USER_Table")
                .select("USER_PRIVACY_ACCEPTED_UNTIL")
                .eq("USER_ID", user_id)
                .maybe_single()
                .execute()
            )
            db_val = resp.data.get("USER_PRIVACY_ACCEPTED_UNTIL") if resp.data else None
            if db_val:
                try:
                    db_ack_until = datetime.fromisoformat(db_val)
                except Exception:
                    db_ack_until = datetime.fromisoformat(db_val.rstrip("Z"))

                # Clear expired DB value
                if datetime.now() > db_ack_until:
                    supabase.table("USER_Table").update({
                        "USER_PRIVACY_ACCEPTED_UNTIL": None
                    }).eq("USER_ID", user_id).execute()
                    db_ack_until = None

        except Exception:
            db_ack_until = None

    # Show only if it hasn't been shown this session AND DB value is missing or expired
    if not st.session_state.get("privacy_shown_once", False) and (db_ack_until is None):
        show_dialog = True
        st.session_state["privacy_shown_once"] = True

    # --- Privacy Dialog ---
    if show_dialog:
        @st.dialog("Privacy Notice")
        def privacy_dialog():

            st.markdown("""
                <style>
                    .st-key-accept_privacy button {
                        background-color: #d32f2f !important;
                        color: white !important;
                        border: none !important;
                        border-radius: 25px !important;
                        font-weight: bold !important;
                        height: 2.5rem !important;
                        width: 150% !important;
                        margin: 0.5rem 0 0.5rem 50% !important; 
                        display: block !important;
                        transition: background-color 0.3s ease !important;
                    }
                    .st-key-accept_privacy button:hover {
                        background-color: #f3a5a5 !important;
                        color: white !important;
                    }
                    .st-key-see_more button {
                        background-color: #f3a5a5 !important;
                        color: #282626 !important;
                        border: none !important;
                        border-radius: 25px !important;
                        font-weight: bold !important;
                        height: 2.5rem !important;
                        width: 150% !important;
                        margin: 0.5rem auto 0 auto !important;
                        display: block !important;
                        transition: background-color 0.3s ease !important;
                    }
                    .st-key-see_more button:hover {
                        background-color: #d32f2f !important;
                        color: white !important;
                    }
                </style>
            """, unsafe_allow_html=True)

            st.markdown("""
            <strong>Welcome to DeteXTB!</strong><br><br>

            This system may process sensitive and confidential information. Please ensure to: 
            <ul>
            <li>use responsibly and only for its intended purpose;</li>
            <li>protect patient and case information from unauthorized disclosure;</li>
            <li>comply with privacy and data protection regulations.</li>
            </ul>

            For full details, view the complete Privacy Policy via ‘See More’.
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("See More", key="see_more"):
                    st.session_state["active_page"] = "Privacy"
                    st.rerun()

            with col2:
                if st.button("I Understand", key="accept_privacy"):
                    # Update DB with expiry
                    if user_id:
                        new_expiry = (datetime.now() + timedelta(hours=2)).isoformat()
                        supabase.table("USER_Table").update({
                            "USER_PRIVACY_ACCEPTED_UNTIL": new_expiry
                        }).eq("USER_ID", user_id).execute()
                    st.rerun()

        privacy_dialog()


    # --- Theme Variables ---
    text_color = "black" if is_light else "white"
    dashboard_card_bg = "rgba(158,158,158,0.24)"
    tooltip_text_bg = "#333" if is_light else "#6D6C6C"
    tooltip_pointer = "#333" if is_light else "#6D6C6C"

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

    # --- Helper Functions ---

    # Function to fetch the username
    def get_current_username():
        # Get username from session state saved on login
        username = st.session_state.get("user_data", {}).get("username")
        if username:
            return username
        else:
            # fallback
            return "Manager"

    # Function to normalize DX_STATUS values
    def normalize_dx_status(dx_status):
        if not dx_status:
            return None
        dx_status = str(dx_status).strip().lower()
        if "confirmed positive" in dx_status:
            return "positive"
        elif "confirmed negative" in dx_status:
            return "negative"
        elif dx_status == "pending":
            return "pending"
        return None

    # Function to fetch Dashboard Data
    def fetch_dashboard_data():
        try:
            # 1. Total Confirmed TB Cases
            confirmed_res = supabase.table("DIAGNOSIS_Table") \
                .select("count", count="exact") \
                .eq("DX_STATUS", "Confirmed Positive") \
                .execute()
            total_confirmed = confirmed_res.count or 0

            # 2. Total Pending Results
            pending_res = supabase.table("RESULT_Table") \
                .select("count", count="exact") \
                .eq("RES_STATUS", "Pending") \
                .execute()
            total_pending = pending_res.count or 0

            # 3. Recently Updated Diagnoses (latest 5)
            diagnoses = supabase.table("DIAGNOSIS_Table") \
                .select("DX_STATUS, DX_UPDATED_AT, CXR_ID") \
                .order("DX_UPDATED_AT", desc=True) \
                .limit(5) \
                .execute()

            recent_cases = []
            for diag in diagnoses.data or []:
                cxr_id = diag["CXR_ID"]

                # Get result data using CXR_ID
                result_resp = supabase.table("RESULT_Table") \
                    .select("RES_PRESUMPTIVE, RES_CONF_SCORE, RES_DATE") \
                    .eq("CXR_ID", cxr_id) \
                    .maybe_single() \
                    .execute()
                result = result_resp.data

                # Get patient data from x-ray table
                chest_resp = supabase.table("CHEST_XRAY_Table") \
                    .select("PT_ID, PATIENT_Table(PT_FNAME, PT_MNAME, PT_LNAME)") \
                    .eq("CXR_ID", cxr_id) \
                    .maybe_single() \
                    .execute()
                chest = chest_resp.data

                if chest and chest.get("PATIENT_Table") and result:
                    patient = chest["PATIENT_Table"]
                    full_name = f"{patient['PT_FNAME']} {patient['PT_MNAME']} {patient['PT_LNAME']}".strip()
                    confidence = int(float(result.get("RES_CONF_SCORE", 0)) * 100)
                    ai_result = f"{result['RES_PRESUMPTIVE']} ({confidence}%)"

                    recent_cases.append({
                        "pt_id": chest["PT_ID"],
                        "name": full_name,
                        "ai_result": ai_result,
                        "status": diag["DX_STATUS"],
                        "updated": diag["DX_UPDATED_AT"][:10]  # date only
                    })

            return total_confirmed, total_pending, recent_cases

        except Exception as e:
            show_notification(" Failed to fetch dashboard data.", "error")
            st.exception(e)
            return 0, 0, []

    # Function to fetch the AI Accuracy Rate
    def fetch_ai_accuracy_rate():
        try:
            # Get all AI prediction results
            ai_results_resp = supabase.table("RESULT_Table").select("CXR_ID", "RES_PRESUMPTIVE").execute()
            ai_results = ai_results_resp.data or []

            if not ai_results:
                return "No Data"

            # Extract all CXR_IDs from AI results
            cxr_ids = [item["CXR_ID"] for item in ai_results]

            # Fetch diagnosis for these CXR_IDs
            dx_resp = supabase.table("DIAGNOSIS_Table") \
                .select("CXR_ID", "DX_STATUS") \
                .in_("CXR_ID", cxr_ids) \
                .execute()
            diagnosis_list = dx_resp.data or []

            # Create lookup dict: CXR_ID -> normalized DX_STATUS
            diagnosis_dict = {item["CXR_ID"]: normalize_dx_status(item["DX_STATUS"]) for item in diagnosis_list}

            correct = 0
            evaluated = 0

            for ai_item in ai_results:
                cxr_id = ai_item["CXR_ID"]
                ai_pred = str(ai_item.get("RES_PRESUMPTIVE", "")).strip().lower()
                dx_status = diagnosis_dict.get(cxr_id)

                # Skip if diagnosis is pending or missing
                if dx_status and dx_status != "pending":
                    evaluated += 1
                    if ai_pred == dx_status:
                        correct += 1

            if evaluated == 0:
                return "No Confirmed Cases"
            else:
                accuracy_percent = (correct / evaluated) * 100
                return f"{int(round(accuracy_percent))}%"
        except Exception as e:
            show_notification("Failed to fetch AI accuracy rate.", "error")
            st.exception(e)
            return "Error"

    # --- Fetch all data ---
    total_confirmed, total_pending, recent_cases = fetch_dashboard_data()
    ai_accuracy = fetch_ai_accuracy_rate()
    username = get_current_username()

    # --- Custom CSS ---
    st.markdown(f"""
    <style>
        #MainMenu, header, footer {{visibility: hidden;}}
        html, body, .stApp {{
            background-color: {'white' if is_light else '#0e0e0e'} !important;
            padding-top: 0rem !important;
            color: {'white' if is_light else 'black'} !important;
            font-family: 'Arial', sans-serif;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: {'black' if is_light else 'white'} !important;
        }}
        .block-container {{
            padding-top: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
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
        /* Custom Tooltip Styles */
        .tooltip-wrapper {{
            position: relative;
            display: inline-block;
            cursor: help;
        }}

        .tooltip-wrapper .tooltip-text {{
            visibility: hidden;
            width: 250px;
            background-color: {tooltip_text_bg};
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 10px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -125px;
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
            border-color: {tooltip_pointer} transparent transparent transparent;
        }}

        .tooltip-wrapper:hover .tooltip-text {{
            visibility: visible;
            opacity: 1;
        }}

        /* Add a question mark icon to indicate tooltip availability */
        .tooltip-icon {{
            display: inline-block;
            margin-left: 5px;
            margin-top: 2px; 
            width: 15px;
            height: 15px;
            background-color: #E53935;
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 15px;
            font-size: 12px;
            font-weight: bold;
            cursor: help;
        }}
    </style>
    """, unsafe_allow_html=True)

    # --- Page Header + Theme Toggle ---
    col_title, col_toggle = st.columns([6, 1])
    with col_title:
        st.markdown(f"<h4>Welcome, Manager {username}!</h4>", unsafe_allow_html=True)
    with col_toggle:
        new_toggle = st.toggle("🌙", value=is_light, key="theme_toggle", label_visibility="collapsed")
        if new_toggle != is_light:
            st.session_state["light_mode"] = new_toggle
            st.rerun()

    # --- Top Dashboard Cards ---
    st.markdown(f"""
    <div style="display:flex;gap:2rem; margin-bottom:1rem;">
        <div style="flex:1;background-color:{dashboard_card_bg};border-radius:12px;padding:1.5rem;text-align:center;">
            <div style="font-size:2.5rem;font-weight:bold;color:#E53935;">{total_confirmed}</div>
            <div style="color:{text_color};margin-top:0.5rem;">
                <span class="tooltip-wrapper">
                    <b>Confirmed TB Cases</b>
                    <span class="tooltip-icon">?</span>
                    <span class="tooltip-text">
                        Number of patients confirmed by the doctor to have active tuberculosis (TB+).
                    </span>
                </span>
            </div>
        </div>
        <div style="flex:1;background-color:{dashboard_card_bg};border-radius:12px;padding:1.5rem;text-align:center;">
            <div style="font-size:2.5rem;font-weight:bold;color:#E53935;">{total_pending}</div>
            <div style="color:{text_color};margin-top:0.5rem;">
                <span class="tooltip-wrapper">
                    <b>Pending Confirmations</b>
                    <span class="tooltip-icon">?</span>
                    <span class="tooltip-text">
                        Number of patients whose X-ray has been analyzed by AI but is still waiting for the doctor’s final decision.
                    </span>
                </span>
            </div>
        </div>
        <div style="flex:1;background-color:{dashboard_card_bg};border-radius:12px;padding:1.5rem;text-align:center;">
            <div style="font-size:2.5rem;font-weight:bold;color:#E53935;">{ai_accuracy}</div>
            <div style="color:{text_color};margin-top:0.5rem;">
                <span class="tooltip-wrapper">
                    <b>AI–Doctor Agreement Rate</b>
                    <span class="tooltip-icon">?</span>
                    <span class="tooltip-text">
                        Percentage of cases where the AI's prediction matches the doctor's final diagnosis across all evaluated cases.
                    </span>
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- AI Model Performance Metrics ---
    st.markdown(f"""
    <div style="display:flex;gap:2rem;">
        <div style="flex:1;background-color:{dashboard_card_bg};border-radius:12px;padding:1.5rem;text-align:center;">
            <div style="font-size:2rem;font-weight:bold;color:#E53935;">93%</div>
            <div style="color:{text_color};margin-top:0.5rem;">
                <span class="tooltip-wrapper">
                    <b>AI Model Accuracy</b>
                    <span class="tooltip-icon">?</span>
                    <span class="tooltip-text">
                        Percentage of all X-ray predictions made by the AI that were correct during model evaluation and testing.<br><br>
                        <em>Example:</em> If the AI correctly classifies 93 out of 100 X-rays, the accuracy is 93%.
                    </span>
                </span>
            </div>
        </div>
        <div style="flex:1;background-color:{dashboard_card_bg};border-radius:12px;padding:1.5rem;text-align:center;">
            <div style="font-size:2rem;font-weight:bold;color:#E53935;">91%</div>
            <div style="color:{text_color};margin-top:0.5rem;">
                <span class="tooltip-wrapper">
                    <b>Precision</b>
                    <span class="tooltip-icon">?</span>
                    <span class="tooltip-text">
                        When the AI predicts TB, this shows how often the prediction is actually correct.<br><br>
                        <em>Example:</em> If the AI predicts TB in 100 X-rays and 91 of those patients truly have TB, precision is 91%.
                    </span>
                </span>
            </div>
        </div>
        <div style="flex:1;background-color:{dashboard_card_bg};border-radius:12px;padding:1.5rem;text-align:center;">
            <div style="font-size:2rem;font-weight:bold;color:#E53935;">95%</div>
            <div style="color:{text_color};margin-top:0.5rem;">
                <span class="tooltip-wrapper">
                    <b>Recall</b>
                    <span class="tooltip-icon">?</span>
                    <span class="tooltip-text">
                        Out of all patients who actually have TB, this shows how many the AI correctly identifies.<br><br>
                        <em>Example:</em> If 100 patients truly have TB and the AI correctly identifies 95 of them, recall is 95%.
                    </span>
                </span>
            </div>
        </div>
        <div style="flex:1;background-color:{dashboard_card_bg};border-radius:12px;padding:1.5rem;text-align:center;">
            <div style="font-size:2rem;font-weight:bold;color:#E53935;">93%</div>
            <div style="color:{text_color};margin-top:0.5rem;">
                <span class="tooltip-wrapper">
                    <b>F1 Score</b>
                    <span class="tooltip-icon">?</span>
                    <span class="tooltip-text">
                        A single score that balances Precision and Recall, showing how well the AI detects TB while avoiding false alarms.<br><br>
                        <em>Example:</em> A high F1 score means the AI both finds most TB cases and is usually correct when it predicts TB.
                    </span>
                </span>
            </div>
        </div>
        <div style="flex:1;background-color:{dashboard_card_bg};border-radius:12px;padding:1.5rem;text-align:center;">
            <div style="font-size:2rem;font-weight:bold;color:#E53935;">97%</div>
            <div style="color:{text_color};margin-top:0.5rem;">
                <span class="tooltip-wrapper">
                    <b>AUC</b>
                    <span class="tooltip-icon">?</span>
                    <span class="tooltip-text">
                        Area Under the Curve; measures how well the AI can distinguish between TB and non-TB X-rays during training.<br><br>
                        <em>Example:</em> An AUC of 97% means there is a 97% chance the AI will rank a TB X-ray higher than a non-TB X-ray.
                    </span>
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


    # --- Recently Updated Diagnoses Table ---
    st.markdown(f"""
    <h4 style="color:{text_color};margin-top:2rem;margin-bottom:1rem;">Recent Patient Updates</h4>
    """, unsafe_allow_html=True)

    if not recent_cases:
        st.markdown(
            f"<div style='text-align: center; padding: 2rem; font-weight: bold; color: {text_color};'>No recent patient updates have been recorded.</div>",
            unsafe_allow_html=True
        )
    else:
        # Header Row - force color via inline style
        header_cols = st.columns([2, 2, 2, 2, 1.5])
        header_cols[0].markdown(f"<b style='color:{text_color};font-weight: bold'>Patient ID</b>", unsafe_allow_html=True)
        header_cols[1].markdown(f"<b style='color:{text_color};font-weight: bold'>Name</b>", unsafe_allow_html=True)
        header_cols[2].markdown(f"<b style='color:{text_color};font-weight: bold'>Date Updated</b>", unsafe_allow_html=True)
        header_cols[3].markdown(f"<b style='color:{text_color};font-weight: bold'>AI Result</b>", unsafe_allow_html=True)
        header_cols[4].markdown(f"<b style='color:{text_color};font-weight: bold'>Final Diagnosis</b>", unsafe_allow_html=True)

        # Data Rows
        for r in recent_cases:
            color = "#e6af0a"  # Pending
            if r["status"] == "Confirmed Positive":
                color = "#f44336"
            elif r["status"] == "Confirmed Negative":
                color = "#4caf50"

            row_cols = st.columns([2, 2, 2, 2, 1.5])
            row_cols[0].markdown(f"<span style='color:{text_color};'>{r['pt_id']}</span>", unsafe_allow_html=True)
            row_cols[1].markdown(f"<span style='color:{text_color};'>{r['name']}</span>", unsafe_allow_html=True)
            row_cols[2].markdown(f"<span style='color:{text_color};'>{r['updated']}</span>", unsafe_allow_html=True)
            row_cols[3].markdown(f"<span style='color:{text_color};'>{r['ai_result']}</span>", unsafe_allow_html=True)
            row_cols[4].markdown(f"<span style='color:{color};font-weight:bold'>{r['status']}</span>", unsafe_allow_html=True)
