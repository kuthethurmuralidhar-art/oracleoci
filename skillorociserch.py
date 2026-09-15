import streamlit as st
import pandas as pd
import oracledb
import os
import io
import zipfile
from collections import Counter

WALLET_DIR = os.path.join(os.getcwd(), "wallet_files")

def get_db_connection():
    params = {
        "user": "ADMIN",
        "password": st.secrets["db_password"],
        "dsn": "search_low",
        "config_dir": WALLET_DIR,
        "wallet_location": WALLET_DIR,
        "wallet_password": st.secrets["wallet_password"],
        "ssl_server_dn_match": False
    }
    def blob_handler(cursor, name, default_type, size, precision, scale):
        if default_type == oracledb.DB_TYPE_BLOB:
            return cursor.var(bytes, arraysize=cursor.arraysize)
    conn = oracledb.connect(**params)
    conn.outputtypehandler = blob_handler
    return conn

def get_categorized_skills_with_counts():
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT skills_matrix FROM skills", conn)
        conn.close()
        if df.empty: return {}, {}, 0
        df.columns = [c.upper() for c in df.columns]
        
        all_skills = []
        norm_map = {"plsql": "PL/SQL", "pl/sql": "PL/SQL", "oracle dba": "Oracle DBA", "oci": "OCI"}
        for rm in df['SKILLS_MATRIX'].astype(str).dropna():
            sp = rm.split("Skills:")[-1] if "Skills:" in rm else rm
            for item in sp.split(","):
                cl = item.strip().lower()
                if cl: all_skills.append(norm_map.get(cl, item.strip().title()))
        
        tally = Counter(all_skills)
        cats = {
            "🔒 Cloud Platforms": ["OCI", "AWS", "Azure", "Cloud Security"],
            "🗄️ Database Systems": ["Oracle DBA", "Oracle Designer", "PostgreSQL", "Database Modelling", "PL/SQL", "SQL"],
            "💻 Programming Languages": ["Python Basics", "Java", "Cobol", "Flask", "Django"],
            "💿 Operating Systems": ["Linux", "Dos", "Mac", "Unix"],
            "⚙️ Middleware & Tools": ["Websphere", "Git", "Docker", "Kubernetes", "Streamlit"]
        }
        output = {c: [] for c in cats.keys()}
        output["🧩 Other Miscellaneous Skills"] = []
        for s in tally.keys():
            m = False
            for c_name, kws in cats.items():
                if any(k.lower() in s.lower() for k in kws):
                    output[c_name].append(s); m = True; break
            if not m: output["🧩 Other Miscellaneous Skills"].append(s)
        return tally, output, len(df)
    except:
        return {}, {}, 0

