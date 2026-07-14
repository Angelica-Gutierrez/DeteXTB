# Privacy.py for Manager

import streamlit as st
import time
from datetime import datetime, timedelta
from Supabase import supabase  # Your Supabase client

def Privacy(is_light=True):

    # st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    # --- Title and Theme Toggle ---
    col_title, col_toggle = st.columns([6, 1])
    with col_title:
        st.markdown("<h4>Privacy Policy</h4>", unsafe_allow_html=True)
    with col_toggle:
        new_toggle = st.toggle("🌙", value=is_light, key="theme_toggle", label_visibility="collapsed")

    if new_toggle != st.session_state["light_mode"]:
        st.session_state["light_mode"] = new_toggle
        st.rerun()

    # --- Theme & Colors ---
    text_color = "black" if is_light else "white"
    bg_color = "white" if is_light else "#0e0e0e"

    # --- Apply same global CSS as Dashboard ---
    st.markdown(f"""
    <style>
        #MainMenu, header, footer {{visibility: hidden;}}
        html, body, .stApp {{
            background-color: {bg_color} !important;
            color: {text_color} !important;
            font-family: 'Arial', sans-serif;
        }}
        h1,h2,h3,h4,h5,h6 {{
            color: {text_color} !important;
        }}
        section[data-testid="stSidebar"] {{
            display: none;
        }}
        .block-container {{
            margin: 2rem auto !important;       
            padding: 2rem 3rem !important;      
            max-width: 900px;                  
            text-align: justify;  /* <-- This justifies your text */
        }}
        .st-key-back button {{
            background-color: #d32f2f !important;
            color: white !important;
            border: none !important;
            border-radius: 25px !important;
            font-weight: bold !important;
            width: 150% !important;
            display: block !important;
            margin: 0.5rem auto !important;
            transition: background-color 0.3s ease !important;
        }}
        .st-key-back button:hover {{
            background-color: #f3a5a5 !important;
            color: white !important;
        }}
        .st-key-understand button {{
            background-color: #d32f2f !important;
            color: white !important;
            border: none !important;
            border-radius: 25px !important;
            font-weight: bold !important;
            width: 150% !important;
            display: block !important;
            margin: 0.5rem 0 0.5rem 270% !important;  
            transform: translateX(-50%);  
            transition: background-color 0.3s ease !important;
        }}
        .st-key-understand button:hover {{
            background-color: #f3a5a5 !important;
            color: white !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    # --- Privacy Content ---
    st.markdown("""
            Welcome to **DeteXTB**, an AI-assisted system designed to support presumptive tuberculosis detection and mapping. Protecting the privacy and security of patient and case information is a top priority.

            As a manager responsible for supervising clinical workflows, confirming diagnoses, and monitoring system use, using this system comes with specific responsibilities:

            <strong>1. Authorized Use Only</strong><br>
            You will use the system responsibly and only for its intended purpose: assisting in presumptive tuberculosis detection, recording, and reporting. Managers have additional oversight responsibilities and must ensure proper use by staff under their supervision.

            <strong>2. Confidentiality</strong><br>
            All patient and case information entered, accessed, or processed must be kept confidential. You will not disclose sensitive information to unauthorized individuals or third parties. As a manager, you are responsible for ensuring that all staff members comply with confidentiality requirements.

            <strong>3. Data Security</strong><br>
            You agree to follow organizational guidelines for protecting data, including secure login practices and avoiding unauthorized sharing of credentials. Managers are responsible for monitoring access and reporting any suspected breaches or misuse.

            <strong>4. Compliance</strong><br>
            You will comply with all applicable privacy, data protection, and health information regulations. Managers must ensure that team members are also trained and compliant with these regulations.

            <strong>5. System Integrity</strong><br>
            You will not attempt to alter, bypass, or misuse system functionality. Managers are responsible for monitoring system use, approving workflows, and reporting anomalies.

            By continuing to use DeteXTB, you confirm your understanding and acceptance of these responsibilities. Thank you for helping maintain the <strong>confidentiality, integrity, and security</strong> of patient information.
            """, 
            unsafe_allow_html=True
        )

    # --- Buttons at the Bottom ---
    col1, col2 = st.columns(2)
    user_id = st.session_state.get("USER_ID")  # Make sure user_id is available from session

    with col1:
        if st.button("Back", key="back"):
            st.session_state["active_page"] = "Dashboard"
            st.rerun()

    with col2:
        if st.button("I Understand", key="understand"):
            if user_id:
                # Save new expiry (2 minutes for testing)
                new_expiry = (datetime.now() + timedelta(minutes=2)).isoformat()
                supabase.table("USER_Table").update({
                    "USER_PRIVACY_ACCEPTED_UNTIL": new_expiry
                }).eq("USER_ID", user_id).execute()
            
            st.session_state["privacy_ack"] = True
            st.session_state["active_page"] = "Dashboard"
            st.rerun()
