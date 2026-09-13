import streamlit as st
import pandas as pd
import oracledb
import os

# ----------------------------------------------------
# 1. ORACLE CLOUD ENGINE CONFIGURATION (THIN MODE)
# ----------------------------------------------------
# On Streamlit Cloud, the wallet folder will sit right next to the script
WALLET_DIR = os.path.join(os.getcwd(), "wallet_files")

def get_db_connection():
    connection_params = {
        "user": "ADMIN",
        "password": st.secrets["db_password"],      # 🔒 Secured via Streamlit Vault
        "dsn": "search_low",                       
        "config_dir": WALLET_DIR,                  
        "wallet_location": WALLET_DIR,             
        "wallet_password": st.secrets["wallet_password"],  # 🔒 Secured via Streamlit Vault
        "ssl_server_dn_match": False               
    }
    
    def blob_to_bytes_handler(cursor, name, default_type, size, precision, scale):
        if default_type == oracledb.DB_TYPE_BLOB:
            return cursor.var(bytes, arraysize=cursor.arraysize)
            
    conn = oracledb.connect(**connection_params)
    conn.outputtypehandler = blob_to_bytes_handler
    return conn

# Pulls unique expertise items dynamically from live cloud database rows
def get_unique_skills_from_oracle():
    try:
        conn = get_db_connection()
        query = "SELECT skills_matrix FROM skills"
        df = pd.read_sql(query, conn)
        conn.close()
        
        if df.empty:
            return ["Oracle DBA", "OCI", "Oracle Designer", "Python Basics", "Streamlit"]
            
        target_column = 'SKILLS_MATRIX' if 'SKILLS_MATRIX' in df.columns else 'skills_matrix'
        
        skills_series = df[target_column].astype(str).dropna()
        skills_lists = skills_series.str.split(',')
        exploded_skills = skills_lists.explode()
        cleaned_skills = exploded_skills.str.strip()
        
        unique_series = cleaned_skills.drop_duplicates()
        unique_series = unique_series[unique_series != '']
        unique_series = unique_series[unique_series.str.lower() != 'error']
        
        return sorted(unique_series.tolist())
    except Exception as e:
        return ["Oracle DBA", "OCI", "Oracle Designer", "Python Basics", "Streamlit", "AWS", "Cloud Security", "Linux", "PL/SQL", "Git"]

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
st.set_page_config(page_title="Oracle Cloud Portal", page_icon="☁️", layout="wide")
st.title("☁️ Profile Matcher Portal")
st.write("Select expertise checklist flags below. Checkboxes are **dynamically populated** from live OCI cloud database rows.")

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
    
    available_skills = get_unique_skills_from_oracle()
    
    selected_sidebar_skills = []
    for skill in available_skills:
        if st.checkbox(skill, key=f"cloud_cb_{skill.replace(' ', '_')}"):
            selected_sidebar_skills.append(skill.lower())

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
    st.info("👋 Good Evening! Check sidebar filters on the left matrix to query live rows directly from Oracle Cloud.")
