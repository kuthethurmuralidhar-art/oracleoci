import os, oracledb, pandas as pd

T_DIR = r"D:\Personal\AIrelatedDocs\Oracle AI\Project"
# ✅ TARGETED PROFILES FOLDER PATH LAYOUT
PROFILES_DIR = os.path.join(T_DIR, "profiles")
excel_path = os.path.join(T_DIR, "bulk_candidate_intake.xlsx")

# Import your single source of truth connection method natively from your service layers
from utils import get_db_connection

print("=================================================================================")
print("⏳ EXECUTING MASTER ENTERPRISE SPREADSHEET & BLOB SYNC PIPELINE...")
print("=================================================================================\n")

if not os.path.exists(excel_path):
    print(f"❌ Error: {excel_path} not found on disk!")
    exit()

if not os.path.exists(PROFILES_DIR):
    print(f"❌ Error: Profiles subfolder path '{PROFILES_DIR}' not found!")
    exit()

# --- PART 1: INGEST FRESH METADATA TEXT ROWS FROM EXCEL SPREADSHEET CATALOG ---
try:
    df = pd.read_excel(excel_path)
    df.columns = [c.strip().upper() for c in df.columns]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT email FROM skills")
    existing_emails = {row[0].strip().lower() for row in cursor.fetchall() if row and row[0]}
    
    text_rows_added = 0
    for idx, row in df.iterrows():
        email_clean = str(row["EMAIL"]).strip().lower()
        if not email_clean or email_clean == "nan": continue
        
        if email_clean in existing_emails:
            continue
            
        c_name = str(row["NAME"]).strip()
        c_email = str(row["EMAIL"]).strip()
        c_exp = float(row["EXPERIENCE_YEARS"])
        c_loc = str(row["LOCATION"]).strip()
        c_skills = str(row["SKILLS_MATRIX"]).strip()
        
        cursor.execute("SELECT NVL(MAX(id), 0) + 1 FROM skills")
        c_id = int(cursor.fetchone()[0])
        
        insert_sql = """
            INSERT INTO skills (id, name, email, experience_years, location, skills_matrix)
            VALUES (:1, :2, :3, :4, :5, :6)
        """
        cursor.execute(insert_sql, [c_id, c_name, c_email, c_exp, c_loc, c_skills])
        conn.commit()
        
        existing_emails.add(email_clean)
        text_rows_added += 1
        print(f"  📝 Ingested text metadata profile row: {c_name} ({c_email})")

    print(f"\n✨ Ingestion Pass Complete: Added {text_rows_added} fresh metadata profile rows.")
    print("-" * 81)
    
    # --- PART 2: AUTOMATED LOCAL FOLDER TO OCI BLOB SYNCHRONIZATION LOOP PASS ---
    print("🔎 Commencing automated binary resume PDF folder sync pass...")
    
    # Fetch all records currently stored inside your OCI Cloud table instance schemas
    cursor.execute("SELECT id, name, email, NVL(DBMS_LOB.GETLENGTH(resume_blob), 0) FROM skills")
    all_cloud_records = cursor.fetchall()
    
    # Gather a clean lowercase listing of all physical files inside your profiles folder
    available_files = os.listdir(PROFILES_DIR)
    available_files_lower = {f.lower(): f for f in available_files if f.lower().endswith(".pdf")}
    
    blob_updates_count = 0
    
    for row in all_cloud_records:
        r_id, r_name, r_email, r_blob_size = row[0], str(row[1]).strip(), str(row[2]).strip(), row[3]
        
        # ✅ THE SYNCHRONIZATION TRIGGER: Targets only rows where BLOB is missing or empty!
        if r_blob_size == 0:
            # Formulate smart fuzzy filename candidate matching strings
            name_clean = r_name.replace(" ", "_").lower()
            name_space = r_name.lower()
            
            target_filename_1 = f"{name_clean}_resume.pdf"
            target_filename_2 = f"{name_clean}.pdf"
            target_filename_3 = f"{name_space}_resume.pdf"
            target_filename_4 = f"{name_space}.pdf"
            
            matched_file = None
            for choice in [target_filename_1, target_filename_2, target_filename_3, target_filename_4]:
                if choice in available_files_lower:
                    matched_file = available_files_lower[choice]
                    break
            
            if matched_file:
                full_file_path = os.path.join(PROFILES_DIR, matched_file)
                try:
                    # Read the physical file direct into raw binary memory array blocks
                    with open(full_file_path, "rb") as f_pdf:
                        pdf_data_bytes = f_pdf.read()
                        
                    # Execute an optimized SQL UPDATE to stream bytes straight into your cloud table cell row
                    update_sql = "UPDATE skills SET resume_blob = :1 WHERE id = :2"
                    cursor.execute(update_sql, [pdf_data_bytes, r_id])
                    conn.commit()
                    
                    blob_updates_count += 1
                    print(f"  ✅ Successfully synchronized BLOB: {r_name} 📂 Linked ➔ '{matched_file}'")
                except Exception as file_err:
                    print(f"  ⚠️ Error reading file '{matched_file}': {file_err}")
            else:
                print(f"  ❌ No resume PDF match found inside folder for candidate: {r_name}")
                
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 81)
    print(f"🏆 SUCCESS: Ingested {text_rows_added} text profiles and synchronized {blob_updates_count} binary resume BLOBs!")
    print("=" * 81)

except Exception as main_e:
    print(f"\n❌ Pipeline Interruption Error: {main_e}")
