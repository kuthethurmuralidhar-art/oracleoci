import streamlit as st, pandas as pd, oracledb, os, io, zipfile
from collections import Counter

W_DIR = os.path.join(os.getcwd(), "wallet_files")

def get_db_connection():
    p = {
        "user": "ADMIN", "password": st.secrets["db_password"], "dsn": "search_low",
        "config_dir": W_DIR, "wallet_location": W_DIR, "wallet_password": st.secrets["wallet_password"],
        "ssl_server_dn_match": False
    }
    def bh(cursor, name, dtype, size, prec, scale):
        if dtype == oracledb.DB_TYPE_BLOB: return cursor.var(bytes, arraysize=cursor.arraysize)
    conn = oracledb.connect(**p)
    conn.outputtypehandler = bh
    return conn

def get_master_taxonomy():
    return {
        "Delivery Manager": {
            "☁️ Cloud Architecture": ["OCI", "AWS", "Azure", "Cloud Security"],
            "📐 Solution Blueprinting": ["Database Modelling", "Oracle Designer"],
            "🤖 Executive AI Automation": ["AI Skills"]
        },
        "🗄️ Database Administrator (DBA)": {
            "💎 Core Oracle Engine": ["Oracle DBA", "PL/SQL", "SQL"],
            "💾 Open-Source Data RDBMS": ["PostgreSQL"]
        },
        "💻 Application Developer": {
            "🐍 Python Ecosystem": ["Python", "Flask", "Django", "Streamlit"],
            "☕ Java Core Enterprise": ["Java"],
            "🤖 Cognitive Core Frameworks": ["AI Skills"]
        },
        "🖥️ System Administrator": {
            "💿 Unix & Open Server OS": ["Linux", "Unix"],
            "⚙️ Legacy Server Environments": ["Websphere", "Dos", "Mac"]
        },
        "🛠️ ITIL & Infrastructure Engineer": {
            "📦 DevOps Containerization": ["Docker", "Kubernetes", "Git"],
            "🧱 Legacy Infrastructure Core": ["Cobol"]
        }
    }

def get_categorized_skills_with_counts():
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT skills_matrix FROM skills", conn)
        conn.close()
        if df.empty: return {}, {}, 0
        df.columns = [c.upper() for c in df.columns]
        
        all_s = []
        n_map = {
            "plsql": "PL/SQL", "pl/sql": "PL/SQL", "oracle dba": "Oracle DBA", "oci": "OCI",
            "python basics": "Python", "python": "Python", "ai skills": "AI Skills", 
            "ai": "AI Skills", "machine learning": "AI Skills"
        }
        for rm in df['SKILLS_MATRIX'].astype(str).dropna():
            sp = rm.split("Skills:")[-1] if "Skills:" in rm else rm
            for it in sp.split(","):
                cl = it.strip().lower()
                if cl: all_s.append(n_map.get(cl, it.strip().title()))
        
        tally = Counter(all_s)
        cats = get_master_taxonomy()
        tree = {r: {t: [] for t in td.keys()} for r, td in cats.items()}
        for fs in sorted(tally.keys()):
            for r, td in cats.items():
                for t, kws in td.items():
                    if any(k.lower() in fs.lower() for k in kws): tree[r][t].append(fs)
        return tally, tree, len(df)
    except: return {}, {}, 0

def query_all_profiles_from_oracle():
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT id, name, email, experience_years, skills_matrix, resume_blob FROM skills", conn)
        conn.close()
        df.columns = [c.upper() for c in df.columns]
        return df
    except: return pd.DataFrame()

def build_zip_archive(candidates):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for c in candidates:
            if c["BLOB"] is not None and len(c["BLOB"]) > 0:
                zf.writestr(f"{c['NAME'].replace(' ', '_')}_Resume.pdf", c["BLOB"])
    buf.seek(0)
    return buf.getvalue()

st.set_page_config(page_title="Talent Search", layout="wide")
st.title("☁️ Talent Search Workspace")
st.write("Function-driven tabular workstation powered by Oracle Cloud Infrastructure.")
st.markdown("<hr>", unsafe_allow_html=True)

raw_tally, structured_tree, total_candidates = get_categorized_skills_with_counts()
nlp_input = st.text_input("Type your query statement natively below:", placeholder="e.g., Find an Oracle DBA expert with OCI experience").strip()

selected_sidebar_skills = []
with st.sidebar:
    st.header("🎯 Parameters")
    if st.button("🧹 Clear All Filters", use_container_width=True):
        st.cache_data.clear()
        for k in list(st.session_state.keys()):
            if k.startswith("s_cb_") or k.startswith("chk_"): st.session_state[k] = False
        st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
    s_tier = st.radio("Select Target Bracket:", options=["All Profiles (Ignore Exp Limit)", "< 3 Yrs (Entry Level)", "4-10 Yrs (Mid-Senior)", "> 10 Yrs (Principal)"])
    st.markdown("<hr>", unsafe_allow_html=True)
    for r_title, tech_dict in structured_tree.items():
        if any(len(lst) > 0 for lst in tech_dict.values()):
            with st.expander(r_title, expanded=False):
                for t_title, s_list in tech_dict.items():
                    if s_list:
                        st.markdown(f"**`{t_title}`**")
                        for s_name in s_list:
                            cnt = raw_tally.get(s_name, 0)
                            cb_key = f"s_cb_{r_title}_{t_title}_{s_name}".replace(' ', '_').replace('💻', '').replace('🤖', '').replace('🐍', '').replace('☕', '').replace('💿', '').replace('⚙️', '').replace('📦', '').replace('🧱', '').replace('🗄️', '').replace('💎', '').replace('💾', '').replace('👔', '').replace('☁️', '').replace('📐', '')
                            if st.checkbox(f"{s_name} ({cnt})", key=cb_key): selected_sidebar_skills.append(s_name.lower())

