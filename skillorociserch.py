import streamlit as st
import pandas as pd
import oracledb
import os
from collections import Counter

# 1. ORACLE CLOUD ENGINE CONFIGURATION (THIN MODE)
WALLET_DIR = os.path.join(os.getcwd(), "wallet_files")

def get_db_connection():
    connection_params = {
        "user": "ADMIN",
        "password": st.secrets["db_password"],
        "dsn": "search_low",
        "config_dir": WALLET_DIR,
        "wallet_location": WALLET_DIR,
        "wallet_password": st.secrets["wallet_password"],
        "ssl_server_dn_match": False
    }
    def blob_to_bytes_handler(cursor, name, default_type, size, precision, scale):
        if default_type == oracledb.DB_TYPE_BLOB:
            return cursor.var(bytes, arraysize=cursor.arraysize)
    conn = oracledb.connect(**connection_params)
    conn.outputtypehandler = blob_to_bytes_handler
    return conn

# Pulls OCI rows and extracts normalized distinct skills along with frequency counters
def get_unique_skills_with_counts():
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT skills_matrix FROM skills", conn)
        conn.close()
        if df.empty:
            return {}, [], 0
        target_column = 'SKILLS_MATRIX' if 'SKILLS_MATRIX' in df.columns else 'skills_matrix'
        all_skills_list = []
        
        normalization_map = {
            "plsql": "PL/SQL", "pl/sql": "PL/SQL",
            "oracle dba": "Oracle DBA", "oracledba": "Oracle DBA",
            "oci": "OCI", "oracle cloud infrastructure": "OCI",
            "oracle cloud infrastructure (oci)": "OCI",
            "python basics": "Python Basics", "python": "Python Basics",
            "oracle designer": "Oracle Designer"
        }
        
        for raw_matrix in df[target_column].astype(str).dropna():
            skills_part = raw_matrix.split("Skills:")[-1] if "Skills:" in raw_matrix else raw_matrix
            for item in skills_part.split(","):
                cleaned_item = item.strip().lower()
                if cleaned_item:
                    normalized_item = normalization_map.get(cleaned_item, item.strip().title())
                    all_skills_list.append(normalized_item)
                    
        tally_dict = Counter(all_skills_list)
        return tally_dict, sorted(tally_dict.keys()), len(df)
    except:
        fallback = ["Oracle DBA", "OCI", "PL/SQL"]
        return {k: 1 for k in fallback}, fallback, 0

