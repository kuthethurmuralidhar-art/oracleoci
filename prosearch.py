import streamlit as st
from collections import Counter
from utils import get_db_connection, get_master_taxonomy, init_page_headers
# ✅ THE CLEAN FACTORIZED IMPORT: Call your standalone layout engine!
from matrix_view import render_candidate_matrix_workspace

init_page_headers()

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
        import pandas as pd
        return tally, tree, sorted(all_locs), len(df)
    except: return {}, {}, [], 0

if "reset_counter" not in st.session_state: st.session_state.reset_counter = 0

raw_tally, structured_tree, unique_locations, total_candidates = get_categorized_skills_with_counts()
autocomplete_options = sorted(list(raw_tally.keys()))
nlp_selection_tags = st.multiselect(
    "Select keywords:", options=autocomplete_options, 
    placeholder="Start typing...", key=f"main_search_index_{st.session_state.reset_counter}"
)

selected_sidebar_skills, selected_locations_filter = [], []
with st.sidebar:
    st.header("🎯 Parameters")
    if st.button("🧹 Clear All Filters", use_container_width=True):
        st.cache_data.clear()
        st.session_state.reset_counter += 1
        for k in list(st.session_state.keys()):
            if k.startswith("chk_") or "sel_all" in k or "master_selected" in k: st.session_state.pop(k, None)
        st.rerun()
    s_tier = st.radio("Select Target Bracket:", options=["All Profiles (Ignore Exp Limit)", "< 3 Yrs (Entry Level)", "4-10 Yrs (Mid-Senior)", "> 10 Yrs (Principal)"])
    selected_locations_filter = st.multiselect("Choose Target Cities:", options=unique_locations, key=f"loc_ms_{st.session_state.reset_counter}")
    active_selected_roles = st.multiselect("Select Target Professional Roles:", options=list(structured_tree.keys()), key=f"roles_ms_{st.session_state.reset_counter}")
    
    chained_available_skills = []
    if active_selected_roles:
        for typed_role in active_selected_roles:
            matched_key = next((k for k in structured_tree.keys() if typed_role.lower() in k.lower() or k.lower() in typed_role.lower()), None)
            if matched_key:
                for s_list in structured_tree.get(matched_key, {}).values():
                    for s_name in s_list:
                        if s_name not in chained_available_skills: chained_available_skills.append(s_name)
    else: chained_available_skills = list(raw_tally.keys())
    active_selected_skills = st.multiselect("Select chained technologies:", options=sorted(chained_available_skills), key=f"chained_skills_ms_{st.session_state.reset_counter}")
    for tag in active_selected_skills: selected_sidebar_skills.append(tag.lower().strip())

nlp_tokens = [t.lower().strip() for t in nlp_selection_tags]
sidebar_tokens = [s.lower().strip() for s in selected_sidebar_skills]
active_keywords = list(set(nlp_tokens + sidebar_tokens))

# ✅ THE CLEAN MASTER CALL: If filters are active, pass control cleanly to matrix_view!
if len(active_keywords) > 0 or len(selected_locations_filter) > 0:
    render_candidate_matrix_workspace(active_keywords, selected_locations_filter, s_tier)
else:
    st.info("👋 Select your Target Roles and Location filters on the left sidebar parameter panel to begin shortlisting.")
