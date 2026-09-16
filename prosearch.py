import streamlit as st, pandas as pd, os
from collections import Counter
# ✅ THE DISCONNECTED IMPORT FIX: References the correct, active API handshake courier function!
from utils import get_db_connection, get_master_taxonomy, query_matched_profiles_via_stored_function, build_zip_archive, init_page_headers

init_page_headers()

def is_fuzzy_match(kw, target_str):
    return kw.lower().strip() in target_str.lower().strip()

def get_categorized_skills_with_counts():
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT skills_matrix, location FROM skills", conn)
        conn.close()
        if df.empty: return {}, {}, [], 0
        df.columns = [c.upper() for c in df.columns]
        all_s, all_locs = [], []
        n_map = {"plsql": "PL/SQL", "pl/sql": "PL/SQL", "oracle dba": "Oracle DBA", "oci": "OCI", "python basics": "Python", "python": "Python", "ai skills": "AI Skills", "ai": "AI Skills", "machine learning": "AI Skills"}
        for loc in df['LOCATION'].astype(str).dropna():
            l_cl = loc.strip().title()
            if l_cl and l_cl not in all_locs: all_locs.append(l_cl)
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
        return tally, tree, sorted(all_locs), len(df)
    except: return {}, {}, [], 0

if "reset_counter" not in st.session_state: st.session_state.reset_counter = 0

raw_tally, structured_tree, unique_locations, total_candidates = get_categorized_skills_with_counts()
autocomplete_options = sorted(list(raw_tally.keys()))
nlp_selection_tags = st.multiselect(
    "Select technical competency keywords from the unified index:", 
    options=autocomplete_options, placeholder="Start typing or click to select skills...", 
    key=f"main_search_index_{st.session_state.reset_counter}"
)

selected_sidebar_skills, selected_locations_filter = [], []
with st.sidebar:
    st.header("🎯 Parameters")
    if st.button("🧹 Clear All Filters", use_container_width=True):
        st.cache_data.clear()
        st.session_state.reset_counter += 1
        st.rerun()
    
    st.markdown("""
        <style>
            div[data-testid="stSidebar"] div.stRadio { margin-top: -15px !important; padding-top: 0px !important; }
            div[data-testid="stSidebar"] div.stRadio > label { margin-bottom: 2px !important; font-weight: bold !important; }
            div[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] { margin-bottom: 4px !important; }
        </style>
    """, unsafe_allow_html=True)
    
    s_tier = st.radio("Select Target Bracket:", options=["All Profiles (Ignore Exp Limit)", "< 3 Yrs (Entry Level)", "4-10 Yrs (Mid-Senior)", "> 10 Yrs (Principal)"])
    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
    
    st.write("**📍 Multi-Location Filter:**")
    selected_locations_filter = st.multiselect("Choose Target Cities:", options=unique_locations, placeholder="All Cities Active...", key=f"loc_ms_{st.session_state.reset_counter}")
    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
    
    st.write("**👔 Multi-Role Selection Panel:**")
    active_selected_roles = st.multiselect("Select Target Professional Roles:", options=list(structured_tree.keys()), placeholder="Click to pick target roles...", key=f"roles_ms_{st.session_state.reset_counter}")
    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
    
    st.write("**🛠️ Chained Competency Skills Index:**")
    chained_available_skills = []
    if active_selected_roles:
        for typed_role in active_selected_roles:
            matched_key = next((k for k in structured_tree.keys() if typed_role.lower() in k.lower() or k.lower() in typed_role.lower()), None)
            if matched_key:
                for s_list in structured_tree.get(matched_key, {}).values():
                    for s_name in s_list:
                        if s_name not in chained_available_skills: chained_available_skills.append(s_name)
    else:
        chained_available_skills = list(raw_tally.keys())
        
    active_selected_skills = st.multiselect("Select chained technologies:", options=sorted(chained_available_skills), placeholder="Pick target technologies...", key=f"chained_skills_ms_{st.session_state.reset_counter}")
    for tag in active_selected_skills: selected_sidebar_skills.append(tag.lower().strip())

nlp_tokens = [t.lower().strip() for t in nlp_selection_tags]
sidebar_tokens = [s.lower().strip() for s in selected_sidebar_skills]
active_keywords = list(set(nlp_tokens + sidebar_tokens))

