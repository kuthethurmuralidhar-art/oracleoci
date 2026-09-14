import streamlit as st
import oracledb
import os
import re

# ----------------------------------------------------
# 1. ORACLE CLOUD ENGINE CONFIGURATION (THIN MODE)
# ----------------------------------------------------
# Maps absolute path to your unzipped wallet folder directory
WALLET_DIR = r"D:\Personal\AIrelatedDocs\Oracle AI\Project\wallet_files"

def insert_candidate_to_oracle(name, email, skills, pdf_bytes):
    # Configure connection parameters using your secure Streamlit Secrets
    connection_params = {
        "user": "ADMIN",
        "password": st.secrets["db_password"],      # 🔒 Secured via hidden vault configuration
        "dsn": "search_low",                       # Connect utilizing the low-latency string tag
        "config_dir": WALLET_DIR,                  # Directs driver to find sqlnet.ora
        "wallet_location": WALLET_DIR,             # Directs driver to find cwallet.sso
        "wallet_password": st.secrets["wallet_password"], # 🔒 Secure wallet password
        "ssl_server_dn_match": False               # Bypasses local hostname mismatches safely
    }
    
    try:
        # Establish link using Python's native Thin Mode network layer
        conn = oracledb.connect(**connection_params)
        cursor = conn.cursor()
        
        # SQL INSERT statement using secure relational positional bind variables
        sql_insert = """
            INSERT INTO skills (name, email, skills_matrix, resume_blob)
            VALUES (:1, :2, :3, :4)
        """
        
        cursor.execute(sql_insert, [name, email, skills, pdf_bytes])
        
        # Commit the transaction permanently to your OCI cloud tablespace storage
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
st.write("Submit your credentials and stream your resume PDF directly into your live Oracle Cloud Autonomous Database.")
st.markdown("<hr style='margin: 15px 0; border: 0; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)

# Build a native clean entry form block container
with st.form("registration_form", clear_on_submit=True):
    st.subheader("👤 Personal Details & Core Expertise")
    
    # Form Input Widgets
    full_name = st.text_input("Full Name", placeholder="e.g., Jane Doe").strip()
    email_address = st.text_input("Email Address", placeholder="e.g., jane.doe@example.com").strip()
    skills_matrix = st.text_area("Skills Matrix (Separate multiple skills with a comma)", placeholder="e.g., Oracle DBA, OCI, PL/SQL, Python").strip()
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📄 Upload Profile Document")
    
    # Native File Uploader constraint to accept single PDF assets
    uploaded_file = st.file_uploader("Choose your Resume PDF file", type=["pdf"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Form Submit Action Button Execution trigger
    submit_button = st.form_submit_button("🚀 Submit Profile to Oracle Cloud")

# ----------------------------------------------------
# 3. FORM VALIDATION & EXECUTION LOGIC
# ----------------------------------------------------
if submit_button:
    # Strict validation rules to ensure required fields are filled out properly
    if not full_name:
        st.error("❌ Form Submission Failed: Please fill in your Full Name.")
    elif not email_address or not re.match(r"[^@]+@[^@]+\.[^@]+", email_address):
        st.error("❌ Form Submission Failed: Please enter a valid Email Address.")
    elif not skills_matrix:
        st.error("❌ Form Submission Failed: Please enter at least one core skill.")
    elif uploaded_file is None:
        st.error("❌ Form Submission Failed: Please upload your Resume PDF file.")
    else:
        # Display an active visual spinner loader on screen
        with st.spinner("Processing files and streaming binary bytes into OCI Autonomous Database..."):
            try:
                # Read the file object stream buffer into raw data array bytes directly out of memory
                binary_pdf_bytes = uploaded_file.read()
                
                # Execute the database write function loop
                success, error_msg = insert_candidate_to_oracle(full_name, email_address, skills_matrix, binary_pdf_bytes)
                
                if success:
                    st.success(f"🎉 Marvelous! Profile for **'{full_name}'** has been successfully streamed into your Oracle Cloud table live!")
                    st.balloons()
                else:
                    st.error(f"❌ Oracle Cloud Transaction Failure: Could not execute row insertion.\n\nError Log: {error_msg}")
                    
            except Exception as system_err:
                st.error(f"❌ Application Critical Runtime Exception Error: {system_err}")
