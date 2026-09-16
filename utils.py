import streamlit as st, pandas as pd, os, io, zipfile, requests

W_DIR = os.path.join(os.getcwd(), "wallet_files")

def get_db_connection():
    # Kept natively intact for background binary BLOB downloads if needed
    p = {
        "user": "ADMIN", "password": st.secrets["db_password"], "dsn": "search_low",
        "config_dir": W_DIR, "wallet_location": W_DIR, "wallet_password": st.secrets["wallet_password"],
        "ssl_server_dn_match": False
    }
    def bh(cursor, name, dtype, size, prec, scale):
        if dtype == oracledb.DB_TYPE_BLOB: return cursor.var(bytes, arraysize=cursor.arraysize)
    import oracledb
    conn = oracledb.connect(**p)
    conn.outputtypehandler = bh
    return conn

def get_master_taxonomy():
    return {
        "Delivery Manager": {"☁️ Cloud": ["OCI", "AWS", "Azure"], "📐 Design": ["Modelling", "Designer"], "🤖 AI": ["AI Skills"]},
        "Database Administrator (DBA)": {"💎 Core": ["Oracle DBA", "PL/SQL", "SQL"], "💾 Open": ["PostgreSQL"]},
        "Application Developer": {"🐍 Python": ["Python", "Flask", "Django", "Streamlit"], "☕ Java": ["Java"], "🤖 AI": ["AI Skills"]},
        "System Administrator": {"💿 Unix": ["Linux", "Unix"], "⚙️ Legacy": ["Websphere", "Dos", "Mac"]},
        "ITIL & Infrastructure Engineer": {"📦 DevOps": ["Docker", "Kubernetes", "Git"], "🧱 Legacy": ["Cobol"]}
    }

# ✅ THE DISCONNECTED MICROSERVICES HOOK: Fetches rows from the localhost API instead of connecting to Oracle!
def query_matched_profiles_via_stored_function(keyword=None, location=None):
    try:
        # Calls the high-speed local Web API endpoint gateway you just verified!
        api_url = "http://localhost:8000/api/candidates"
        payload_params = {}
        if keyword: payload_params["keyword"] = keyword
        if location: payload_params["location"] = location
        
        # Execute high-speed HTTP web request loop pass over local Port 8000
        response = requests.get(api_url, params=payload_params, timeout=5)
        
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get("status") == "SUCCESS":
                candidates_list = json_data.get("data", [])
                # Convert the incoming JSON array stream directly into a clean Pandas DataFrame grid
                df = pd.DataFrame(candidates_list)
                if not df.empty:
                    df.columns = [c.upper() for c in df.columns]
                return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"⚠️ Microservice Connection Failure: Ensure api_server.py is running via Uvicorn! Details: {e}")
        return pd.DataFrame()

def build_zip_archive(candidates):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for c in candidates:
            if c.get("BLOB") is not None:
                zf.writestr(f"{c['NAME'].replace(' ', '_')}_Resume.pdf", c["BLOB"])
    buf.seek(0)
    return buf.getvalue()

def init_page_headers():
    st.set_page_config(page_title="Talent Search", layout="wide")
    st.title("☁️ Talent Search Workspace")
    st.write("Tabular workstation powered by Oracle Cloud Infrastructure.")
    st.markdown("<hr>", unsafe_allow_html=True)

def apply_corporate_styles(wb):
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    f_hdr = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    f_cel = Font(name="Segoe UI", size=10, color="2C3E50")
    fill_hdr = PatternFill(start_color="1F77B4", end_color="1F77B4", fill_type="solid")
    fill_zb = PatternFill(start_color="F2F7FA", end_color="F2F7FA", fill_type="solid")
    fill_wh = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    border_thin = Border(left=Side(style="thin", color="E0E0E0"), right=Side(style="thin", color="E0E0E0"), top=Side(style="thin", color="E0E0E0"), bottom=Side(style="thin", color="E0E0E0"))
    for name in wb.sheetnames:
        ws = wb[name]
        ws.sheet_view.showGridLines = True
        for r in range(1, ws.max_row + 1):
            ws.row_dimensions[r].height = 26 if r == 1 else 22
            for c in range(1, ws.max_column + 1):
                cell = ws.cell(row=r, column=c)
                if r == 1: cell.font = f_hdr; cell.fill = fill_hdr
                else:
                    cell.font = f_cel; cell.border = border_thin
                    cell.fill = fill_zb if r % 2 == 0 else fill_wh
                    if str(cell.value).startswith("Go to") or str(cell.value).startswith("2026-"):
                        cell.alignment = Alignment(horizontal="center", vertical="center")
        for col_idx in range(1, ws.max_column + 1):
            lens = [len(str(ws.cell(row=r, column=col_idx).value or '')) for r in range(1, ws.max_row + 1)]
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max((max(lens) if lens else 10) + 3, 12), 75)