def query_all_profiles_from_oracle():
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT id, name, email, experience_years, skills_matrix, resume_blob FROM skills", conn)
        conn.close()
        df.columns = [c.upper() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def build_zip_archive(candidates):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for c in candidates:
            if c["BLOB"] is not None and len(c["BLOB"]) > 0:
                zf.writestr(f"{c['NAME'].replace(' ', '_')}_Resume.pdf", c["BLOB"])
    buf.seek(0)
    return buf.getvalue()

st.set_page_config(page_title="Talent Search", layout="wide")

st.markdown("""
<style>
    [data-testid="stVerticalBlock"] { gap: 0.4rem !important; padding-top: 0.2rem !important; padding-bottom: 0.2rem !important; }
    .stCheckbox { margin-top: 2px !important; margin-bottom: 2px !important; }
    div.row-widget.stRadio > div { gap: 0.5rem !important; }
    hr { margin-top: 4px !important; margin-bottom: 4px !important; border-top: 1px solid #ddd !important; }
    .element-container { margin-bottom: 0rem !important; }
</style>
""", unsafe_allow_html=True)

st.title("☁️ Talent Search Workspace")
st.write("High-volume tabular matching workstation powered by Oracle Cloud Infrastructure.")
st.markdown("<hr>", unsafe_allow_html=True)

raw_tally, categorized_skills, total_candidates = get_categorized_skills_with_counts()

st.subheader("🤖 AI-Powered Central Search Engine")
nlp_input = st.text_input("Type your query statement natively below:", placeholder="e.g., Find an Oracle DBA expert with OCI experience").strip()

selected_sidebar_skills = []
with st.sidebar:
    st.header("🎯 Search Parameters")
    if st.button("🧹 Clear All Filter Selections", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
    selected_tier = st.radio("Select Target Bracket:", options=["All Profiles (Ignore Exp Limit)", "< 3 Yrs (Entry Level)", "4-10 Yrs (Mid-Senior)", "> 10 Yrs (Principal)"])
    st.markdown("<hr>", unsafe_allow_html=True)
    st.write("**🛠️ Technology Competency Categories:**")
    for cat_title, s_list in categorized_skills.items():
        if s_list:
            with st.expander(cat_title, expanded=False):
                for s_name in sorted(s_list):
                    cnt = raw_tally.get(s_name, 0)
                    if st.checkbox(f"{s_name} ({cnt})", key=f"s_cb_{s_name.replace(' ', '_')}"):
                        selected_sidebar_skills.append(s_name.lower())

stopwords = {"find", "me", "a", "an", "developer", "engineer", "expert", "with", "experience", "skills", "show", "in", "for", "specialist"}
nlp_tokens = [w.lower() for w in nlp_input.replace(",", " ").split() if w.lower() not in stopwords]
active_keywords = list(set(selected_sidebar_skills + nlp_tokens))

if len(active_keywords) > 0:
    raw_df = query_all_profiles_from_oracle()
    if not raw_df.empty:
        matched_candidates = []
        for idx, row in raw_df.iterrows():
            raw_str = str(row['SKILLS_MATRIX']).strip()
            cand_exp = float(row['EXPERIENCE_YEARS'])
            
            has_match = False
            for kw in active_keywords:
                if kw == "pl/sql" and "plsql" in raw_str.lower(): has_match = True
                elif kw == "oci" and "oracle cloud infrastructure" in raw_str.lower(): has_match = True
                elif kw in raw_str.lower(): has_match = True
            if not has_match: continue
                
            if cand_exp < 3.0: tier_label = "< 3 Yrs"
            elif 4.0 <= cand_exp <= 10.0: tier_label = "4-10 Yrs"
            else: tier_label = "> 10 Yrs"
                
            if selected_tier == "< 3 Yrs (Entry Level)" and tier_label != "< 3 Yrs": continue
            elif selected_tier == "4-10 Yrs (Mid-Senior)" and tier_label != "4-10 Yrs": continue
            elif selected_tier == "> 10 Yrs (Principal)" and tier_label != "> 10 Yrs": continue
                
            if selected_tier == "All Profiles (Ignore Exp Limit)": exp_wt = 100
            elif selected_tier == "< 3 Yrs (Entry Level)": exp_wt = int((cand_exp / 3.0) * 100)
            elif selected_tier == "4-10 Yrs (Mid-Senior)": exp_wt = int((cand_exp / 10.0) * 100)
            elif selected_tier == "> 10 Yrs (Principal)": exp_wt = min(int((cand_exp / 12.0) * 100), 100)
                
            disp_skills = raw_str.split("Skills:")[-1].strip() if "Skills:" in raw_str else raw_str
            hl_list = []
            for tag in disp_skills.split(","):
                st_tag = tag.strip()
                mf = any(kw in st_tag.lower() or (kw == "pl/sql" and "plsql" in st_tag.lower()) or (kw == "oci" and "oracle cloud infrastructure" in st_tag.lower()) for kw in active_keywords)
                hl_list.append(f"**:red[{st_tag}]**" if mf else st_tag)
                
            matched_candidates.append({
                "ID": row['ID'], "NAME": str(row['NAME']).strip(), "EXP": cand_exp,
                "TIER": tier_label, "WEIGHT": f"{exp_wt}%", "SKILLS_DISP": ", ".join(hl_list), "BLOB": row['RESUME_BLOB']
            })
            
        if matched_candidates:
            st.markdown(f"### 🎯 Matched Candidates ({len(matched_candidates)} Profiles Found)")
            h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1.0, 2.5, 1.5, 1.5, 4.5])
            with h_col1: st.write("**Download**")
            with h_col2: st.write("**Candidate Name**")
            with h_col3: st.write("**Experience**")
            with h_col4: st.write("**Exp Weight**")
            with h_col5: st.write("**Technologies Found**")
            st.markdown("<hr style='margin:4px 0; border:0; border-top:2px solid #333;'>", unsafe_allow_html=True)
            
            selected_downloads = []
            for c_idx, candidate in enumerate(matched_candidates):
                r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([1.0, 2.5, 1.5, 1.5, 4.5])
                with r_col1:
                    if st.checkbox("", key=f"dl_check_{candidate['ID']}_{c_idx}"):
                        selected_downloads.append(candidate)
                with r_col2: st.markdown(f"👤 **{candidate['NAME']}**")
                with r_col3: st.write(f"{candidate['EXP']} Yrs ({candidate['TIER']})")
                with r_col4: st.write(f"🎯 **{candidate['WEIGHT']}**")
                with r_col5: st.markdown(candidate['SKILLS_DISP'])
                st.markdown("<hr style='margin:4px 0; border:0; border-top:1px dashed #ccc;'>", unsafe_allow_html=True)
                
            if selected_downloads:
                st.markdown("<br>", unsafe_allow_html=True)
                zip_data_bytes = build_zip_archive(selected_downloads)
                st.download_button(
                    label=f"📥 Bulk Download Selected Resumes ({len(selected_downloads)} Files Bundle)",
                    data=zip_data_bytes, file_name="OCI_Talent_Search_Resumes.zip", mime="application/zip", use_container_width=True, type="primary"
                )
        else:
            st.warning("⚠️ No profiles matching criteria found inside this tier bracket.")
    else:
        st.warning("No candidate records matched your search parameters.")
else:
    st.info("👋 Good Morning! Please type a query statement above or expand a technology category on the left sidebar to begin.")
