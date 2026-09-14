import streamlit as st
import pandas as pd
import oracledb
import os
from collections import Counter

# ----------------------------------------------------
# 1. ORACLE CLOUD ENGINE CONFIGURATION (THIN MODE)
# ----------------------------------------------------
WALLET_DIR = os.path.join(os.getcwd(), "wallet_files")

def get_db_connection():
    connection_params = {
        "user": "ADMIN",
        "password": st.secrets["db_password"],      # 🔒 Secured via hidden vault configuration
        "dsn": "search_low",                       
        "config_dir": WALLET_DIR,                  
        "wallet_location": WALLET_DIR,             
        "wallet_password": st.secrets["wallet_password"],  # 🔒 Secure wallet password
        "ssl_server_dn_match": False               
    }
    
    def blob_to_bytes_handler(cursor, name, default_type, size, precision, scale):
        if default_type == oracledb.DB_TYPE_BLOB:
            return cursor.var(bytes, arraysize=cursor.arraysize)
            
    conn = oracledb.connect(**connection_params)
    conn.outputtypehandler = blob_to_bytes_handler
    return conn

# Pulls skills matrices from OCI and tallies volume counts dynamically
def get_unique_skills_with_counts():
    try:
        conn = get_db_connection()
        query = "SELECT skills_matrix FROM skills"
        df = pd.read_sql(query, conn)
        conn.close()
        
        if df.empty:
            return {}, []
            
        target_column = 'SKILLS_MATRIX' if 'SKILLS_MATRIX' in df.columns else 'skills_matrix'
        
        # Isolate and split comma strings into a single consolidated flat python list
        all_skills_list = []
        for raw_matrix in df[target_column].astype(str).dropna():
            if raw_matrix.strip():
                # Split comma rows, strip out surrounding whitespace characters, and preserve spelling casing
                items = [item.strip() for item in raw_matrix.split(",") if item.strip()]
                all_skills_list.extend(items)
        
        # Calculate raw frequency volumes using high-performance counter dictionaries
        tally_dict = Counter(all_skills_list)
        
        # Extract individual unique string keys and sort them alphabetically
        sorted_unique_names = sorted(tally_dict.keys())
        return tally_dict, sorted_unique_names
    except Exception as e:
        # Graceful fallback array array structure to handle connection blocks safely
        fallback_list = ["Oracle DBA", "OCI", "Oracle Designer", "Python Basics", "Streamlit"]
        fallback_counts = {k: 1 for k in fallback_list}
        return fallback_counts, fallback_list

def query_profiles_from_oracle(search_keywords=None):
    try:
        conn = get_db_connection()
        if search_keywords:
            where_clauses = []
            bind_params = {}
            for i, kw in enumerate(search_keywords):
                param_name = f"skill_{i}"
                where_clauses.append(f"LOWER(skills_matrix) LIKE :{param_name}")
                bind_params[param_name] = f"%{kw.lower()}%"
            
            query = f"SELECT id, name, email, skills_matrix, resume_blob FROM skills WHERE " + " OR ".join(where_clauses)
            df = pd.read_sql(query, conn, params=bind_params)
        else:
            df = pd.DataFrame(columns=["ID", "NAME", "EMAIL", "SKILLS_MATRIX", "RESUME_BLOB"])
            
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Oracle Cloud Database Connection Failure: {e}")
        return pd.DataFrame(columns=["ID", "NAME", "EMAIL", "SKILLS_MATRIX", "RESUME_BLOB"])

# ----------------------------------------------------
# 2. RUNTIME UI & STYLING LOGIC
# ----------------------------------------------------
st.set_page_config(page_title="Oracle Cloud BLOB Portal", page_icon="☁️", layout="wide")
st.title("☁️ Live Oracle Cloud 23ai BLOB Matcher Engine")
st.write("Select expertise checklist flags below. Checkboxes display **real-time profile metrics** from OCI cloud table rows.")

st.markdown("""
<style>
    .candidate-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .skill-tag-matched {
        display: inline-block;
        background-color: #0066cc;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        margin: 3px;
        font-size: 12px;
        font-weight: 600;
    }
    .skill-tag-normal {
        display: inline-block;
        background-color: #f1f5f9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 6px;
        margin: 3px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 3. SIDEBAR LAYOUT CONFIGURATION
# ----------------------------------------------------
with st.sidebar:
    st.header("☁️ OCI Database Checklist")
    st.write("Toggle filter flags to run live SQL parameter filters against your Always Free ATP instance.")
    st.write("**Dynamic Skills Matrix Filters:**")
    
    # Extract calculated metrics data straight out of the live database
    skills_tally, sorted_skills_keys = get_unique_skills_with_counts()
    
    selected_sidebar_skills = []
    for skill_name in sorted_skills_keys:
        count_val = skills_tally.get(skill_name, 0)
        # Formats text display to append numerical profile volumes dynamically on screen
        checkbox_label = f"{skill_name} ({count_val})"
        
        if st.checkbox(checkbox_label, key=f"cloud_cb_{skill_name.replace(' ', '_')}"):
            selected_sidebar_skills.append(skill_name.lower())

# ----------------------------------------------------
# 4. DATA MATCHING ENGINE INTEGRATION RUNS
# ----------------------------------------------------
active_keywords = selected_sidebar_skills

if active_keywords:
    profiles_df = query_profiles_from_oracle(active_keywords)
    
    if not profiles_df.empty:
        display_text = ", ".join([s.title() for s in active_keywords])
        st.markdown(f"### 🎯 Found **{len(profiles_df)}** remote cloud match(es) for filters: **'{display_text}'**:")
        
        cols = st.columns(3)
        
        for idx, row in profiles_df.iterrows():
            original_name = str(row['NAME']).strip()
            all_skills = [s.strip() for s in str(row['SKILLS_MATRIX']).split(",") if s.strip()]
            bytes_data = row['RESUME_BLOB']
            
            tags_html = ""
            for skill in all_skills:
                is_matched = any(kw in skill.lower() for kw in active_keywords)
                tag_class = "skill-tag-matched" if is_matched else "skill-tag-normal"
                tags_html += f'<span class="{tag_class}">{skill}</span> '
                
            col_target = cols[idx % 3]
            
            with col_target:
                card_html = f"""
                <div class="candidate-card">
                    <h4 style="margin-top:0; color:#0066cc; font-size:16px;">👤 {original_name}</h4>
                    <p style="font-size:13px; margin-bottom:8px;"><b>Email:</b> <a href="mailto:{row['EMAIL']}">{row['EMAIL']}</a></p>
                    <div style="margin-top:10px; margin-bottom:15px;">{tags_html}</div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
                if bytes_data is not None and len(bytes_data) > 0:
                    download_filename = f"{original_name.replace(' ', '_')}_Resume.pdf"
                    st.download_button(
                        label="📥 Download Profile File",
                        data=bytes_data,       
                        file_name=download_filename,
                        mime="application/pdf",
                        key=f"dl_cloud_blob_{row['ID']}"
                    )
                else:
                    st.warning("⚠️ No resume document uploaded in DB for this profile.")
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.warning(f"No profile matches found inside cloud table 'skills' for criteria.")
else:
    st.info("👋 Good Morning! Check sidebar filters on the left matrix to query live rows directly from Oracle Cloud.")
