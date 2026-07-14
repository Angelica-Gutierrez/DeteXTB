# Login.py
import streamlit as st
import base64
import random
import time
import smtplib
import os
from PIL import Image
from io import BytesIO
from datetime import datetime, timezone
from Supabase import supabase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

 
def Login(is_light=True):
    if st.session_state.get("authenticated"):
        st.session_state.page = "Dashboard"
        st.rerun()
        return
    
    def img_to_base64(path):
        img = Image.open(path)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    # Load images based on theme
    tb_logo = img_to_base64("images/logoonly-dark.png" if is_light else "images/logoonly-light.png")
    city_logo = img_to_base64("images/ctu-logo.png")
    detextb_logo = img_to_base64("images/textlogo-dark.png" if is_light else "images/textlogo-light.png")
    lock_icon = img_to_base64("images/lock.png")
    email_icon = img_to_base64("images/email.png")

    # --- CSS Styling ---
    error_text = "#b71c1c" if is_light else "#ff8a80"
    success_text = "#2e7d32" if is_light else "#69f0ae"
    pwIcon_color = "#0F0F0F" if is_light else "white"


    st.markdown(f"""
    <style>
        html, body {{
            background-color: {"white" if is_light else "#000000"};
            color: {"#000000" if is_light else "white"} !important;
            font-family: 'Arial', sans-serif;
        }}
        #MainMenu, header, footer {{
            visibility: hidden;
        }}

        section[data-testid="stSidebar"] {{
            display: none !important;
        }}

        [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
            background-color: {"white" if is_light else "#000000"} !important;
            color: {"#000000" if is_light else "white"} !important;
        }}
        .block-container {{
            padding: 0 !important;
            margin-top: -14px !important;
        }}
    
        .left-pane {{
            flex: 1;
            background: linear-gradient(to bottom, {'#F7F7F7,#919191' if is_light else '#080808,#6E6E6E'});
            padding: 2rem;
            color: {'black' if is_light else 'white'};
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 100vh;
        }}

        .logo-row {{
            display: flex;
            align-items: center;
        }}

        .left-title {{
            margin-left: 2.4rem;
            margin-top: 3rem;
            font-size: 2.4rem;
            font-weight: bold;
        }}

        .footer {{
            margin-left: 2rem;
            margin-top: auto;
            font-size: 0.9rem;
        }}

        .right-pane {{
            flex: 1;
            background: {'white' if is_light else '#000000'};
            display: flex;
            justify-content: center;
            align-items: center;
            text-align: center;
            margin-top: -2rem; 
            position: relative;
        }}

        .login-card h3 {{
            margin-top: -3rem; 
            margin-bottom: 2rem;
        }}

        .stTextInput > div {{
            margin: 0 auto 1rem auto;
            width: 60% !important; 
            background-color: {'white' if is_light else '#0F0F0F'} !important;
            border-radius: 25px !important;
            border: 1px solid {'#0F0F0F' if is_light else 'white'} !important;
        }}

        .stTextInput input {{
            background-color: {'white' if is_light else '#0F0F0F'} !important;       
            color: {'#0F0F0F' if is_light else 'white'} !important;
            caret-color: {"black" if is_light else "white"} !important;
        }}

        .stTextInput > div > div > input {{
            background-color: {'white' if is_light else '#0F0F0F'} !important;       
            color: {'#0F0F0F' if is_light else 'white'} !important;
            padding-left: 10px !important;
        }}

        .stTextInput input::placeholder {{
            color: {'#0F0F0F' if is_light else 'white'} !important;
        }}        

        /* Hide Streamlit's default input instructions */
        div.stTextInput > div > div > div[data-testid="InputInstructions"],
        [data-testid="InputInstructions"] {{
            display: none !important;
        }} 

       
        .st-key-login button,
        .st-key-back_to_login button,
        .st-key-send_reset_code button,
        .st-key-back_to_email button,
        .st-key-verify_code button,
        .st-key-back_to_verify button,
        .st-key-save_password button{{
            background-color: #d32f2f !important;
            color: white !important;
            border: none !important;
            border-radius: 25px !important;
            font-weight: bold !important;
            width: 60% !important;
            margin: 0.5rem auto 0 auto !important;
            display: block !important;
            transition: background-color 0.3s ease !important;
        }}

        .st-key-login button:hover,
        .st-key-back_to_login button:hover,
        .st-key-send_reset_code button:hover,
        .st-key-back_to_email button:hover,
        .st-key-verify_code button:hover,
        .st-key-back_to_verify button:hover,
        .st-key-save_password button:hover{{
            background-color: #f3a5a5 !important;
            color: white !important;
        }}

        /* Forgot password button styling */
        .st-key-forgot_password_btn button {{
            background-color: transparent !important;
            color: {{ 'black' if is_light else 'white' }} !important;
            border: none !important;
            border-radius: 0px !important;
            font-weight: bold !important;
            width: 60% !important;
            margin: -1.5rem auto 0.1rem auto !important;
            display: block !important;
            transition: color 0.3s ease, text-decoration 0.3s ease !important;
            text-align: right !important;
        }}

        /* Hover effect: red text with underline */
        .st-key-forgot_password_btn button:hover {{
            background-color: transparent !important;
            color: #d32f2f !important;
            text-decoration: underline !important;
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

        /* Form elements for password reset */
        .form-icon {{
            margin: 0.5rem auto 1.5rem auto;
            width: 80px;
            margin-top: -2rem;
        }}

        .form-instruction {{
            margin-bottom: 2.5rem;
            color: {"#666" if is_light else "#aaa"};
            font-size: 0.95rem;
        }}

        .button-row {{
            display: flex;
            justify-content: center;
            gap: 10px;
            width: 240px;
            margin: 0 auto;
            margin-top: -2rem;
        }}

        .button-row button {{
            flex: 1;
        }}

        .password-form-wrapper {{
            position: relative;
            width: 100%;
        }}
        
        .button-pass {{
            position: relative;
            display: flex;
            justify-content: center;
            gap: 10px;
            width: 60%;
            margin: -3rem auto 0 auto;
            z-index: 1;
        }}
        
        .button-pass button {{
            flex: 1;
            margin: 0 !important;
        }}
        
        .password-inputs {{
            margin-bottom: 0.5rem;
        }}
        
        /* Notification styles - removed left border */
        .notification-container {{
            position: fixed;
            top: 30px;
            left: 75%;
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
        
        @keyframes slideIn {{
            from {{ transform: translateY(-20px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}
        
        .notification-icon {{
            margin-right: 8px;
            font-size: 1rem;
        }}
        
        .notification-success {{
            background-color: {"#e8f5e9" if is_light else "#1b5e20"} !important;
            color: {"#000000" if is_light else "white"} !important;
        }}
        
        .notification-error {{
            background-color: {"#ffebee" if is_light else "#b71c1c"} !important;
            color: {"#000000" if is_light else "white"} !important;
        }}
        
        .notification-info {{
            background-color: {"#e3f2fd" if is_light else "#0d47a1"} !important;
            color: {"#000000" if is_light else "white"} !important;
        }}
        
        /* Theme toggle positioning */
        .theme-toggle-container {{
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 100;
        }}

    </style>
    """, unsafe_allow_html=True)


    # Initialize password reset states
    if 'reset_data' not in st.session_state:
        st.session_state.reset_data = {
            'email': None,
            'code': None,
            'code_sent_time': None,
            'verified': False,
            'notification': None
        }

    def show_notification(message, notification_type="info"):
        """Show a compact notification message at the center top"""
        icon = "ℹ️" if notification_type == "info" else "✅" if notification_type == "success" else "❌"
        st.markdown(f"""
            <div class="notification-container">
                <div class="notification notification-{notification_type}">
                    <span class="notification-icon">{icon}</span>
                    {message}
                </div>
            </div>
        """, unsafe_allow_html=True)

    def send_email(to_email: str, subject: str, message: str) -> bool:
        """Send email using SMTP"""
        try:
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            email_address = "angelgoat2003.29@gmail.com"
            email_password = "yobj vize lygi drlo"
            
            msg = MIMEMultipart()
            msg['From'] = email_address
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_address, email_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            show_notification(f"Error sending email: {str(e)}", "error")
            return False

    def send_reset_code(email: str):
        """Send 4-digit reset code to email"""
        try:
            response = supabase.table("USER_Table").select("*").eq("USER_EMAIL", email).execute()
            if not response.data:
                st.session_state.reset_data['notification'] = {
                    'message': "Email not found in our system",
                    'type': "error"
                }
                return False
            
            code = str(random.randint(1000, 9999))
            
            st.session_state.reset_data = {
                'email': email,
                'code': code,
                'code_sent_time': time.time(),
                'verified': False,
                'notification': {
                    'message': f"Verification code sent to {email}.",
                    'type': "success"
                }
            }
            
            subject = "Your Password Reset Code"
            message = f"""Hello,
            
            We received a request to reset your password for DeteXTB. 
            Your verification code is: {code}
                        
            This code will expire in 5 minutes.
                        
            If you didn't request this, please ignore this email.
                        
            The DeteXTB Team"""
            
            if not send_email(email, subject, message):
                st.session_state.reset_data['notification'] = {
                    'message': "Failed to send verification code. Please try again later.",
                    'type': "error"
                }
                return False
                
            return True
        except Exception as e:
            st.session_state.reset_data['notification'] = {
                'message': f"Error sending verification code: {str(e)}",
                'type': "error"
            }
            return False

    def verify_code(entered_code: str):
        """Verify the entered 4-digit code"""
        if not st.session_state.reset_data['code']:
            st.session_state.reset_data['notification'] = {
                'message': "No verification code exists",
                'type': "error"
            }
            return False
        
        if time.time() - st.session_state.reset_data['code_sent_time'] > 300:
            st.session_state.reset_data['notification'] = {
                'message': "Verification code has expired. Please request a new one.",
                'type': "error"
            }
            return False
        
        if entered_code == st.session_state.reset_data['code']:
            st.session_state.reset_data['verified'] = True
            st.session_state.reset_data['notification'] = {
                'message': "Email verified successfully! You can now set a new password.",
                'type': "success"
            }
            return True
        else:
            st.session_state.reset_data['notification'] = {
                'message': "Invalid verification code. Please try again.",
                'type': "error"
            }
            return False

    def update_password(new_password: str):
        """Update password in Supabase"""
        if not st.session_state.reset_data['verified']:
            st.session_state.reset_data['notification'] = {
                'message': "Email not verified",
                'type': "error"
            }
            return False
        
        try:
            supabase.table("USER_Table").update({"USER_PASSWORD": new_password})\
                .eq("USER_EMAIL", st.session_state.reset_data['email']).execute()
            
            st.session_state.reset_data['notification'] = {
                'message': "Password updated successfully! You can now login with your new password.",
                'type': "success"
            }
            return True
        except Exception as e:
            st.session_state.reset_data['notification'] = {
                'message': f"Error updating password: {str(e)}",
                'type': "error"
            }
            return False

    # Page layout
    left_col, right_col = st.columns([1.1, 1])

    # Left panel
    with left_col:
        st.markdown(f"""
            <div class="left-pane">
                <div class="logo-row">
                    <img src="data:image/png;base64,{tb_logo}" style="height: 130px;">
                    <img src="data:image/png;base64,{city_logo}" style="height: 90px;">
                </div>
                <div class="left-title">
                    AI-Assisted Presumptive<br>
                    Tuberculosis Detection<br>
                    and Mapping System
                </div>
                <div class="footer">© 2025 DeteXTB</div>
            </div>
        """, unsafe_allow_html=True)

    # Right panel
    with right_col:
        # Theme toggle
        toggle_col1, toggle_col2 = st.columns([6, 1])
        with toggle_col2:
            st.markdown("<div style='margin: 40px 20px 0px 0px;'>", unsafe_allow_html=True)
            toggle = st.toggle("🌙", value=is_light, label_visibility="collapsed", key="theme_toggle")
            st.markdown("</div>", unsafe_allow_html=True)

        if toggle != st.session_state["light_mode"]:
            st.session_state["light_mode"] = toggle
            st.rerun()

        # Show notification if exists
        if st.session_state.reset_data.get('notification'):
            show_notification(
                st.session_state.reset_data['notification']['message'],
                st.session_state.reset_data['notification']['type']
            )

        # Form states: 0=login, 1=forgot password, 2=verification, 3=new password
        current_form = 0
        if st.session_state.get("forgot_password"):
            if st.session_state.reset_data.get('verified'):
                current_form = 3  # New password form
            elif st.session_state.reset_data.get('code'):
                current_form = 2  # Verification form
            else:
                current_form = 1  # Email input form

        # Login Form
        if current_form == 0:
            st.markdown(f"""
                <div class="right-pane">
                    <div class="login-card">
                        <img src="data:image/png;base64,{detextb_logo}" width="180">
                        <h3>Login to DeteXTB</h3>
            """, unsafe_allow_html=True)

            username = st.text_input("", placeholder="Username", key="login_user", label_visibility="collapsed")
            password = st.text_input("", placeholder="Password", type="password", key="login_pass", label_visibility="collapsed")

            # Forgot password button - now styled like login button
            if st.button("Forgot password?", key="forgot_password_btn", use_container_width=True):
                st.session_state["forgot_password"] = True
                st.session_state.reset_data['notification'] = None
                st.rerun()

            # Configurable block duration (seconds)
            BLOCK_DURATION = 300  # 5 minutes

            # Initialize session state for per-user attempts
            if "user_attempts" not in st.session_state:
                st.session_state.user_attempts = {}  # {username: {"attempts": 0, "lock_until": None, "email": None}}

            # Placeholders for login button and countdown
            login_placeholder = st.empty()
            countdown_placeholder = st.empty()

            # Function to handle live countdown per user
            def show_lock_countdown(username):
                user_data = st.session_state.user_attempts[username]
                
                # Hide login button while locked
                login_placeholder.empty()
                
                # Show initial notification
                show_notification(f"Too many failed attempts for '{username}'. Locked for 5 minutes.", "error")
                
                while True:
                    remaining = int(user_data["lock_until"] - time.time())
                    if remaining <= 0:
                        # Unlock user
                        user_data["attempts"] = 0
                        user_data["lock_until"] = None
                        st.session_state.user_attempts[username] = user_data
                        countdown_placeholder.empty()
                        st.rerun()
                    mins, secs = divmod(remaining, 60)
                    countdown_placeholder.error(f"⏳ User '{username}' can try again in {mins:02d}:{secs:02d}")
                    time.sleep(1)

            # --- Always show login button at the start ---
            login_clicked = login_placeholder.button("Login", key="login", use_container_width=True)

            # --- Before allowing login, check if user is currently locked ---
            if username:
                if username not in st.session_state.user_attempts:
                    st.session_state.user_attempts[username] = {"attempts": 0, "lock_until": None, "email": None}
                
                user_data = st.session_state.user_attempts[username]
                
                # If user is locked, immediately show countdown and block login
                if user_data["lock_until"] and time.time() < user_data["lock_until"]:
                    show_lock_countdown(username)  # This will hide login button

            # --- Handle login click only if user is not locked ---
            if login_clicked:
                if not username and not password:
                    show_notification("Please enter your username and password.", "error")
                elif not username:
                    show_notification("Please enter your username.", "error")
                elif not password:
                    show_notification("Please enter your password.", "error")
                else:
                    user_data = st.session_state.user_attempts[username]
                    
                    # If user is currently locked, don't proceed
                    if user_data["lock_until"] and time.time() < user_data["lock_until"]:
                        show_lock_countdown(username)
                    
                    # Fetch user from Supabase
                    try:
                        response = supabase.table("USER_Table").select("*").eq("USER_USERNAME", username).execute()
                        user = response.data[0] if response.data else None
                    except Exception as e:
                        show_notification(f"Login error: {e}", "error")
                        st.stop()
                    
                    # Check if username exists
                    if not user:
                        show_notification("Username not registered.", "error")
                        # Clear the input fields (added this hoping it'd work, but the code's smoothly working, so... programming rule.)
                        st.session_state.login_user = ""
                        st.session_state.login_pass = ""
                        st.rerun()
                    else:
                        # Store email if exists
                        user_data["email"] = user["USER_EMAIL"]
                        
                        # Check if user is locked in database (persistent lock)
                        if user.get("USER_LOCK_UNTIL"):
                            lock_until = datetime.fromisoformat(user["USER_LOCK_UNTIL"]).timestamp()
                            if time.time() < lock_until:
                                # Hide login button while locked
                                login_placeholder.empty()
                                
                                # Show initial notification
                                show_notification("Account locked due to multiple failed attempts.", "error")
                                
                                # Live countdown loop
                                while True:
                                    remaining = int(lock_until - time.time())
                                    if remaining <= 0:
                                        # Clear the lock from database after timeout
                                        supabase.table("USER_Table").update({
                                            "USER_LOCK_UNTIL": None
                                        }).eq("USER_USERNAME", username).execute()
                                        
                                        # Refresh the page to show login form again
                                        countdown_placeholder.empty()
                                        st.rerun()
                                        
                                    mins, secs = divmod(remaining, 60)
                                    countdown_placeholder.error(f"⏳ Account locked. Please try again in {mins:02d}:{secs:02d}")
                                    time.sleep(1)
                        
                        # Check credentials
                        if password == user["USER_PASSWORD"]:
                            # Successful login - reset attempts
                            user_data["attempts"] = 0
                            user_data["lock_until"] = None
                            st.session_state.user_attempts[username] = user_data

                            # Reset database attempts & lock
                            supabase.table("USER_Table").update({
                                "USER_FAILED_ATTEMPTS": 0,
                                "USER_LOCK_UNTIL": None
                            }).eq("USER_USERNAME", username).execute()

                            # Update last active
                            supabase.table("USER_Table").update({
                                "USER_LAST_ACTIVE": datetime.now().isoformat()
                            }).eq("USER_ID", user["USER_ID"]).execute()

                            # Set session state for successful login
                            light_mode = st.session_state.get("light_mode", True)
                            st.session_state.authenticated = True
                            st.session_state.page = "Dashboard"
                            st.session_state.light_mode = light_mode
                            st.session_state.user_role = user["USER_ROLE"].lower()
                            st.session_state.user_data = {
                                "id": user["USER_ID"],
                                "name": f"{user['USER_FNAME']} {user['USER_LNAME']}",
                                "username": user["USER_USERNAME"],
                                "email": user["USER_EMAIL"],
                                "role": user["USER_ROLE"],
                                "fname": user["USER_FNAME"],        # Full first name (may contain spaces)
                                "mname": user.get("USER_MNAME", ""), # Middle name (optional)
                                "lname": user["USER_LNAME"],        # Last name
                            }
                            st.session_state["USER_ID"] = user["USER_ID"]
                            st.rerun()

                        else:
                            # Incorrect password - increment attempts
                            user_attempts = user.get("USER_FAILED_ATTEMPTS", 0) + 1
                            remaining_attempts = 3 - user_attempts

                            # Update session state
                            user_data["attempts"] = user_attempts
                            st.session_state.user_attempts[username] = user_data

                            # Update database attempts
                            supabase.table("USER_Table").update({
                                "USER_FAILED_ATTEMPTS": user_attempts
                            }).eq("USER_USERNAME", username).execute()

                            if user_attempts >= 3:
                                # Lock user in session state
                                user_data["lock_until"] = time.time() + BLOCK_DURATION
                                st.session_state.user_attempts[username] = user_data

                                # Lock user in database
                                lock_until_time = datetime.fromtimestamp(time.time() + BLOCK_DURATION, timezone.utc).isoformat()
                                supabase.table("USER_Table").update({
                                    "USER_LOCK_UNTIL": lock_until_time
                                }).eq("USER_USERNAME", username).execute()

                                # Send security alert email
                                if user_data.get("email"):
                                    subject = "DeteXTB Security Alert"
                                    message = f"""
                        Hello {username},

                        There have been multiple failed login attempts to your DeteXTB account.
                        Your account is temporarily locked for {BLOCK_DURATION // 60} minutes for security reasons.

                        If this wasn't you, please change your password immediately.
                        Otherwise, you can ignore this email and try logging in again after the lock period.

                        The DeteXTB Team
                        """
                                    send_email(user_data["email"], subject, message)

                                # Show live countdown and hide login button
                                show_lock_countdown(username)

                            else:
                                show_notification(f"Incorrect password. Attempts left: {remaining_attempts}", "error")

                            # Clear the password field
                            st.session_state.login_pass = ""
                            st.rerun()

            st.markdown("</div></div>", unsafe_allow_html=True)

        # Forgot Password Form (Email Input)
        elif current_form == 1:
            st.markdown(f"""
                <div class="right-pane">
                    <div class="login-card">
                        <img src="data:image/png;base64,{detextb_logo}" width="180">
                        <h3>Forgot Password</h3>
                        <div class="form-icon">
                            <img src="data:image/png;base64,{lock_icon}" width="80">
                        </div>
                        <div class="form-instruction">
                            Please enter your email address to receive a verification code
                        </div>
            """, unsafe_allow_html=True)

            email = st.text_input("", placeholder="Enter your email", key="reset_email", label_visibility="collapsed")

            spinner_placeholder = st.empty()

            st.markdown('<div class="button-row">', unsafe_allow_html=True)
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Back", key="back_to_login", use_container_width=True):
                    st.session_state["forgot_password"] = False
                    st.session_state.reset_data = {
                        'email': None,
                        'code': None,
                        'code_sent_time': None,
                        'verified': False,
                        'notification': None
                    }
                    st.rerun()
            with col2:
                if st.button("Send", key="send_reset_code", use_container_width=True):
                    if email:
                        with spinner_placeholder.container():
                            st.markdown("""
                                <div style='display: flex; flex-direction: column; align-items: center; margin: 0.1rem 0;'>
                                <div class="loader"></div>
                                <p style='margin: 0.2rem 0 -1.5rem 0; color: #b71c1c; font-weight: 500;'>Sending verification code...</p>
                                </div>
                                <style>
                                .loader {
                                    border: 4px solid #f3f3f3;
                                    border-top: 4px solid #b71c1c;
                                    border-radius: 50%;
                                    width: 30px;
                                    height: 30px;
                                    animation: spin 1s linear infinite;
                                }

                                @keyframes spin {
                                    0% { transform: rotate(0deg); }
                                    100% { transform: rotate(360deg); }
                                }
                                </style>
                            """, unsafe_allow_html=True)

                            # Simulate sending
                            send_success = send_reset_code(email)
                            if send_success:
                                st.rerun()
                    else:
                        show_notification("Please enter your email.", "error")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)

        # Verification Code Form
        elif current_form == 2:
            st.markdown(f"""
                <div class="right-pane">
                    <div class="login-card">
                        <img src="data:image/png;base64,{detextb_logo}" width="180">
                        <h3>Verify Your Email</h3>
                        <div class="form-icon">
                            <img src="data:image/png;base64,{email_icon}" width="80">
                        </div>
                        <div class="form-instruction">
                            Please enter the 4-digit code sent to {st.session_state.reset_data['email']}
                        </div>
            """, unsafe_allow_html=True)

            verification_code = st.text_input(
                "", 
                placeholder="Enter 4-digit code", 
                key="verification_code_input",
                label_visibility="collapsed",
                max_chars=4
            )

            st.markdown('<div class="button-row">', unsafe_allow_html=True)
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Back", key="back_to_email", use_container_width=True):
                    st.session_state.reset_data['code'] = None
                    st.session_state.reset_data['notification'] = None
                    st.rerun()
            with col2:
                if st.button("Verify", key="verify_code", use_container_width=True):
                    if verification_code and len(verification_code) == 4:
                        if verify_code(verification_code):
                            st.rerun()
                    else:
                        show_notification("Please enter a complete 4-digit code", "error")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)

        # New Password Form
        elif current_form == 3:
            st.markdown(f"""
                <div class="right-pane">
                    <div class="login-card">
                        <img src="data:image/png;base64,{detextb_logo}" width="180">
                        <h3>Create New Password</h3>
                        <div class="form-instruction">
                            Your new password must be different from previously used password
                        </div>
                        <div class="password-form-wrapper">
                            <div class="password-inputs">
            """, unsafe_allow_html=True)

            new_password = st.text_input("", placeholder="New Password", type="password", key="new_pass", label_visibility="collapsed")
            confirm_password = st.text_input("", placeholder="Confirm Password", type="password", key="confirm_pass", label_visibility="collapsed")

            st.markdown('<div class="button-pass">', unsafe_allow_html=True)
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Back", key="back_to_verify", use_container_width=True):
                    st.session_state.reset_data['verified'] = False
                    st.session_state.reset_data['notification'] = None
                    st.rerun()
            with col2:
                if st.button("Save", key="save_password", use_container_width=True):
                    if not new_password or not confirm_password:
                        show_notification("Please enter and confirm your new password", "error")
                    elif new_password != confirm_password:
                        show_notification("Passwords do not match", "error")
                    elif len(new_password) < 8:
                        show_notification("Password must be at least 8 characters long", "error")
                    else:
                        if update_password(new_password):
                            # Reset all states
                            st.session_state["forgot_password"] = False
                            st.session_state.reset_data = {
                                'email': None,
                                'code': None,
                                'code_sent_time': None,
                                'verified': False,
                                'notification': {
                                    'message': "Password updated successfully! You can now login with your new password.",
                                    'type': "success"
                                }
                            }
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)