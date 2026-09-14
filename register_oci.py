import streamlit as st
import oracledb
import os
import re

# ----------------------------------------------------
# 1. ORACLE CLOUD ENGINE CONFIGURATION (THIN MODE)
# ----------------------------------------------------
WALLET_DIR = r"D:\Personal\AIrelatedDocs\Oracle AI\Project\wallet_files"

def insert_candidate_to_oracle(name, email, skills_string, exp_years, pdf_bytes):
    # Formulate a bulletproof, standardized text block in the background
    # This completely insulates the database from user formatting mistakes!
    consolidated_matrix = f"{float(exp_years)} Yrs Experience | Skills: {skills_string}"

    connection_params = {
        "user": "ADMIN",
        "password": st.secrets["db_password"],      # 🔒 Secured via Streamlit Vault
        "dsn": "search_low",                       
        "config_dir": WALLET_DIR,                  
        "wallet_location": WALLET_DIR,             
        "wallet_password": st.secrets["wallet_password"],  
        "ssl_server_dn_match": False               
    }
    
    try:
        conn = oracledb.connect(**connection_params)
        cursor = conn.cursor()
        
        sql_insert = """
            INSERT INTO skills (name, email, skills_matrix, resume_blob)
            VALUES (:1, :2, :3, :4)
        """
        cursor.execute(sql_insert, [name, email, consolidated_matrix, pdf_bytes])
        conn.commit()
        
        cursor.close()
        conn.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

# ----------------------------------------------------
# 2. RUNTIME UI LAYOUT & FORM CONSTRAINTS
# ----------------------------------------------------
st.set_page_config(page_title="Candidate Cloud Registration Portal", page_icon="📝", layout="centered")

st.title("☁️ OCI Profile Registration Portal")
st.write("Submit your professional credentials and stream your resume PDF directly into our live Oracle Cloud Autonomous Database.")
st.markdown("<hr style='margin: 15px 0; border: 0; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)

with st.form("registration_form", clear_on_submit=True):
    st.subheader("👤 Personal Details & Core Expertise")
    
    full_name = st.text_input("Full Name", placeholder="e.g., Jane Doe").strip()
    email_address = st.text_input("Email Address", placeholder="e.g., jane.doe@example.com").strip()
    
    # UI UPGRADE: Dedicated, clean independent field block inputs
    experience_years = st.number_input("Total Years of Professional Experience", min_value=0.0, max_value=40.0, value=1.0, step=0.5, format="%.1f")
    skills_matrix = st.text_area("Core Skills (Separate multiple skills with a comma)", placeholder="e.g., Oracle DBA, OCI, PL/SQL, Python").strip()
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📄 Upload Profile Document")
    uploaded_file = st.file_uploader("Choose your Resume PDF file", type=["pdf"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    submit_button = st.form_submit_button("🚀 Submit Profile to Oracle Cloud")

# ----------------------------------------------------
# 3. FORM VALIDATION & EXECUTION LOGIC
# ----------------------------------------------------
if submit_button:
    if not full_name:
        st.error("❌ Form Submission Failed: Please fill in your Full Name.")
    elif not email_address or not re.match(r"[^@]+@[^@]+\.[^@]+", email_address):
        st.error("❌ Form Submission Failed: Please enter a valid Email Address.")
    elif experience_years <= 0:
        st.error("❌ Form Submission Failed: Experience must be greater than 0 years.")
    elif not skills_matrix:
        st.error("❌ Form Submission Failed: Please enter at least one core skill.")
    elif uploaded_file is None:
        st.error("❌ Form Submission Failed: Please upload your Resume PDF file.")
    else:
        with st.spinner("Processing forms and streaming binary bytes into OCI Autonomous Database..."):
            try:
                binary_pdf_bytes = uploaded_file.read()
                
                success, error_msg = insert_candidate_to_oracle(
                    full_name, email_address, skills_matrix, experience_years, binary_pdf_bytes
                )
                
                if success:
                    st.success(f"🎉 Marvelous! Profile for **'{full_name}'** with **{experience_years} years** of experience has been successfully streamed into your Oracle Cloud table live!")
                    st.balloons()
                else:
                    st.error(f"❌ Oracle Cloud Transaction Failure: Could not execute row insertion.\n\nError Log: {error_msg}")
                    
            except Exception as system_err:
                st.error(f"❌ Application Critical Runtime Exception Error: {system_err}")
