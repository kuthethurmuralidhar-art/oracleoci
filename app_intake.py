import streamlit as st, oracledb, os
from utils import get_db_connection, get_master_taxonomy, init_page_headers

st.set_page_config(page_title="Join Our OCI Talent Pool", layout="centered")

st.title("👤 Standardized Candidate Intake Portal")
st.write("Submit your unified professional profile directly into our secure OCI Talent Network Pool.")
st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

# Central dynamic function pass to grab master locations from active cloud tables natively
def get_standardized_cities():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT location FROM skills WHERE location IS NOT NULL")
        cities = sorted([row[0].strip().title() for row in cursor.fetchall() if row[0]])
        cursor.close()
        conn.close()
        return cities if cities else ["Mumbai", "Hyderabad", "Bengaluru", "Chennai", "Delhi"]
    except:
        return ["Mumbai", "Hyderabad", "Bengaluru", "Chennai", "Delhi"]

master_cities = get_standardized_cities()
taxonomy_tree = get_master_taxonomy()

with st.form("standardized_intake_form", clear_on_submit=True):
    c_name = st.text_input("Full Name:", placeholder="e.g. Muralidhar Murali")
    c_email = st.text_input("Email Address:", placeholder="e.g. murali@example.com")
    
    st.markdown("<br>", unsafe_allow_html=True)
    c0, c1 = st.columns(2)
    with c0:
        # ✅ STANDARDIZED SELECTION 1: Drops city strings parameter input in favor of master dropdown arrays!
        chosen_city = st.selectbox("Current City Location:", options=master_cities, index=0)
    with c1:
        # ✅ STANDARDIZED SELECTION 2: Standardized floating-point experience selection loop pass
        chosen_exp = st.selectbox("Total Professional Experience:", options=[float(i) for i in range(0, 31)], index=5)
        
    st.markdown("<br>", unsafe_allow_html=True)
    # ✅ STANDARDIZED SELECTION 3: Master professional role selector block
    chosen_role = st.selectbox("Select Your Target Core Professional Role:", options=list(taxonomy_tree.keys()), index=1)
    
    # ✅ STANDARDIZED SELECTION 4: Dynamic multi-select skills menu chained direct to selected corporate taxonomy matrix
    available_chained_skills = []
    if chosen_role in taxonomy_tree:
        for cat_bucket in taxonomy_tree[chosen_role].values():
            for skill_tag in cat_bucket:
                if skill_tag not in available_chained_skills:
                    available_chained_skills.append(skill_tag)
                    
    chosen_skills_tags = st.multiselect(
        "Select Your Matching Core Technologies / Competencies:", 
        options=sorted(available_chained_skills),
        placeholder="Click to pick matching skills matching your target role..."
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload Your Professional Resume Document (PDF Format Only):", type=["pdf"])
    
    submit_btn = st.form_submit_button("🚀 Submit Profile into Talent Pool", use_container_width=True, type="primary")

if submit_btn:
    if not c_name.strip() or not c_email.strip():
        st.warning("⚠️ Form Incomplete: Please fill out your Name and Email address fields before submitting.")
    elif not chosen_skills_tags:
        st.warning("⚠️ Competencies Missing: Please select at least one technology skill tag to complete your profile.")
    elif not uploaded_file:
        st.warning("⚠️ Document Missing: Please upload your resume PDF to complete your registration handshake.")
    else:
        try:
            pdf_bytes = uploaded_file.read()
            final_skills_matrix_string = f"Skills: {', '.join(chosen_skills_tags)}"
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Cloud integrity duplicate email constraint validation check
            cursor.execute("SELECT COUNT(*) FROM skills WHERE LOWER(email) = LOWER(TRIM(:1))", [c_email.strip()])
            if cursor.fetchone()[0] > 0:
                st.error(f"❌ Submission Rejected: A candidate with the email '{c_email.strip()}' is already registered in our cloud pool!")
                cursor.close()
                conn.close()
            else:
                # Natively calculate next available row incremental counter ID pointer
                next_id = int(cursor.execute("SELECT NVL(MAX(id), 0) + 1 FROM skills").fetchone()[0])
                
                # Insert package parameters layout containing the pristine VARCHAR2 configurations
                insert_sql = """
                    INSERT INTO skills (id, name, email, experience_years, location, skills_matrix, resume_blob)
                    VALUES (:1, :2, :3, :4, :5, :6, :7)
                """
                cursor.execute(insert_sql, [next_id, c_name.strip(), c_email.strip(), float(chosen_exp), chosen_city, final_skills_matrix_string, pdf_bytes])
                conn.commit()
                
                cursor.close()
                conn.close()
                
                st.success(f"🎉 CONGRATULATIONS, {c_name.strip()}! Your professional profile and standardized resume have been ingested successfully inside our Oracle Cloud Database engine!")
                st.balloons()
                
        except Exception as err:
            st.error(f"❌ Submission Pipeline Interruption Error: {err}")
