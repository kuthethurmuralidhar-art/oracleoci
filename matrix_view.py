import streamlit as st
import requests, os
from utils import query_matched_profiles_via_stored_function, get_master_taxonomy

def is_fuzzy_match(kw, target_str):
    return kw.lower().strip() in target_str.lower().strip()

def on_master_toggle(m_key, a_keys):
    val = st.session_state[m_key]
    for k in a_keys:
        st.session_state[k] = val

def on_row_toggle(m_key, r_key):
    if not st.session_state[r_key]:
        st.session_state[m_key] = False

# ✅ HARD-CLAMPED PAGINATION GRID ENGINE (STRICTLY 8 RECORDS MAX PER PAGE)
def render_candidate_matrix_workspace(active_keywords, selected_locations_filter, s_tier):
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1

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
        
        # Enforce strict experience bracket boundaries
        if s_tier == "< 3 Yrs (Entry Level)":
            if c_exp >= 3.0: continue 
            tl, sx_score = "< 3 Yrs", max(20.0 - (abs(1.5 - c_exp) * 10.0), 0.0)
        elif s_tier == "3-10 Yrs (Mid-Senior)":
            if c_exp < 3.0 or c_exp >= 10.0: continue 
            tl, sx_score = "3-10 Yrs", max(20.0 - (abs(6.5 - c_exp) * 2.5), 0.0)
        elif s_tier == ">= 10 Yrs (Principal)":
            if c_exp < 10.0: continue 
            tl, sx_score = ">= 10 Yrs", min(max((c_exp - 10.0) * 4.0, 0.0), 20.0)
        else:
            tl, sx_score = "General", min(c_exp * 2.0, 20.0)

        te_score = (sum(1 for kw in active_keywords if is_fuzzy_match(kw, raw_str)) / len(active_keywords)) * 50.0 if active_keywords else 0.0
        la_score = 10.0 if not selected_locations_filter or c_loc in selected_locations_filter else 5.0
        final_aggregate_score = int(te_score + sx_score + la_score)
        
        disp_skills = raw_str
        hl_list = []
        for tag in disp_skills.split(","):
            st_tag = tag.strip()
            mf = active_keywords and any(is_fuzzy_match(kw, st_tag) for kw in active_keywords)
            hl_list.append(f"**:red[{st_tag}]**" if mf else st_tag)
            
        matched_candidates.append({
            "ID": str(item.get('ID', '')).strip(), "NAME": str(item.get('NAME', '')).strip(), "EXP": c_exp, "LOCATION": c_loc,
            "TIER": tl, "SCORE_PCT": final_aggregate_score, "SKILLS_DISP": ", ".join(hl_list), "EMAIL": str(item.get('EMAIL', '')).strip()
        })
        
    if not matched_candidates:
        st.warning("⚠️ No profiles matching the strict criteria found inside this bracket filter.")
        return

    matched_candidates = sorted(matched_candidates, key=lambda x: x["SCORE_PCT"], reverse=True)

    # ======================================================================
    # 📐 HARD-BOUNDED SLICER CORE
    # ======================================================================
    records_per_page = 8
    total_records = len(matched_candidates)
    total_pages = (total_records + records_per_page - 1) // records_per_page
    
    if st.session_state.current_page > total_pages:
        st.session_state.current_page = max(1, total_pages)

    start_idx = (st.session_state.current_page - 1) * records_per_page
    end_idx = start_idx + records_per_page
    
    # ✅ INSULATED LAYER SLICE: Strictly force python to grab only 8 records maximum
    page_records = list(matched_candidates[start_idx:end_idx])

    st.markdown(f"### 🎯 AI Ranking Workspace Matrix ({total_records} Total Profiles Available)")
    st.markdown(f"**Showing records {start_idx + 1} to {min(end_idx, total_records)} on Page {st.session_state.current_page} of {total_pages}**")
    
    master_key = f"master_selected_p{st.session_state.current_page}_{st.session_state.reset_counter}"
    all_keys = [f"chk_{cand['ID']}_{st.session_state.reset_counter}" for cand in page_records]
    
    if master_key not in st.session_state: st.session_state[master_key] = False
    for k in all_keys:
        if k not in st.session_state: st.session_state[k] = False
        
    all_checked_by_user = all(st.session_state.get(k, False) for k in all_keys) if all_keys else False

    c0, c1, c2, c3, c4, c5 = st.columns([0.8, 2.2, 1.2, 1.2, 2.0, 3.2])
    with c0: 
        st.checkbox("All", value=all_checked_by_user, key=master_key, on_change=on_master_toggle, args=(master_key, all_keys))
        
    with c1: st.write("**Candidate Name**")
    with c2: st.write("**Location**")
    with c3: st.write("**Experience**")
    with c4: st.write("**Ranking**")
    with c5: st.write("**Technologies Found**")
    st.markdown("<hr style='margin:2px 0; border-top:2px solid #333;'>", unsafe_allow_html=True)
    
    final_selected_ids = []
    for c in page_records:
        r_key = f"chk_{c['ID']}_{st.session_state.reset_counter}"
        r0, r1, r2, r3, r4, r5 = st.columns([0.8, 2.2, 1.2, 1.2, 2.0, 3.2])
        
        with r0: st.checkbox("", key=r_key, on_change=on_row_toggle, args=(master_key, r_key))
        if st.session_state.get(r_key, False): 
            final_selected_ids.append(c["ID"])
            
        with r1: 
            display_label = c['NAME'] if not c['EMAIL'].startswith("dummy_") else f"{c['NAME']} 👤"
            st.markdown(f"**{display_label}**")
        with r2: st.write(f"📍 **{c['LOCATION']}**")
        with r3: st.write(f"{c['EXP']} Yrs ({c['TIER']})")
        
        with r4: 
            if c["SCORE_PCT"] >= 80:
                st.markdown(f"<div style='background-color:#E8F5E9; border:1px solid #2E7D32; border-left:5px solid #2E7D32; padding:4px 8px; border-radius:4px; font-weight:bold; color:#1B5E20; text-align:center; font-size:12px;'>🟢 {c['SCORE_PCT']}%</div>", unsafe_allow_html=True)
            elif 60 <= c["SCORE_PCT"] < 80:
                st.markdown(f"<div style='background-color:#FFF3E0; border:1px solid #EF6C00; border-left:5px solid #EF6C00; padding:4px 8px; border-radius:4px; font-weight:bold; color:#E65100; text-align:center; font-size:12px;'>🟠 {c['SCORE_PCT']}%</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#FFEBEE; border:1px solid #C62828; border-left:5px solid #C62828; padding:4px 8px; border-radius:4px; font-weight:bold; color:#B71C1C; text-align:center; font-size:12px;'>🔴 {c['SCORE_PCT']}%</div>", unsafe_allow_html=True)
            
        with r5: st.markdown(c['SKILLS_DISP'])
        st.markdown("<hr style='margin:2px 0; border-top:1px dashed #ccc;'>", unsafe_allow_html=True)

    # ======================================================================
    # 🕹️ INTERACTIVE PREV / NEXT NAVIGATION CONTROLLER BUTTONS
    # ======================================================================
    st.markdown("<br>", unsafe_allow_html=True)
    p_col1, p_col2, p_col3 = st.columns([3, 2, 3])
    
    with p_col1:
        if st.session_state.current_page > 1:
            if st.button("◀️ Previous Page", use_container_width=True, key="btn_prev_page"):
                st.session_state.current_page -= 1
                st.rerun()
                
    with p_col2:
        st.markdown(f"<div style='text-align:center; font-weight:bold; padding-top:6px; background-color:#ECEFF1; border-radius:4px; border:1px solid #CFD8DC;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)
        
    with p_col3:
        if st.session_state.current_page < total_pages:
            if st.button("Next Page ▶️", use_container_width=True, key="btn_next_page"):
                st.session_state.current_page += 1
                st.rerun()

    # Dynamic cloud download panel
    if final_selected_ids:
        st.markdown("<br>", unsafe_allow_html=True)
        param_ids_string = ",".join(final_selected_ids)
        api_gateway_env = os.environ.get("API_GATEWAY_URL")
        if api_gateway_env:
            base_url = api_gateway_env.strip().rstrip("/")
            api_stream_url = f"{base_url}/api/download/zip?ids={param_ids_string}"
        else:
            api_stream_url = f"http://localhost:8000/api/download/zip?ids={param_ids_string}"
        
        try:
            response = requests.get(api_stream_url, stream=True, timeout=10)
            if response.status_code == 200:
                st.download_button(
                    f"📥 Download Shortlisted ZIP Bundle ({len(final_selected_ids)} Resumes)", 
                    data=response.content, file_name="Shortlisted_Resumes.zip", 
                    mime="application/zip", use_container_width=True, type="primary"
                )
            else:
                st.error("❌ Gateway Transmission Interruption: Cloud server reported an unstable connection state.")
        except Exception as api_err:
            st.error(f"⚠️ Cloud API Connection Refused: {api_err}")