if len(active_keywords) > 0 or len(selected_locations_filter) > 0:
    # ✅ REDIRECTED HOOK: Calls the active REST API pipeline route function instead of raw SQL!
    kw_arg = active_keywords[0] if active_keywords else None
    loc_arg = selected_locations_filter[0] if selected_locations_filter else None
    
    df_raw = query_matched_profiles_via_stored_function(keyword=kw_arg, location=loc_arg)
    
    if not df_raw.empty:
        matched_candidates = []
        raw_records = df_raw.to_dict(orient="records")
        
        for item in raw_records:
            raw_str = str(item.get('SKILLS_MATRIX', '')).strip()
            c_exp = float(item.get('EXPERIENCE_YEARS', 0.0))
            c_loc = str(item.get('LOCATION', 'General')).strip().title()
            
            if selected_locations_filter and c_loc not in selected_locations_filter: continue
            if active_keywords and not any(is_fuzzy_match(kw, raw_str) for kw in active_keywords): continue
            
            if c_exp < 3.0: tl, exp_wt = "< 3 Yrs", int((c_exp / 3.0) * 100)
            elif 4.0 <= c_exp <= 10.0: tl, exp_wt = "4-10 Yrs", int((c_exp / 10.0) * 100)
            else: tl, exp_wt = "> 10 Yrs", min(int((c_exp / 12.0) * 100), 100)
            if s_tier == "All Profiles (Ignore Exp Limit)": exp_wt = 100
            if s_tier == "< 3 Yrs (Entry Level)" and tl != "< 3 Yrs": continue
            if s_tier == "4-10 Yrs (Mid-Senior)" and tl != "4-10 Yrs": continue
            if s_tier == "> 10 Yrs (Principal)" and tl != "> 10 Yrs": continue
            
            disp_skills = raw_str.split("Skills:")[-1].strip() if "Skills:" in raw_str else raw_str
            hl_list = []
            for tag in disp_skills.split(","):
                st_tag = tag.strip()
                mf = active_keywords and any(is_fuzzy_match(kw, st_tag) for kw in active_keywords)
                hl_list.append(f"**:red[{st_tag}]**" if mf else st_tag)
                
            matched_candidates.append({
                "ID": str(item.get('ID', '')).strip(), "NAME": str(item.get('NAME', '')).strip(), "EXP": c_exp, "LOCATION": c_loc,
                "TIER": tl, "WEIGHT": f"{exp_wt}%", "SKILLS_DISP": ", ".join(hl_list), "BLOB": item.get('RESUME_BLOB', None)
            })
            
        if matched_candidates:
            st.markdown(f"### 🎯 Shortlisting Workspace Matrix ({len(matched_candidates)} Profiles Found)")
            dl_list = [c for c in matched_candidates if st.session_state.get(f"chk_{c['ID']}_{st.session_state.reset_counter}", False)]
            if dl_list:
                zb_bytes = build_zip_archive(dl_list)
                st.download_button(f"📥 Download Shortlisted ZIP Bundle ({len(dl_list)} Resumes)", zb_bytes, "Shortlisted_Resumes.zip", "application/zip", use_container_width=True, type="primary")
            else: st.info("💡 Pro Tip: Tick candidate row checkboxes below to shortlist and download.")
            st.markdown("<br>", unsafe_allow_html=True)
            
            c0, c1, c2, c3, c4, c5 = st.columns([0.8, 2.2, 1.2, 1.2, 1.2, 4.0])
            c0.write("**Shortlist**")
            c1.write("**Candidate Name**")
            c2.write("**Location**")
            c3.write("**Experience**")
            c4.write("**Exp Weight**")
            c5.write("**Technologies Found**")
            st.markdown("<hr style='margin:2px 0; border-top:2px solid #333;'>", unsafe_allow_html=True)
            for c in matched_candidates:
                r0, r1, r2, r3, r4, r5 = st.columns([0.8, 2.2, 1.2, 1.2, 1.2, 4.0])
                r0.checkbox("", key=f"chk_{c['ID']}_{st.session_state.reset_counter}")
                r1.markdown(f"👤 **{c['NAME']}**")
                r2.write(f"📍 **{c['LOCATION']}**")
                r3.write(f"{c['EXP']} Yrs ({c['TIER']})")
                r4.write(f"🎯 **{c['WEIGHT']}**")
                r5.markdown(c['SKILLS_DISP'])
                st.markdown("<hr style='margin:2px 0; border-top:1px dashed #ccc;'>", unsafe_allow_html=True)
        else: st.warning("⚠️ No profiles matching criteria found inside this bracket filter.")
    else: st.warning("No candidate records matched your search parameters.")
else: st.info("👋 Select your Target Roles and Location filters on the left sidebar parameter panel to begin shortlisting.")
