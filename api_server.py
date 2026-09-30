from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
import oracledb, io, zipfile
from utils import get_db_connection

app = FastAPI(title="OCI Talent Network Secure API Gateway", version="4.5")

@app.get("/api/candidates")
def get_candidates(keyword: str = None, location: str = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        kw_param = keyword.strip() if keyword else None
        loc_param = location.strip() if location else None
        
        ref_cursor = cursor.callfunc(
            "GET_MATCHED_CANDIDATES", oracledb.DB_TYPE_CURSOR,
            keyword_parameters={"P_KEYWORD": kw_param, "P_LOCATION": loc_param}
        )
        
        rows = ref_cursor.fetchall()
        cols = [col.name.upper() for col in ref_cursor.description]
        results = []
        for row in rows:
            record = dict(zip(cols, row))
            # Strip out giant raw binary blobs from general lookup responses to keep json data packets slim
            if "RESUME_BLOB" in record:
                record["HAS_BLOB"] = True if record["RESUME_BLOB"] is not None else False
                del record["RESUME_BLOB"]
            results.append(record)
            
        ref_cursor.close()
        cursor.close()
        conn.close()
        return {"status": "SUCCESS", "count": len(results), "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database lookup interruption error: {str(e)}")

# ✅ THE FIXED BINARY STREAMING CHANNELS SERVICE: Pipes file archives dynamically across Port 8000!
@app.get("/api/download/zip")
def download_shortlisted_resumes_stream(ids: str = Query(..., description="Comma-separated listing of target candidate primary IDs")):
    try:
        id_list = [str(x).strip() for x in ids.split(",") if x.strip()]
        if not id_list:
            raise HTTPException(status_code=400, detail="Invalid parameter context mapping list array.")
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Pull all target candidate profiles concurrently matching selection array conditions
        bind_placeholders = ",".join([f":{i+1}" for i in range(len(id_list))])
        select_sql = f"SELECT name, experience_years, resume_blob FROM skills WHERE id IN ({bind_placeholders})"
        cursor.execute(select_sql, id_list)
        records = cursor.fetchall()
        
        if not records:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="No matching profile rows discovered in cloud table sets.")
            
        # ✅ THE IN-MEMORY STORAGE BUFFER: Packs data streams straight into RAM to maximize transfer rates!
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for row in records:
                c_name, c_exp, c_blob = row[0], row[1], row[2]
                if c_blob is not None:
                    # Enforce strict corporate file naming layouts inside the compressed zip folder
                    formatted_file_name = f"{c_name.strip().replace(' ', '_')}_{c_exp}Yrs_Resume.pdf"
                    zf.writestr(formatted_file_name, c_blob)
                    
        cursor.close()
        conn.close()
        
        # Rewind pointer coordinate back to the header element position of memory blocks
        zip_buffer.seek(0)
        
        # ✅ STREAMING CHANNELS EMISSION: Pipes raw binary bytes across network ports instantly!
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=Shortlisted_Resumes.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API Streaming Pipeline Break: {str(e)}")
