import streamlit as st
import pandas as pd
import oracledb
import os

# ----------------------------------------------------
# 1. ORACLE CLOUD ENGINE CONFIGURATION (THIN MODE)
# ----------------------------------------------------
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

def get_clean_skills_list():
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT skills_matrix FROM skills", conn)
        conn.close()
        if df.empty:
            return ["Oracle DBA", "OCI", "Python Basics"]
        
        target_column = 'SKILLS_MATRIX' if 'SKILLS_MATRIX' in df.columns else 'skills_matrix'
        unique_skills = set()
        for raw_matrix in df[target_column].astype(str).dropna():
            if "Skills:" in raw_matrix:
                # Extract out just the skills part after our split marker pipe token
                skills_part = raw_matrix.split("Skills:")[-1]
                for item in skills_part.split(","):
                    cleaned_item = item.strip()
                    if cleaned_item:
                        unique_skills.add(cleaned_item)
            else:
                # Fallback check to parse rows loaded under legacy structures
                for item in raw_matrix.split(","):
                    cleaned_item = item.split(":")[0].strip() if ":" in item else item.strip()
                    if cleaned_item and "yrs experience" not in cleaned_item.lower():
                        unique_skills.add(cleaned_item)
        return sorted(list(unique_skills))
    except:
        return ["Oracle DBA", "OCI", "PL/SQL", "Python Basics", "Streamlit"]

def query_profiles_from_oracle(search_keywords=None, min_exp=0.0):
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
            conn.close()
            return pd.DataFrame(columns=["ID", "NAME", "EMAIL", "SKILLS_MATRIX", "RESUME_BLOB"])
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Oracle Cloud Database Connection Failure: {e}")
        return pd.DataFrame(columns=["ID", "NAME", "EMAIL", "SKILLS_MATRIX", "RESUME_BLOB"])

# ----------------------------------------------------
# 2. RUNTIME UI LAYOUT & PREMIUM STYLING
# ----------------------------------------------------
st.set_page_config(page_title="OCI Enterprise Seeker", layout="wide")

st.markdown("""
<style>
    .candidate-card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .exp-badge-premium { background-color: #eff6ff; color: #1e40af; padding: 4px 12px; border-radius: 8px; font-size: 13px; font-weight: 700; margin-bottom: 10px; display: inline-block; }
    .match-badge-high { background-color: #dcfce7; color: #166534; padding: 5px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; float: right; }
    .match-badge-low { background-color: #fee2e2; color: #991b1b; padding: 5px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; float: right; }
    .skill-tag-matched { display: inline-block; background-color: #2563eb; color: white; padding: 4px 12px; border-radius: 8px; margin: 3px; font-size: 12px; font-weight: 600; }
    .skill-tag-normal { display: inline-block; background-color: #f1f5f9; color: #475569; padding: 4px 12px; border-radius: 8px; margin: 3px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("☁️ OCI 23ai AI Balanced Experience Talent Matcher")
st.write("Extracts raw candidate inputs and benchmarks numerical values against real-time OCI cloud rows.")
st.markdown("<hr>", unsafe_allow_html=True)

# ----------------------------------------------------
# SIDEBAR CONTROL SLIDERS
# ----------------------------------------------------
with st.sidebar:
    st.header("🎯 Filter Panel Controls")
    
    available_skills = get_clean_skills_list()
    selected_sidebar_skills = []
    for s in available_skills:
        if st.checkbox(s, key=f"rec_cb_{s.replace(' ', '_')}"):
            selected_sidebar_skills.append(s.lower())
            
    st.markdown("<hr>", unsafe_allow_html=True)
    # Recruiter dials in their precise cutoff requirement threshold
    min_exp_required = st.slider("Minimum Target Experience (Years)", min_value=0.0, max_value=15.0, value=3.0, step=0.5)

# ----------------------------------------------------
# 3. ANALYSIS COMPILATION LOOPS
# ----------------------------------------------------
active_keywords = selected_sidebar_skills

if active_keywords:
    profiles_df = query_profiles_from_oracle(active_keywords)
    
    if not profiles_df.empty:
        st.markdown(f"### 🎯 Dynamic Qualification Matching Matrix:")
        cols = st.columns(3)
        
        for idx, row in profiles_df.iterrows():
            original_name = str(row['NAME']).strip()
            raw_matrix_str = str(row['SKILLS_MATRIX']).strip()
            bytes_data = row['RESUME_BLOB']
            
            # Extract experience and skills strings using regex/splits safely
            candidate_exp = 1.0
            skills_part = raw_matrix_str
            
            if "Yrs Experience | Skills:" in raw_matrix_str:
                parts = raw_matrix_str.split(" Yrs Experience | Skills:")
                candidate_exp = float(parts[0])
                skills_part = parts[1]
            
            # MATH MATCH ENGINE BLOCK
            keyword_match_count = sum(1 for kw in active_keywords if kw in skills_part.lower())
            keyword_score = keyword_match_count / len(active_keywords)
            
            exp_score = min(candidate_exp / min_exp_required, 1.0) if min_exp_required > 0 else 1.0
            
            # Balanced Score: 50% keyword presence, 50% experience year volume criteria matching
            final_weighted_percentage = int(((keyword_score * 0.5) + (exp_score * 0.5)) * 100)
            
            badge_class = "match-badge-high" if final_weighted_percentage >= 70 else "match-badge-low"
            
            tags_html = ""
            for item in skills_part.split(","):
                cleaned_item = item.strip()
                if cleaned_item:
                    is_matched = cleaned_item.lower() in active_keywords
                    tag_class = "skill-tag-matched" if is_matched else "skill-tag-normal"
                    tags_html += f'<span class="{tag_class}">{cleaned_item}</span> '
            
            col_target = cols[idx % 3]
            with col_target:
                card_html = f"""
                <div class="candidate-card">
                    <span class="{badge_class}">🎯 {final_weighted_percentage}% Match</span>
                    <h4 style="margin-top:0; color:#2563eb; font-size:17px; margin-bottom:2px;">👤 {original_name}</h4>
                    <div class="exp-badge-premium">💼 {candidate_exp} Yrs Experience</div>
                    <p style="font-size:13px; margin-bottom:12px; color:#475569;"><b>Email:</b> <a href="mailto:{row['EMAIL']}">{row['EMAIL']}</a></p>
                    <div style="margin-top:5px; margin-bottom:15px;">{tags_html}</div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
                if bytes_data is not None and len(bytes_data) > 0:
                    st.download_button(
                        label="📥 Download Profile PDF File",
                        data=bytes_data,       
                        file_name=f"{original_name.replace(' ', '_')}_Resume.pdf",
                        mime="application/pdf",
                        key=f"dl_cloud_seeker_{row['ID']}"
                    )
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.warning("No records satisfied your filter criteria tokens.")
else:
    st.info("👋 Select checkbox tags on the left sidebar pane and slide experience requirements to calculate metrics dynamically.")
