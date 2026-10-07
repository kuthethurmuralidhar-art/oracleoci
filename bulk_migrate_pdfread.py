import openpyxl, os, oracledb
from utils import get_db_connection

T_DIR = r"D:\Personal\AIrelatedDocs\Oracle AI\Project"
excel_path = os.path.join(T_DIR, "bulk_candidate_intake.xlsx")
profiles_dir = os.path.join(T_DIR, "profiles")

print("⏳ Initialising Incremental Append-Only Database Synchronisation Engine...")

if not os.path.exists(excel_path):
    print(f"❌ Error: Intake spreadsheet missing at {excel_path}! Run append_new_candidates.py first.")
    exit()

try:
    # 1. Establish secure network link into OCI Cloud Database instance pool
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 2. Scan all registered candidate emails already sitting in the cloud
    print("🔍 Fetching existing cloud table record matrix indexes...")
    cursor.execute("SELECT email FROM skills")
    existing_cloud_emails = {str(row[0]).strip().lower() for row in cursor.fetchall() if row and row[0]}
    print(f"   -> Found {len(existing_cloud_emails)} active candidate records currently stored in cloud database.")

    # 3. Load and parse your local intake spreadsheet catalog rows
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active
    
    new_records_to_upload = []
    for r in range(2, ws.max_row + 1):
        c_name = ws.cell(row=r, column=1).value
        c_email = str(ws.cell(row=r, column=2).value or "").strip()
        c_loc = ws.cell(row=r, column=3).value
        c_exp = ws.cell(row=r, column=4).value
        c_skills = ws.cell(row=r, column=5).value
        c_filename = ws.cell(row=r, column=6).value
        
        if not c_email:
            continue
            
        # THE DELTA FILTER: If email is already present inside OCI cloud database, completely skip it!
        if c_email.lower() in existing_cloud_emails:
            continue
            
        new_records_to_upload.append({
            "name": c_name, "email": c_email, "location": c_loc,
            "exp": c_exp, "skills": c_skills, "file": c_filename
        })

    if not new_records_to_upload:
        print("--> 💡 No new unmatched records found. Cloud table data is already perfectly synchronized!")
        cursor.close()
        conn.close()
        exit()

    print(f"🚀 Discovered {len(new_records_to_upload)} new candidate profiles to ingest. Initializing secure streaming...")
    
    # 4. ✅ PERFECTLY ALIGNED: Removed phone column completely. Maps strictly to your 6 real table attributes!
    insert_sql = """
        INSERT INTO skills (name, email, location, experience_years, skills_matrix, resume_blob)
        VALUES (:1, :2, :3, :4, :5, :6)
    """

    for cand in new_records_to_upload:
        full_pdf_path = os.path.join(profiles_dir, cand["file"])
        blob_bytes = None
        
        if os.path.exists(full_pdf_path):
            with open(full_pdf_path, "rb") as f_bin:
                blob_bytes = f_bin.read()
        else:
            print(f"  ⚠️ Warning: Physical PDF file '{cand['file']}' missing in profiles folder. Uploading profile text row only.")

        # Execute single row insert safely mapping to the 6 explicit columns
        cursor.execute(insert_sql, [
            cand["name"], cand["email"], cand["location"], 
            float(cand["exp"] or 0.0), cand["skills"], blob_bytes
        ])
        print(f"  ✅ Successfully uploaded fresh profile: {cand['name']} ({cand['email']}) to OCI.")

    # 5. Lock down transaction and save permanent cell state modifications
    conn.commit()
    print("\n📊 SUCCESS: Incremental OCI Cloud migration pass complete. New rows safely integrated!")
    
    cursor.close()
    conn.close()

except Exception as err:
    print(f"❌ Database Transaction Interruption Error: {str(err)}")