def query_profiles_from_oracle(search_keywords=None):
    try:
        conn = get_db_connection()
        where_clauses = []
        bind_params = {}
        for i, kw in enumerate(search_keywords):
            param_name = f"skill_{i}"
            if kw.lower() == "pl/sql":
                where_clauses.append(f"(LOWER(skills_matrix) LIKE :skill_pl1 OR LOWER(skills_matrix) LIKE :skill_pl2)")
                bind_params["skill_pl1"] = "%pl/sql%"
                bind_params["skill_pl2"] = "%plsql%"
            elif kw.lower() == "oci":
                where_clauses.append(f"(LOWER(skills_matrix) LIKE :skill_oci1 OR LOWER(skills_matrix) LIKE :skill_oci2 OR LOWER(skills_matrix) LIKE :skill_oci3)")
                bind_params["skill_oci1"] = "%oci%"
                bind_params["skill_oci2"] = "%oracle cloud infrastructure%"
                bind_params["skill_oci3"] = "%oracle cloud infrastructure (oci)%"
            else:
                where_clauses.append(f"LOWER(skills_matrix) LIKE :{param_name}")
                bind_params[param_name] = f"%{kw.lower()}%"
                
        query = "SELECT id, name, email, skills_matrix, resume_blob FROM skills WHERE " + " OR ".join(where_clauses)
        df = pd.read_sql(query, conn, params=bind_params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Oracle Cloud Database Connection Failure: {e}")
        return pd.DataFrame(columns=["ID", "NAME", "EMAIL", "SKILLS_MATRIX", "RESUME_BLOB"])

# 2. RUNTIME UI LAYOUT & SIDEBAR FILTER ENGINE
st.set_page_config(page_title="Talent Search", layout="wide")
st.title("☁️ Talent Search")
st.write("Powered by OCI Autonomous Database.")
st.markdown("<hr>", unsafe_allow_html=True)

skills_tally, sorted_skills_keys, total_candidates = get_unique_skills_with_counts()

with st.sidebar:
    st.header("🎯 Search Parameters")
    st.write("**💼 Experience Filter:**")
    selected_tier = st.radio("Select Target Bracket:", options=["All Profiles (Ignore Exp Limit)", "< 3 Yrs (Entry Level)", "4-10 Yrs (Mid-Senior)", "> 10 Yrs (Principal)"])
    st.markdown("<hr>", unsafe_allow_html=True)
    st.write("**🛠️ Core Competency Matrix Checklist:**")
    
    selected_sidebar_skills = []
    for skill_name in sorted_skills_keys:
        count_val = skills_tally.get(skill_name, 0)
        if st.checkbox(f"{skill_name} ({count_val})", key=f"rec_cb_{skill_name.replace(' ', '_')}"):
            selected_sidebar_skills.append(skill_name.lower())

# 3. STRICT RUNTIME GATEKEEPER FOR LOADING DATA
active_keywords = selected_sidebar_skills

# 🔒 THE BULLETPROOF GATE: The application will only run if active_keywords list is NOT empty!
if len(active_keywords) > 0:
    profiles_df = query_profiles_from_oracle(active_keywords)
    
    if not profiles_df.empty:
        cols = st.columns(3)
        card_index = 0
        
        for idx, row in profiles_df.iterrows():
            original_name = str(row['NAME']).strip()
            raw_matrix_str = str(row['SKILLS_MATRIX']).strip()
            bytes_data = row['RESUME_BLOB']
            
            candidate_exp = 0.0
            skills_part = raw_matrix_str
            if "Yrs Experience | Skills:" in raw_matrix_str:
                parts = raw_matrix_str.split(" Yrs Experience | Skills:")
                candidate_exp = float(parts[0])
                skills_part = parts[1]
                
            if candidate_exp < 3.0:
                tier_label = "< 3 Yrs"
            elif 4.0 <= candidate_exp <= 10.0:
                tier_label = "4-10 Yrs"
            else:
                tier_label = "> 10 Yrs"
                
            # Filter checks are active ONLY if a specific tiered bracket is chosen
            if selected_tier == "< 3 Yrs (Entry Level)" and tier_label != "< 3 Yrs":
                continue
            elif selected_tier == "4-10 Yrs (Mid-Senior)" and tier_label != "4-10 Yrs":
                continue
            elif selected_tier == "> 10 Yrs (Principal)" and tier_label != "> 10 Yrs":
                continue
                
            if selected_tier == "All Profiles (Ignore Exp Limit)":
                exp_weight_percentage = 100
            elif selected_tier == "< 3 Yrs (Entry Level)":
                exp_weight_percentage = int((candidate_exp / 3.0) * 100)
            elif selected_tier == "4-10 Yrs (Mid-Senior)":
                exp_weight_percentage = int((candidate_exp / 10.0) * 100)
            elif selected_tier == "> 10 Yrs (Principal)":
                exp_weight_percentage = min(int((candidate_exp / 12.0) * 100), 100)
                
            col_target = cols[card_index % 3]
            with col_target:
                st.info(f"👤 {original_name} [🎯 Exp Weight: {exp_weight_percentage}%]")
                st.write(f"💼 **Experience Metrics:** {candidate_exp} Years ({tier_label})")
                st.write(f"📧 **Email Coordinates:** {row['EMAIL']}")
                st.write(f"🛠️ **Skills Index:** {skills_part}")
                if bytes_data is not None and len(bytes_data) > 0:
                    st.download_button(label="📥 Download Profile PDF", data=bytes_data, file_name=f"{original_name.replace(' ', '_')}_Resume.pdf", mime="application/pdf", key=f"dl_cloud_seeker_{row['ID']}")
                st.markdown("<br>", unsafe_allow_html=True)
            card_index += 1
            
        if card_index == 0:
            st.warning("⚠️ No profiles matching your selected criteria were found inside this experience tier bracket.")
    else:
        st.warning("No candidate records matched your search parameters inside your OCI tables.")
else:
    # Safe landing page that keeps the app extremely light on startup
    st.info("👋 Good Afternoon! To scan candidate records cleanly without logging latency, please select at least one Core Competency Checkbox flag on the left sidebar filter matrix.")
