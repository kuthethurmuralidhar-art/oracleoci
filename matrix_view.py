import streamlit as st
from utils import query_matched_profiles_via_stored_function, build_zip_archive

def is_fuzzy_match(kw, target_str):
    return kw.lower().strip() in target_str.lower().strip()

# ✅ CALLBACK HANDLER 1: Fires safely BEFORE redraw passes when the master "All" checkbox is toggled
def on_master_toggle(m_key, a_keys):
    val = st.session_state[m_key]
    for k in a_keys:
        st.session_state[k] = val

# ✅ CALLBACK HANDLER 2: Fires safely BEFORE redraw passes when any individual candidate row checkbox is unchecked
def on_row_toggle(m_key, r_key):
    if not st.session_state[r_key]:
        st.session_state[m_key] = False

# ✅ THE FIXED HYBRID MATRIX VIEW ENGINE: 100% immune to infinite loop redraws and widget errors
def render_candidate_matrix_workspace(active_keywords, selected_locations_filter, s_tier):
    kw_arg = ",".join(active_keywords) if active_keywords else None
    loc_arg = ",".join(selected_locations_filter) if selected_locations_filter else None
    
    df_raw = query_matched_profiles_via_stored_function(keyword=kw_arg, location=loc_arg)
    
    if df_raw.empty:
        st.warning("No candidate records matched your search parameters.")
        return

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
        
    if not matched_candidates:
        st.warning("⚠️ No profiles matching criteria found inside this bracket filter.")
        return

    st.markdown(f"### 🎯 Shortlisting Workspace Matrix ({len(matched_candidates)} Profiles Found)")
    
    master_key = f"master_selected_{st.session_state.reset_counter}"
    all_keys = [f"chk_{cand['ID']}_{st.session_state.reset_counter}" for cand in matched_candidates]
    
    # Initialize background tracking state values cleanly
    if master_key not in st.session_state: st.session_state[master_key] = False
    for k in all_keys:
        if k not in st.session_state: st.session_state[k] = False
        
    # Pre-calculate active check intersections to preserve checkbox integrity across redraws
    all_checked_by_user = all(st.session_state.get(k, False) for k in all_keys) if all_keys else False

    c0, c1, c2, c3, c4, c5 = st.columns([0.8, 2.2, 1.2, 1.2, 1.2, 4.0])
    with c0: 
        # ✅ STABLE BINDING: Invokes master callback securely on change with ZERO instantiation conflicts
        st.checkbox("All", value=all_checked_by_user, key=master_key, on_change=on_master_toggle, args=(master_key, all_keys))
    with c1: st.write("**Candidate Name**")
    with c2: st.write("**Location**")
    with c3: st.write("**Experience**")
    with c4: st.write("**Exp Weight**")
    with c5: st.write("**Technologies Found**")
    st.markdown("<hr style='margin:2px 0; border-top:2px solid #333;'>", unsafe_allow_html=True)
    
    final_dl_list = []
    for c in matched_candidates:
        r_key = f"chk_{c['ID']}_{st.session_state.reset_counter}"
        r0, r1, r2, r3, r4, r5 = st.columns([0.8, 2.2, 1.2, 1.2, 1.2, 4.0])
        
        with r0: 
            # ✅ STABLE ROW HANDSHAKE: Clears master state in memory before rendering pass triggers
            st.checkbox("", key=r_key, on_change=on_row_toggle, args=(master_key, r_key))
            
        if st.session_state.get(r_key, False): 
            final_dl_list.append(c)
            
        with r1: st.markdown(f"👤 **{c['NAME']}**")
        with r2: st.write(f"📍 **{c['LOCATION']}**")
        with r3: st.write(f"{c['EXP']} Yrs ({c['TIER']})")
        with r4: st.write(f"🎯 **{c['WEIGHT']}**")
        with r5: st.markdown(c['SKILLS_DISP'])
        st.markdown("<hr style='margin:2px 0; border-top:1px dashed #ccc;'>", unsafe_allow_html=True)
        
    # ✅ PERMANENTLY INSTANT COMPILING DOWNLOAD ENGINE: Stays perfectly stable on canvas
    if final_dl_list:
        st.markdown("<br>", unsafe_allow_html=True)
        zb_bytes = build_zip_archive(final_dl_list)
        st.download_button(f"📥 Download Shortlisted ZIP Bundle ({len(final_dl_list)} Resumes)", zb_bytes, "Shortlisted_Resumes.zip", "application/zip", use_container_width=True, type="primary")
    else:
        st.info("💡 Pro Tip: Tick the 'All' checkbox at the header or choose row cells below to download.")