stopwords = {"find", "me", "a", "an", "developer", "engineer", "expert", "with", "experience", "skills", "show", "in", "for", "specialist"}
nlp_tokens = [w.lower() for w in nlp_input.replace(",", " ").split() if w.lower() not in stopwords]
active_keywords = list(set(selected_sidebar_skills + nlp_tokens))

if len(active_keywords) > 0:
    raw_df = query_all_profiles_from_oracle()
    if not raw_df.empty:
        matched_candidates = []
        for idx, row in raw_df.iterrows():
            raw_str = str(row['SKILLS_MATRIX']).strip()
            c_exp = float(row['EXPERIENCE_YEARS'])
            
            hm = any(kw in raw_str.lower() or (kw == "pl/sql" and "plsql" in raw_str.lower()) or (kw == "oci" and "oracle cloud infrastructure" in raw_str.lower()) or (kw == "python" and "python basics" in raw_str.lower()) or (kw == "ai skills" and "machine learning" in raw_str.lower()) for kw in active_keywords)
            if not hm: continue
                
            if c_exp < 3.0: tl = "< 3 Yrs"
            elif 4.0 <= c_exp <= 10.0: tl = "4-10 Yrs"
            else: tl = "> 10 Yrs"
                
            if s_tier == "< 3 Yrs (Entry Level)" and tl != "< 3 Yrs": continue
            elif s_tier == "4-10 Yrs (Mid-Senior)" and tl != "4-10 Yrs": continue
            elif s_tier == "> 10 Yrs (Principal)" and tl != "> 10 Yrs": continue
                
            if s_tier == "All Profiles (Ignore Exp Limit)": exp_wt = 100
            elif s_tier == "< 3 Yrs (Entry Level)": exp_wt = int((c_exp / 3.0) * 100)
            elif s_tier == "4-10 Yrs (Mid-Senior)": exp_wt = int((c_exp / 10.0) * 100)
            elif s_tier == "> 10 Yrs (Principal)": exp_wt = min(int((c_exp / 12.0) * 100), 100)
                
            disp_skills = raw_str.split("Skills:")[-1].strip() if "Skills:" in raw_str else raw_str
            hl_list = []
            for tag in disp_skills.split(","):
                st_tag = tag.strip()
                mf = any(kw in st_tag.lower() or (kw == "pl/sql" and "plsql" in st_tag.lower()) or (kw == "oci" and "oracle cloud infrastructure" in st_tag.lower()) or (kw == "python" and "python basics" in st_tag.lower()) or (kw == "ai skills" and "machine learning" in st_tag.lower()) for kw in active_keywords)
                hl_list.append(f"**:red[{st_tag}]**" if mf else st_tag)
                
            matched_candidates.append({
                "ID": str(row['ID']).strip(), "NAME": str(row['NAME']).strip(), "EXP": c_exp,
                "TIER": tl, "WEIGHT": f"{exp_wt}%", "SKILLS_DISP": ", ".join(hl_list), "BLOB": row['RESUME_BLOB']
            })
            
        if matched_candidates:
            st.markdown(f"### 🎯 Matched Candidates ({len(matched_candidates)} Profiles)")
            c1, c2, c3, c4, c5 = st.columns([1.0, 2.5, 1.5, 1.5, 4.5])
            with c1: st.write("**Download**")
            with c2: st.write("**Candidate Name**")
            with c3: st.write("**Experience**")
            with c4: st.write("**Exp Weight**")
            with c5: st.write("**Technologies Found**")
            st.markdown("<hr style='margin:2px 0; border-top:2px solid #333;'>", unsafe_allow_html=True)
            
            for c_idx, candidate in enumerate(matched_candidates):
                r1, r2, r3, r4, r5 = st.columns([1.0, 2.5, 1.5, 1.5, 4.5])
                with r1: st.checkbox("", key=f"chk_{candidate['ID']}")
                with r2: st.markdown(f"👤 **{candidate['NAME']}**")
                with r3: st.write(f"{candidate['EXP']} Yrs ({candidate['TIER']})")
                with r4: st.write(f"🎯 **{candidate['WEIGHT']}**")
                with r5: st.markdown(candidate['SKILLS_DISP'])
                st.markdown("<hr style='margin:2px 0; border-top:1px dashed #ccc;'>", unsafe_allow_html=True)
                
            active_selections = [c for c in matched_candidates if st.session_state.get(f"chk_{c['ID']}", False)]
            if active_selections:
                st.markdown("<br>", unsafe_allow_html=True)
                zb = build_zip_archive(active_selections)
                st.download_button("📥 Download Bundle", zb, "Resumes.zip", "application/zip", use_container_width=True)
        else: st.warning("⚠️ No profiles matching criteria found inside this tier bracket.")
    else: st.warning("No candidate records matched your search parameters.")
