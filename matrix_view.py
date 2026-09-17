import streamlit as st
from utils import query_matched_profiles_via_stored_function, build_zip_archive, get_master_taxonomy

def is_fuzzy_match(kw, target_str):
    return kw.lower().strip() in target_str.lower().strip()

def on_master_toggle(m_key, a_keys):
    val = st.session_state[m_key]
    for k in a_keys:
        st.session_state[k] = val

def on_row_toggle(m_key, r_key):
    if not st.session_state[r_key]:
        st.session_state[m_key] = False

def render_candidate_matrix_workspace(active_keywords, selected_locations_filter, s_tier):
    chosen_role = "Database Administrator (DBA)"
    for k in st.session_state.keys():
        if k.startswith("roles_ms_") and st.session_state[k]:
            chosen_role = st.session_state[k]
            break

    kw_arg = ",".join(active_keywords) if active_keywords else None
    loc_arg = ",".join(selected_locations_filter) if selected_locations_filter else None
    
    df_raw = query_matched_profiles_via_stored_function(keyword=kw_arg, location=loc_arg)
    
    if df_raw.empty:
        st.warning("No candidate records matched your search parameters.")
        return

    matched_candidates = []
    raw_records = df_raw.to_dict(orient="records")
    taxonomy_tree = get_master_taxonomy()
    
    role_allowed_bonus_tokens = ["sql", "performance tuning"]
    if chosen_role in taxonomy_tree:
        for bucket in taxonomy_tree[chosen_role].values():
            for skill in bucket:
                role_allowed_bonus_tokens.append(skill.lower().strip())

    for item in raw_records:
        raw_str = str(item.get('SKILLS_MATRIX', '')).strip()
        c_exp = float(item.get('EXPERIENCE_YEARS', 0.0))
        c_loc = str(item.get('LOCATION', 'General')).strip().title()
        
        if selected_locations_filter and c_loc not in selected_locations_filter: continue
        if active_keywords and not any(is_fuzzy_match(kw, raw_str) for kw in active_keywords): continue
        
        # ======================================================================
        # 🛡️ HARD BRACKET BOUNDARY EXCLUSION FILTERS (NO MORE LEAKING DATA!)
        # ======================================================================
        if s_tier == "< 3 Yrs (Entry Level)":
            if c_exp >= 3.0: continue # Completely drop if 3 years or over!
            tl, sx_score = "< 3 Yrs", max(20.0 - (abs(1.5 - c_exp) * 10.0), 0.0)
            
        elif s_tier == "3-10 Yrs (Mid-Senior)":
            if c_exp < 3.0 or c_exp >= 10.0: continue # Completely drop out of range!
            tl, sx_score = "3-10 Yrs", max(20.0 - (abs(6.5 - c_exp) * 2.5), 0.0)
            
        elif s_tier == ">= 10 Yrs (Principal)":
            if c_exp < 10.0: continue # Completely drop junior profiles!
            tl, sx_score = ">= 10 Yrs", min(max((c_exp - 10.0) * 4.0, 0.0), 20.0)
            
        else:
            tl, sx_score = "General", min(c_exp * 2.0, 20.0)

        # --- Pillar 1: Keyword Density Match (Te) ---
        if active_keywords:
            skills_split = [s.strip().lower() for s in (raw_str.split("Skills:")[-1] if "Skills:" in raw_str else raw_str).split(",")]
            matches = sum(1 for kw in active_keywords if any(kw in s for s in skills_split))
            te_score = (matches / len(active_keywords)) * 50.0
        else:
            te_score = 0.0

        # --- Pillar 3: Dynamic Taxonomy Role Proximity Bonus (Wp) ---
        wp_score = 0.0
        if te_score > 0.0:
            all_raw_lower = raw_str.lower()
            extra_matches = sum(1 for tok in role_allowed_bonus_tokens if tok in all_raw_lower and not any(kw in tok for kw in active_keywords))
            wp_score = min(extra_matches * 10.0, 20.0)

        # --- Pillar 4: Multi-Location Precision Alignment (La) ---
        la_score = 10.0 if not selected_locations_filter or c_loc in selected_locations_filter else 5.0

        final_aggregate_score = int(te_score + sx_score + wp_score + la_score)
        
        disp_skills = raw_str.split("Skills:")[-1].strip() if "Skills:" in raw_str else raw_str
        hl_list = []
        for tag in disp_skills.split(","):
            st_tag = tag.strip()
            mf = active_keywords and any(is_fuzzy_match(kw, st_tag) for kw in active_keywords)
            hl_list.append(f"**:red[{st_tag}]**" if mf else st_tag)
            
        matched_candidates.append({
            "ID": str(item.get('ID', '')).strip(), "NAME": str(item.get('NAME', '')).strip(), "EXP": c_exp, "LOCATION": c_loc,
            "TIER": tl, "SCORE_PCT": final_aggregate_score, "SKILLS_DISP": ", ".join(hl_list), "BLOB": item.get('RESUME_BLOB', None)
        })
        
    if not matched_candidates:
        st.warning("⚠️ No profiles matching the strict criteria found inside this bracket filter.")
        return

    matched_candidates = sorted(matched_candidates, key=lambda x: x["SCORE_PCT"], reverse=True)

    st.markdown(f"### 🎯 AI Ranking Workspace Matrix ({len(matched_candidates)} Profiles Found)")
    
    master_key = f"master_selected_{st.session_state.reset_counter}"
    all_keys = [f"chk_{cand['ID']}_{st.session_state.reset_counter}" for cand in matched_candidates]
    
    if master_key not in st.session_state: st.session_state[master_key] = False
    for k in all_keys:
        if k not in st.session_state: st.session_state[k] = False
        
    all_checked_by_user = all(st.session_state.get(k, False) for k in all_keys) if all_keys else False

    c0, c1, c2, c3, c4, c5 = st.columns([0.8, 2.2, 1.2, 1.2, 2.0, 3.2])
    with c0: 
        select_all = st.checkbox("All", value=all_checked_by_user, key=master_key, on_change=on_master_toggle, args=(master_key, all_keys))
        
    with c1: st.write("**Candidate Name**")
    with c2: st.write("**Location**")
    with c3: st.write("**Experience**")
    with c4: st.write("**Ranking**")
    with c5: st.write("**Technologies Found**")
    st.markdown("<hr style='margin:2px 0; border-top:2px solid #333;'>", unsafe_allow_html=True)
    
    final_dl_list = []
    for c in matched_candidates:
        r_key = f"chk_{c['ID']}_{st.session_state.reset_counter}"
        r0, r1, r2, r3, r4, r5 = st.columns([0.8, 2.2, 1.2, 1.2, 2.0, 3.2])
        
        with r0: st.checkbox("", key=r_key, on_change=on_row_toggle, args=(master_key, r_key))
        if st.session_state.get(r_key, False): final_dl_list.append(c)
            
        with r1: st.markdown(f"👤 **{c['NAME']}**")
        with r2: st.write(f"📍 **{c['LOCATION']}**")
        with r3: st.write(f"{c['EXP']} Yrs ({c['TIER']})")
        
        with r4: 
            if c["SCORE_PCT"] >= 80:
                st.markdown(f"<div style='background-color:#E8F5E9; border:1px solid #2E7D32; border-left:5px solid #2E7D32; padding:6px 12px; border-radius:4px; font-weight:bold; color:#1B5E20; text-align:center; font-size:13px;'>🟢 {c['SCORE_PCT']}%</div>", unsafe_allow_html=True)
            elif 60 <= c["SCORE_PCT"] < 80:
                st.markdown(f"<div style='background-color:#FFF3E0; border:1px solid #EF6C00; border-left:5px solid #EF6C00; padding:6px 12px; border-radius:4px; font-weight:bold; color:#E65100; text-align:center; font-size:13px;'>🟠 {c['SCORE_PCT']}%</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#FFEBEE; border:1px solid #C62828; border-left:5px solid #C62828; padding:6px 12px; border-radius:4px; font-weight:bold; color:#B71C1C; text-align:center; font-size:13px;'>🔴 {c['SCORE_PCT']}%</div>", unsafe_allow_html=True)
            
        with r5: st.markdown(c['SKILLS_DISP'])
        st.markdown("<hr style='margin:2px 0; border-top:1px dashed #ccc;'>", unsafe_allow_html=True)
        
    st.session_state["_last_all"] = select_all
    if final_dl_list:
        st.markdown("<br>", unsafe_allow_html=True)
        zb_bytes = build_zip_archive(final_dl_list)
        st.download_button(f"📥 Download Shortlisted ZIP Bundle ({len(final_dl_list)} Resumes)", zb_bytes, "Shortlisted_Resumes.zip", "application/zip", use_container_width=True, type="primary")
    else:
        st.info("💡 Pro Tip: Tick the 'All' checkbox at the header or choose row cells below to download.")
