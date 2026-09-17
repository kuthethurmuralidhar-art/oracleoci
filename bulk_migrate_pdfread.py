import pandas as pd, oracledb, os

WALLET_DIR = r"D:\Personal\AIrelatedDocs\Oracle AI\Project\wallet_files"
PROJECT_DIR = r"D:\Personal\AIrelatedDocs\Oracle AI\Project"
SUBFOLDER = os.path.join(PROJECT_DIR, "profiles")
EXCEL_TEMPLATE = os.path.join(PROJECT_DIR, "bulk_candidate_intake.xlsx")

connection_params = {
    "user": "ADMIN", "password": "ProOracle_4U", "dsn": "search_low",
    "config_dir": WALLET_DIR, "wallet_location": WALLET_DIR, "wallet_password": "Oracle_4U",
    "ssl_server_dn_match": False
}

try:
    if not os.path.exists(EXCEL_TEMPLATE): raise FileNotFoundError(f"Missing intake excel: {EXCEL_TEMPLATE}")
    df_catalog = pd.read_excel(EXCEL_TEMPLATE)
    
    print("⏳ Connecting to Oracle Cloud Infrastructure (OCI) Database...")
    conn = oracledb.connect(**connection_params)
    cursor = conn.cursor()
    
    # ✅ THE BULLETPROOF FIX: Wipes the old dirty table cells completely first!
    print("🧹 Wiping stale OCI records via TRUNCATE TABLE handshake commands...")
    cursor.execute("TRUNCATE TABLE skills")
    conn.commit()
    print("✨ Database table cleared successfully! Executing a fresh re-ingestion pass...")

    success_records = 0
    print("\n🚀 Executing Automated Spreadsheet-Driven Ingestion Engine...")
    print("-" * 105)
    
    for idx, row in df_catalog.iterrows():
        c_name = str(row['Name']).strip()
        c_email = str(row['Email']).strip()
        c_exp = float(row['Experience_Years'])
        c_loc = str(row['Location']).strip() if 'Location' in row else "General"
        c_pdf_name = str(row['PDF_File_Name']).strip()
        
        # ✅ THE CORE CURE: Natively captures your precise written worksheet skills instead of guessing!
        c_excel_skills = str(row['Skills_Matrix']).strip()
        if not c_excel_skills or c_excel_skills.lower() == "nan": c_excel_skills = "General"
        
        full_pdf_path = os.path.join(SUBFOLDER, c_pdf_name)
        binary_pdf_bytes = None
        
        if os.path.exists(full_pdf_path):
            with open(full_pdf_path, "rb") as pdf_file: binary_pdf_bytes = pdf_file.read()
            pdf_status = "Binary PDF BLOB Attached"
        else:
            pdf_status = "⚠️ Local PDF asset file not found (Null BLOB uploaded)"
            
        sql_insert = """
            INSERT INTO skills (name, email, experience_years, location, skills_matrix, resume_blob)
            VALUES (:1, :2, :3, :4, :5, :6)
        """
        cursor.execute(sql_insert, [c_name, c_email, c_exp, c_loc, c_excel_skills, binary_pdf_bytes])
        print(f" Row {idx+1}: ✅ Onboarded NEW Profile '{c_name}' ➔ Location: {c_loc} | Skills: {c_excel_skills} | [{pdf_status}]")
        success_records += 1
        
    conn.commit()
    print("-" * 105)
    print(f"🏆 INGESTION SUMMARY: Successfully loaded {success_records} fresh profiles with complete location parameters mapped.")
    cursor.close()
    conn.close()
except Exception as err:
    print(f"\n❌ Critical Pipeline Crash Exception: {err}")
