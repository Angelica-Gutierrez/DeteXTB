# Results.py

import streamlit as st
from Supabase import supabase
from datetime import datetime
from datetime import date
import time

def Results(is_light=True):

    if "light_mode" not in st.session_state:
        st.session_state["light_mode"] = True

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
                            PT_LNAME
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
                    continue  # already added latest case for this patient

                seen_patients.add(pt_id)
                full_name = f"{patient_data['PT_FNAME']} {patient_data['PT_MNAME']} {patient_data['PT_LNAME']}".strip()
                confidence_percent = f"{int(float(entry['RES_CONF_SCORE']) * 100)}%"

                latest_cases.append({
                    "pt_id": pt_id,
                    "name": full_name,
                    "date": entry["RES_DATE"],
                    "result": entry["RES_PRESUMPTIVE"],
                    "confidence": confidence_percent,
                    "diagnosis": entry["RES_STATUS"]
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
        st.session_state["search_bar_results"] = ""
        st.session_state["results_status_filter"] = "All"
        st.session_state["results_presumptive_filter"] = "All"
        st.session_state["results_date_from"] = oldest_date
        st.session_state["results_date_to"] = date.today()
        st.session_state["results_page_num"] = 1
        st.session_state["reset_triggered"] = False  # Clear flag


    # Initialize all filter values before any UI access
    if "search_bar_results" not in st.session_state:
        st.session_state["search_bar_results"] = ""

    if "results_status_filter" not in st.session_state:
        st.session_state["results_status_filter"] = "All"

    if "results_presumptive_filter" not in st.session_state:
        st.session_state["results_presumptive_filter"] = "All"

    if "results_date_from" not in st.session_state:
        st.session_state["results_date_from"] = oldest_date
        
    if "results_date_to" not in st.session_state:
        st.session_state["results_date_to"] = date.today()

    if "diagnoses" not in st.session_state:
        st.session_state["diagnoses"] = {f"diagnosis_{i}": case["diagnosis"] for i, case in enumerate(cases)}

    if "results_page_num" not in st.session_state:
        st.session_state["results_page_num"] = 1

    cases_per_page = 10

    def apply_filters():
        filtered = cases
        query = st.session_state["search_bar_results"].strip().lower()
        if query:
            # Search in both patient name and patient ID
            filtered = [
                c for c in filtered 
                if (query in c["name"].lower() or 
                    query in c["pt_id"].lower() or  
                    query in str(c["pt_id"]).lower()) 
            ]

        if st.session_state["results_status_filter"] != "All":
            filtered = [c for c in filtered if c["diagnosis"] == st.session_state["results_status_filter"]]

        if st.session_state["results_presumptive_filter"] != "All":
            target = "Positive" if st.session_state["results_presumptive_filter"] == "Positive" else "Negative"
            filtered = [c for c in filtered if c["result"] == target]

        if st.session_state["results_date_from"]:
            filtered = [c for c in filtered if datetime.fromisoformat(c["date"]).date() >= st.session_state["results_date_from"]]

        if st.session_state["results_date_to"]:
            filtered = [c for c in filtered if datetime.fromisoformat(c["date"]).date() <= st.session_state["results_date_to"]]

        return filtered

    def pagination_controls(position, total_pages):
        col1, col2, col3 = st.columns([1, 7, 1])
        with col1:
            if st.session_state.results_page_num > 1:
                if st.button("Previous", key=f"prev_{position}"):
                    st.session_state.results_page_num -= 1
                    st.rerun()
        with col2:
            st.markdown(f"<div style='text-align: center; font-weight: bold;'>Page {st.session_state.results_page_num} of {total_pages}</div>", unsafe_allow_html=True)
        with col3:
            if st.session_state.results_page_num < total_pages:
                if st.button("Next", key=f"next_{position}"):
                    st.session_state.results_page_num += 1
                    st.rerun()
      

    # ------------------- Layout -------------------

    # --- Title and Theme Toggle ---

    # --- Theme Toggle UI ---
    col_title, col_toggle = st.columns([6, 1])
    with col_title:
        st.markdown("<h4>Patient Results</h4>", unsafe_allow_html=True)
    with col_toggle:
        new_toggle = st.toggle("🌙", value=is_light, key="theme_toggle", label_visibility="collapsed")

    if new_toggle != st.session_state["light_mode"]:
        st.session_state["light_mode"] = new_toggle
        st.rerun()

    is_light = st.session_state["light_mode"]


    # Theme-based color variables
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
    filtered_case_bg_color = "#ffe6e8" if is_light else "#6c0019"
    filtered_case_text = "#c4751a" if is_light else "#deb364"
    filtered_case_border = "#ebc68f" if is_light else "#7E6A23"
    total_cases_bg_color = "#ffe6e8" if is_light else "#6c0019"
    total_cases_text = "#ff1818" if is_light else "#fab4bc"
    total_cases_border = "#ff9191" if is_light else "#8f0700"

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
        }}

        div[data-testid="stDateInput"] svg {{
            color: {text_color} !important;
        }}
        
           div[data-testid="stDateInput"] > div:focus-within {{
        box-shadow: none !important;
        }}

        div[data-baseweb="popover"] {{
            background-color: {calendar_dropdown_bg} !important;
            border: 1px solid {calendar_border} !important;
            border-radius: 15px !important;
        }}

        .stSelectbox div[data-baseweb="select"] > div {{
            background-color: {select_bg} !important;
            color: {text_color} !important;
            border: 1px solid {input_border} !important;
            border-radius: 25px !important;
        }}

        .stSelectbox div[role="listbox"] {{
            background-color: {select_bg} !important;
            color: {text_color} !important;
        }}

        .stSelectbox li:hover {{
            background-color: {select_hover} !important;
        }}

        .stSelectbox label {{
            display: none !important;
        }}

        /* Custom button styling ONLY for main content, NOT sidebar */
    .block-container div[data-testid="stButton"] > button,
    .block-container div[data-testid^="FormSubmitter"] button {{
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
    .block-container div[data-testid^="FormSubmitter"] button:hover {{
        background-color: {button_hover} !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
    }}

        .block-container {{
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }}

        .cases-table-container {{
            overflow-x: auto;
            border-radius: 8px;
            margin-top: 20px;
        }}

        .cases-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .cases-table thead tr {{
            background-color: {"#f0f2f6" if is_light else "#222"};
            color: {text_color};
        }}

        .cases-table th, .cases-table td {{
            padding: 12px 16px;
            font-size: 0.95rem;
            border-bottom: 1px solid {"#e0e0e0" if is_light else "#333"};
        }}

        .cases-table tbody tr:hover {{
            background-color: {"#f9f9f9" if is_light else "#1a1a1a"};
        }}

        .stMarkdown hr {{
            display: none;
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

        </style>
        """
        , unsafe_allow_html=True)
    

    # Search 
    new_search = st.text_input("Search", value=st.session_state["search_bar_results"], placeholder="Enter a patient's name or ID", key="search_input")
    if new_search != st.session_state["search_bar_results"]:
        st.session_state["search_bar_results"] = new_search
        st.session_state.results_page_num = 1
        st.rerun()

    # --- Filters ---
    col_status, col_presumptiveTB, col_date_from, col_date_to, col_reset = st.columns([2, 2, 2, 2, 1.5])

    # Status Filter
    with col_status:
        st.markdown('<div class="filter-label">Status</div>', unsafe_allow_html=True)
        prev_status = st.session_state.get("results_status_filter", "All")
        selected_status = st.selectbox(
            "",
            ["All", "Pending", "Confirmed Positive", "Confirmed Negative"],
            index=["All", "Pending", "Confirmed Positive", "Confirmed Negative"].index(prev_status),
            key="results_status_filter_select"
        )
        if selected_status != prev_status:
            st.session_state["results_status_filter"] = selected_status
            st.session_state.results_page_num = 1
            st.rerun()
    # Presumptive TB
    with col_presumptiveTB:
        st.markdown('<div class="filter-label">Presumptive TB</div>', unsafe_allow_html=True)
        prev_presumptive = st.session_state.get("results_presumptive_filter", "All")
        selected_presumptive = st.selectbox(
            "", 
            ["All", "Positive", "Negative"],
            index=["All", "Positive", "Negative"].index(st.session_state.results_presumptive_filter),
            key="results_presumptive_filter_select"
        )
        if selected_presumptive != prev_presumptive:
            st.session_state["results_presumptive_filter"] = selected_presumptive
            st.session_state.results_page_num = 1
            st.rerun()

    # Date From
    with col_date_from:
        st.markdown('<div class="filter-label">Date From</div>', unsafe_allow_html=True)
        prev_date_from = st.session_state.get("results_date_from")
        selected_from = st.date_input(
            "Start Date", 
            value=st.session_state.results_date_from, 
            key="results_date_from_input", 
            label_visibility="collapsed"
        )
        if selected_from != prev_date_from:
            st.session_state["results_date_from"] = selected_from
            st.session_state.results_page_num = 1
            st.rerun()

    # Date To
    with col_date_to:
        st.markdown('<div class="filter-label">Date To</div>', unsafe_allow_html=True)
        prev_date_to = st.session_state.get("results_date_to")
        selected_to = st.date_input(
            "End Date", 
            value=st.session_state.results_date_to, 
            key="results_date_to_input", 
            label_visibility="collapsed"
        )
        if selected_to != prev_date_to:
            st.session_state["results_date_to"] = selected_to
            st.session_state.results_page_num = 1
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
        st.session_state["results_status_filter"] != "All" or
        st.session_state["results_presumptive_filter"] != "All" or
        st.session_state["results_date_from"] != oldest_date or
        st.session_state["results_date_to"] != date.today() or
        st.session_state["search_bar_results"].strip() != ""
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
    current_page = st.session_state.results_page_num
    start_idx = (current_page - 1) * cases_per_page
    end_idx = start_idx + cases_per_page
    cases_to_display = filtered_cases[start_idx:end_idx]

    with st.container():
        if not cases_to_display:
            st.markdown(
                "<div style='text-align: center; padding: 2rem; font-weight: bold;'>No matching results have been recorded.</div>",
                unsafe_allow_html=True
            )
        else:
            # Header
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1.5])
            col1.markdown("<b>Patient Name</b>", unsafe_allow_html=True)
            col2.markdown("<b>X-Ray Date</b>", unsafe_allow_html=True)
            col3.markdown("<b>Presumptive TB</b>", unsafe_allow_html=True)
            col4.markdown("<b>AI Confidence</b>", unsafe_allow_html=True)
            col5.markdown("<b>Status</b>", unsafe_allow_html=True)

            # Data rows
            for case in cases_to_display:
                cols = st.columns([2, 2, 2, 2, 1.5])
                cols[0].write(case['name'])
                cols[1].write(datetime.fromisoformat(case['date']).date().isoformat())
                cols[2].write(case['result'])
                cols[3].write(case['confidence'])
                status = case['diagnosis']
                color = "#ffc107" if status == "Pending" else "#4caf50" if status == "Confirmed Negative" else "#f44336"
                cols[4].markdown(f"<b style='color:{color};'>{status}</b>", unsafe_allow_html=True)
            
            pagination_controls("bottom", total_pages)
