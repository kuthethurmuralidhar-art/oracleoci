from fastapi import FastAPI, Query
import oracledb, os, pandas as pd

# Initialize the modern high-performance FastAPI microservice gateway engine
app = FastAPI(title="OCI Talent Microservice Gateway", version="1.0.0")
W_DIR = os.path.join(os.getcwd(), "wallet_files")

def get_db_connection():
    # Establishes the independent secure cloud database handshake link
    # NOTE: Since this background script runs outside Streamlit, we input credentials safely here!
    p = {
        "user": "ADMIN", 
        "password": "ProOracle_4U", # 🌟 REPLACE with your real DB password!
        "dsn": "search_low",
        "config_dir": W_DIR, 
        "wallet_location": W_DIR, 
        "wallet_password": "Oracle_4U", # 🌟 REPLACE with your real wallet zip password!
        "ssl_server_dn_match": False
    }
    return oracledb.connect(**p)

# ✅ THE REST API WEB ROUTE: Exposes your OCI Stored Function over a secure web address port!
@app.get("/api/candidates")
def get_candidates(
    keyword: str = Query(None, description="Technical skill keyword token parameter"),
    location: str = Query(None, description="Target city filter parameter string")
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        kw_param = keyword if keyword and keyword.strip() else None
        loc_param = location if location and location.strip() else None
        
        # Executes your compiled Oracle PL/SQL Stored Function natively across the network
        ref_cursor = cursor.callfunc("GET_MATCHED_CANDIDATES", oracledb.DB_TYPE_CURSOR, [kw_param, loc_param])
        
        rows = ref_cursor.fetchall()
        cols = [col[0].upper() for col in ref_cursor.description]
        
        # Build clean JSON record dictionary structures out of the active cursor memory stream
        results = []
        for row in rows:
            record = dict(zip(cols, row))
            
            # Cleanse binary BLOB cell arrays to prevent JSON network transmission freezes
            if "RESUME_BLOB" in record and record["RESUME_BLOB"] is not None:
                record["HAS_BLOB"] = True
                del record["RESUME_BLOB"] # We drop the raw BLOB; separate streaming route will download files!
            else:
                record["HAS_BLOB"] = False
                
            results.append(record)
            
        ref_cursor.close()
        cursor.close()
        conn.close()
        
        return {"status": "SUCCESS", "count": len(results), "data": results}
    except Exception as e:
        return {"status": "ERROR", "message": str(e), "data": []}
