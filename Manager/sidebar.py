# sidebar.py for Manager

import streamlit as st 
import base64
from streamlit import switch_page
import os

def main():  # Wrap your sidebar layout in a function
    if not st.session_state.get("authenticated"):
        import Login
        Login.Login()
        st.stop()

    from Manager.Dashboard import Dashboard
    from Manager.Manage_Cases import Manage_Cases
    from Manager.Heatmap import Heatmap
    from Manager.Reports import Reports
    from Manager.Users import Users
    from Manager.Account import Account

    if not st.session_state.get("authenticated"):
        st.session_state.page = "Login"
    elif "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    # Always read the current mode into a variable
    is_light = st.session_state.get("light_mode", True)


    # --- Load and Encode Logo as base64 ---
    def get_base64_logo(image_path):
        # Always resolve relative to sidebar.py's own location
        base_dir = os.path.dirname(__file__)  # e.g., .../DeteXTB-System/Receptionist
        abs_path = os.path.join(base_dir, image_path)  # e.g., ../images/logo_light.png
        with open(abs_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()

    logo_path = "../images/logo_light.png" if is_light else "../images/logo_dark.png"
    logo_base64 = get_base64_logo(logo_path)

    # --- Function to get formatted display name ---
    def get_display_name():
        """Smartly formats the display name for 13-character sidebar limit."""
        user_data = st.session_state.user_data
        fname = user_data.get("fname", "").strip()
        mname = user_data.get("mname", "").strip()
        lname = user_data.get("lname", "").strip()
        
        SIDEBAR_LIMIT = 13  # Maximum characters for sidebar display
        
        # Rule 1: Try First + Last name
        first_last = f"{fname} {lname}".strip()
        if len(first_last) <= SIDEBAR_LIMIT:
            return first_last
        
        # Rule 2: Display first name only (with both parts if applicable)
        if len(fname) <= SIDEBAR_LIMIT:
            return fname
        
        # Rule 3: If first name is too long, try abbreviation with last name
        first_name_parts = fname.split()
        if len(first_name_parts) > 1:
            # Multiple first names - abbreviate all parts (e.g., P.S. Vancouver)
            initials = "".join([part[0] + "." for part in first_name_parts])
            abbreviated = f"{initials} {lname}".strip()
            if len(abbreviated) <= SIDEBAR_LIMIT:
                return abbreviated
        
        # Rule 4: Final fallback - abbreviate everything (First + Middle + Last)
        # Build abbreviation parts intelligently
        abbreviation_parts = []
        
        # Handle first name
        if fname:
            f_initials = "".join([part[0] + "." for part in fname.split()])
            abbreviation_parts.append(f_initials)
        
        # Handle last name - if it's too long, abbreviate it too
        if lname:
            if len(lname) > 8:  # If last name is long, use initial
                abbreviation_parts.append(lname[0] + ".")
            else:
                abbreviation_parts.append(lname)
        
        full_abbreviation = " ".join(abbreviation_parts).strip()
        if len(full_abbreviation) <= SIDEBAR_LIMIT:
            return full_abbreviation
        
        # If still too long, use minimal initials only
        minimal_initials = ""
        if fname:
            minimal_initials += fname[0] + "."
        if lname:
            minimal_initials += lname[0] + "."
        
        return minimal_initials.strip(" .")
    

    # --- Custom Sidebar Styling ---
    SIDEBAR_BG = "#D9D9D9" if is_light else "#1c1c1c"         
    TEXT_COLOR = "#000000" if is_light else "#ffffff"         
    HOVER_COLOR = "#C2C2C2" if is_light else "#666666"      
    ACTIVE_COLOR = HOVER_COLOR
    BUTTON_TEXT_COLOR = TEXT_COLOR
    BUTTON_COLOR = "#d32f2f"
    BUTTON_HOVER = "#f3a5a5"

    st.markdown(f"""
        <style>
        #MainMenu, header, footer {{
            visibility: hidden;
        }}
                
        [data-testid="stSidebarCollapseButton"] {{
        display: none;
        }}

        [data-testid="stDialog"] button[aria-label="Close"] {{
        display: none !important;
        }}
                
        section[data-testid="stSidebar"] {{
            background-color: {SIDEBAR_BG};
            padding: 1rem 0.8rem 0.5rem 0.8rem;
            width: 250px !important;
            border-radius: 10px;
            margin: 10px;
        }}

        ::-webkit-scrollbar {{ display: none; }}

        .sidebar-logo {{
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 140px;
            padding-bottom: 2rem;
            margin-top: -40px;
        }}

        .account {{
            color: {TEXT_COLOR};
            font-size: 13px; /* Smaller font */
        }}

        .sidebar-icon {{
            padding-top: 4px;
            margin-left: 25px;
        }}

        .sidebar-icon-dashboard,
        .sidebar-icon-logout {{
            padding-top: 4px;
            margin-left:30px;
        }}

        .sidebar-icon-account {{
            padding-top: 4px;
            margin-left: 18px;
        }}

        /* Default sidebar buttons style */
        .st-key-dashboard button, 
        .st-key-cases button,
        .st-key-heatmap button,
        .st-key-reports button,
        .st-key-users button,
        .st-key-account button,
        .st-key-logout button  {{
            background-color: transparent;
            color: {BUTTON_TEXT_COLOR} !important;
            border: none !important;
            border-radius: 25px !important;
            text-align: right;
            width: auto;
            justify-content: flex-end;
            margin-right: 8px;
            padding: 1px;
        }} 

        .logout-text {{
            background-color: {'#fff9d0' if st.session_state['light_mode'] else '#332d04'} !important;
            color: {'#bd2f2f' if st.session_state['light_mode'] else '#ea7b64'} !important;
            padding: 10px 15px !important;
            border-radius: 4px !important ;
            margin-bottom: 13px !important;
            font-weight: semibold !important;
            }}

        .custom-warning {{
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

    # --- Sidebar Content ---
    with st.sidebar:
        st.markdown(f'<img src="data:image/png;base64,{logo_base64}" class="sidebar-logo">', unsafe_allow_html=True)

        # --- Navigation Buttons with Icons ---
        def nav_button_with_icon(label, icon_path, key):
            col1, col2 = st.columns([0.4, 0.8])
            with col1:
                st.markdown(f'<img src="data:image/png;base64,{get_base64_logo(icon_path)}" width="26" class="sidebar-icon">', unsafe_allow_html=True)
            with col2:
                if st.button(label, key=key):
                    st.session_state.page = label

        # --- Dashboard with smaller icon ---
        col1, col2 = st.columns([0.4, 0.8])
        with col1:
            st.markdown(
                f'<img src="data:image/png;base64,{get_base64_logo("../images/dashboard.png")}" width="20" class="sidebar-icon-dashboard">',
                unsafe_allow_html=True
            )
        with col2:
            if st.button("Dashboard", key="dashboard"):
                st.session_state.page = "Dashboard"

        nav_button_with_icon("Manage Cases", "../images/cases.png", "cases")
        nav_button_with_icon("Heatmap", "../images/heatmap.png", "heatmap")
        nav_button_with_icon("Reports", "../images/reports.png", "reports")
        nav_button_with_icon("Users", "../images/users.png", "users")

        # --- Account Name (with larger icon) ---
        col1, col2 = st.columns([0.4, 0.8])
        with col1:
            st.markdown(
                f'<img src="data:image/png;base64,{get_base64_logo("../images/account.png")}" width="45" class="sidebar-icon-account">',
                unsafe_allow_html=True
            )
        with col2:
            display_name = get_display_name()
            if st.button(display_name, key="account"):
                st.session_state.page = "Account Name"

        # --- Manager text directly below Account Name ---
        st.markdown(f"<div class='account' style='margin-left: 68px; margin-top: -28px;font-size: 14px;'>TB DOTS Manager</div>", unsafe_allow_html=True)

        # --- Logout Button ---
        logout_icon_path = "../images/logout.png"
        col1, col2 = st.columns([0.4, 0.8])
        
        def trigger_logout():
            st.session_state.show_logout_confirm = True

        with col1:
            st.markdown(
                f'<img src="data:image/png;base64,{get_base64_logo(logout_icon_path)}" width="24" class="sidebar-icon-logout">',
                unsafe_allow_html=True
            )
        with col2:
            st.button("Logout", key="logout", on_click=trigger_logout)

        # --- Show confirmation dialog ---
        if st.session_state.get("show_logout_confirm", False):

            @st.dialog("Confirm Logout")
            def logout_dialog():
                st.write("You are about to log out of DeteXTB. Make sure all patient data has been properly saved and submitted before continuing. Do you want to proceed?")

                st.markdown("""
                    <style>
                        .st-key-confirm_logout button {
                            background-color: #c9302c !important;
                            color: white !important;
                            border: none !important;
                            border-radius: 25px !important;
                            padding: 0.5em 1.5em !important;
                            font-weight: bold !important;
                            transition: background-color 0.3s ease;
                            cursor: pointer !important;
                            width: 100%;
                            margin-bottom: 10px;
                        }
                        .st-key-confirm_logout button:hover {
                            background-color: #d9534f !important;
                        }

                        .st-key-cancel_logout button {
                            background-color: #c9302c !important;
                            color: white !important;
                            border: none !important;
                            border-radius: 25px !important;
                            padding: 0.5em 1.5em !important;
                            font-weight: bold !important;
                            transition: background-color 0.3s ease;
                            cursor: pointer !important;
                            width: 100%;
                            margin-left: 220% !important;
                            display: block !important;
                            margin-bottom: 10px;
                        }
                        .st-key-cancel_logout button:hover {
                            background-color: #d9534f !important;
                        }
                    </style>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes", key="confirm_logout"):
                        light_mode = st.session_state.get("light_mode", True)
                        privacy_shown = st.session_state.get("privacy_shown", False)
                        
                        st.session_state.clear()
                        st.session_state["light_mode"] = light_mode
                        st.session_state["page"] = "Login"
                        st.session_state["privacy_shown"] = privacy_shown
                        st.rerun()

                with col2:
                    if st.button("No", key="cancel_logout"):
                        st.session_state.show_logout_confirm = False
                        st.rerun()

            logout_dialog()

    # --- Map page names to their button keys for CSS targeting ---
    page_key_map = {
        "Dashboard": "dashboard",
        "Manage Cases": "cases",
        "Heatmap": "heatmap",
        "Reports": "reports",
        "Users": "users",
    }

    active_key = page_key_map.get(st.session_state.page, "")

    # --- Reset styles for all buttons and highlight only active page button ---
    if active_key:
        shared_style = f"""
        background-color: {ACTIVE_COLOR} !important;
        color: {TEXT_COLOR} !important;
        border-radius: 25px !important;
        white-space: nowrap !important;
        font-size: 14px !important;
        line-height: 20px !important;
        padding: 4px 10px 4px 4px !important;
        """

        st.markdown(f"""
        <style>
        /* Reset all sidebar buttons to default */
        .st-key-dashboard button,
        .st-key-cases button,
        .st-key-heatmap button,
        .st-key-reports button,
        .st-key-users button {{
            background-color: transparent !important;
            color: {BUTTON_TEXT_COLOR} !important;
            font-weight: normal !important;
            padding: 1px !important;
            border-radius: 25px !important;
            white-space: nowrap !important;
        }}

        /* Apply shared hover style */
        .st-key-dashboard button:hover,
        .st-key-cases button:hover,
        .st-key-heatmap button:hover,
        .st-key-reports button:hover,
        .st-key-users button:hover {{
            {shared_style}
            font-weight: normal !important;
        }}

        /* Apply shared active style + bold */
        .st-key-{active_key} button * {{
            {shared_style}
            font-weight: bold !important;
        }}
        </style>
        """, unsafe_allow_html=True)


    # --- Main Page Content ---
    if st.session_state.page == "Dashboard":
        Dashboard(is_light=is_light)
    elif st.session_state.page == "Manage Cases":
        Manage_Cases(is_light=is_light)
    elif st.session_state.page == "Heatmap":
        Heatmap(is_light=is_light)
    elif st.session_state.page == "Reports":
        Reports(is_light=is_light)
    elif st.session_state.page == "Users":
        Users(is_light=is_light)
    elif st.session_state.page == "Account Name":
        Account(is_light=is_light)
