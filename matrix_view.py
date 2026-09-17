import streamlit as st
from utils import query_matched_profiles_via_stored_function, build_zip_archive

def is_fuzzy_match(kw, target_str):
    return kw.lower().strip() in target_str.lower().strip()

def on_master_toggle(m_key, a_keys):
    val = st.session_state[m_key]
    for k in a_keys:
        st.session_state[k] = val

def on_row_toggle(m_key, r_key):
    if not st.session_state[r_key]:
        st.session_state[m_key] = False

# ✅ THE DISTRIBUTED MICROSERVICES AI RANKING SERVICE core engine
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
        
        # Determine gross baseline bracket assignment strings
        if c_exp < 3.0: tl = "< 3 Yrs"
        elif 4.0 <= c_exp <= 10.0: tl = "4-10 Yrs"
        else: tl = "> 10 Yrs"

        # ======================================================================
        # 🔥 THE FOUR SCORING PILLARS MATHEMATICAL CO-EFFICIENT ALGORITHM
        # ======================================================================
        
        # Pillar 1: Keyword Density Match (Te) - Max 50 Points
        if active_keywords:
            skills_split = [s.strip().lower() for s in (raw_str.split("Skills:")[-1] if "Skills:" in raw_str else raw_str).split(",")]
            matches = sum(1 for kw in active_keywords if any(kw in s for s in skills_split))
            te_score = (matches / len(active_keywords)) * 50.0
        else:
            te_score = 0.0

        # Pillar 2: Bracket-Aware Experience Seniority Match (Sx) - Max 20 Points
        if s_tier == "< 3 Yrs (Entry Level)":
            sx_score = max(20.0 - (abs(2.0 - c_exp) * 10.0), 0.0)
        elif s_tier == "4-10 Yrs (Mid-Senior)":
            sx_score = max(20.0 - (abs(7.0 - c_exp) * 3.0), 0.0)
        elif s_tier == "> 10 Yrs (Principal)":
            sx_score = min(max((c_exp - 10.0) * 4.0, 0.0), 20.0)
        else: # "All Profiles (Ignore Exp Limit)"
            sx_score = min(c_exp * 2.0, 20.0)

        # Pillar 3: Taxonomy Role Proximity Bonus (Wp) - Max 20 Points
        # Scans if additional keywords are present indicating broad taxonomy thickness
        wp_score = 0.0
        if te_score > 0.0:
            all_raw_lower = raw_str.lower()
            bonus_tokens = ["sql", "performance tuning", "modelling", "linux", "docker", "kubernetes", "python", "aws", "azure"]
            extra_matches = sum(1 for tok in bonus_tokens if tok in all_raw_lower and not any(kw in tok for kw in active_keywords))
            wp_score = min(extra_matches * 5.0, 20.0)

        # Pillar 4: Multi-Location Precision Alignment (La) - Max 10 Points
        la_score = 0.0
        if selected_locations_filter:
            if c_loc in selected_locations_filter: la_score = 10.0
            else: la_score = 5.0
        else:
            la_score = 10.0

        # Final Aggregation pass
        final_aggregate_score = int(te_score + sx_score + wp_score + la_score)
        weight_fraction = min(max(final_aggregate_score / 100.0, 0.0), 1.0)
        
        # Format red highlighted skill tags for UI rendering
        disp_skills = raw_str.split("Skills:")[-1].strip() if "Skills:" in raw_str else raw_str
        hl_list = []
        for tag in disp_skills.split(","):
            st_tag = tag.strip()
            mf = active_keywords and any(is_fuzzy_match(kw, st_tag) for kw in active_keywords)
            hl_list.append(f"**:red[{st_tag}]**" if mf else st_tag)
            
        matched_candidates.append({
            "ID": str(item.get('ID', '')).strip(), "NAME": str(item.get('NAME', '')).strip(), "EXP": c_exp, "LOCATION": c_loc,
            "TIER": tl, "SCORE_PCT": final_aggregate_score, "SCORE_FRAC": weight_fraction, "SKILLS_DISP": ", ".join(hl_list), "BLOB": item.get('RESUME_BLOB', None)
        })
        
    if not matched_candidates:
        st.warning("⚠️ No profiles matching criteria found inside this bracket filter.")
        return

    # ✅ THE STRATEGIC MASTER SORTING PASS: Arranges candidate rows dynamically in memory by descending AI score ratings!
    matched_candidates = sorted(matched_candidates, key=lambda x: x["SCORE_PCT"], reverse=True)

    st.markdown(f"### 🎯 AI Ranking Workspace Matrix ({len(matched_candidates)} Profiles Found)")
    
    master_key = f"master_selected_{st.session_state.reset_counter}"
    all_keys = [f"chk_{cand['ID']}_{st.session_state.reset_counter}" for cand in matched_candidates]
    
    if master_key not in st.session_state: st.session_state[master_key] = False
    for k in all_keys:
        if k not in st.session_state: st.session_state[k] = False
        
    all_checked_by_user = all(st.session_state.get(k, False) for k in all_keys) if all_keys else False

    c0, c1, c2, c3, c4, c5 = st.columns([0.8, 2.2, 1.2, 1.2, 1.8, 3.4])
    with c0: 
        st.checkbox("All", value=all_checked_by_user, key=master_key, on_change=on_master_toggle, args=(master_key, all_keys))
    with c1: st.write("**Candidate Name**")
    with c2: st.write("**Location**")
    with c3: st.write("**Experience**")
    with c4: st.write("**AI Match Weight**")
    with c5: st.write("**Technologies Found**")
    st.markdown("<hr style='margin:2px 0; border-top:2px solid #333;'>", unsafe_allow_html=True)
    
    final_dl_list = []
    for c in matched_candidates:
        r_key = f"chk_{c['ID']}_{st.session_state.reset_counter}"
        r0, r1, r2, r3, r4, r5 = st.columns([0.8, 2.2, 1.2, 1.2, 1.8, 3.4])
        
        with r0: 
            st.checkbox("", key=r_key, on_change=on_row_toggle, args=(master_key, r_key))
            
        if st.session_state.get(r_key, False): 
            final_dl_list.append(c)
            
        with r1: st.markdown(f"👤 **{c['NAME']}**")
        with r2: st.write(f"📍 **{c['LOCATION']}**")
        with r3: st.write(f"{c['EXP']} Yrs ({c['TIER']})")
        
        with r4: 
            # ✅ THE VISUAL PIECE DE RESISTANCE: Dynamic color-shaded progress indicators based on score margins!
            if c["SCORE_PCT"] >= 80:
                st.markdown(f"<div style='margin-bottom:-4px; color:#2E7D32; font-size:12px; font-weight:bold;'>🟢 High Match</div>", unsafe_allow_html=True)
            elif 50 <= c["SCORE_PCT"] < 80:
                st.markdown(f"<div style='margin-bottom:-4px; color:#F57F17; font-size:12px; font-weight:bold;'>🟡 Medium Match</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='margin-bottom:-4px; color:#616161; font-size:12px; font-weight:bold;'>⚪ Low Match</div>", unsafe_allow_html=True)
            st.progress(c["SCORE_FRAC"], text=f"{c['SCORE_PCT']}% Match")
            
        with r5: st.markdown(c['SKILLS_DISP'])
        st.markdown("<hr style='margin:2px 0; border-top:1px dashed #ccc;'>", unsafe_allow_html=True)
        
    if final_dl_list:
        st.markdown("<br>", unsafe_allow_html=True)
        zb_bytes = build_zip_archive(final_dl_list)
        st.download_button(f"📥 Download Shortlisted ZIP Bundle ({len(final_dl_list)} Resumes)", zb_bytes, "Shortlisted_Resumes.zip", "application/zip", use_container_width=True, type="primary")
    else:
        st.info("💡 Pro Tip: Tick the 'All' checkbox at the header or choose row cells below to download.")
