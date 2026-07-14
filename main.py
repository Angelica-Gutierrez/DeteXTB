# main.py

import streamlit as st
import tensorflow as tf
import os
import gdown

st.set_page_config(page_title="DeteXTB", layout="wide")

# --- Model Download & Load ---
MODEL_FILE = "deteXTB_final_mandaue_model.keras"
MODEL_URL = "https://drive.google.com/uc?id=19Qi6uLhoTAz6QrH9cQC9oRR9rkSe5T91"

if not os.path.exists(MODEL_FILE):
    gdown.download(MODEL_URL, MODEL_FILE, quiet=False)
    
if "current_dialog" not in st.session_state:
    st.session_state.current_dialog = None  # Tracks the dialog currently open

if "model" not in st.session_state:
    st.session_state.model = tf.keras.models.load_model(MODEL_FILE)

# --- Auth and Theme Defaults ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "light_mode" not in st.session_state:
    st.session_state.light_mode = True
if "user_role" not in st.session_state:
    st.session_state.user_role = None

# --- Route ---
if not st.session_state.authenticated:
    import Login
    Login.Login(is_light=st.session_state.light_mode)
else:
    if st.session_state.user_role == "receptionist":
        from Receptionist import sidebar as receptionist_sidebar
        receptionist_sidebar.main()
    elif st.session_state.user_role == "manager":
        from Manager import sidebar as manager_sidebar
        manager_sidebar.main()
    else:
        st.error("Unknown user role.")