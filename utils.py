import streamlit as st, pandas as pd, oracledb, os, io, zipfile

W_DIR = os.path.join(os.getcwd(), "wallet_files")

def get_db_connection():
    p = {
        "user": "ADMIN", "password": st.secrets["db_password"], "dsn": "search_low",
        "config_dir": W_DIR, "wallet_location": W_DIR, "wallet_password": st.secrets["wallet_password"],
        "ssl_server_dn_match": False
    }
    def bh(cursor, name, dtype, size, prec, scale):
        if dtype == oracledb.DB_TYPE_BLOB: return cursor.var(bytes, arraysize=cursor.arraysize)
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

# ✅ THE ENTERPRISE REFACTOR HOOK: Calls your Oracle DB function directly to retrieve data!
def query_matched_profiles_via_stored_function(keyword=None, location=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Executes the compiled Oracle DB function natively across the encrypted cloud handshake
        # Arguments parameter array indices are matched sequentially to [p_keyword, p_location]
        kw_param = keyword if keyword else None
        loc_param = location if location else None
        
        ref_cursor = cursor.callfunc("GET_MATCHED_CANDIDATES", oracledb.DB_TYPE_CURSOR, [kw_param, loc_param])
        
        # Fetch data rows dynamically straight from the active database memory cursor stream
        rows = ref_cursor.fetchall()
        cols = [col[0] for col in ref_cursor.description]
        
        df = pd.DataFrame(rows, columns=cols)
        
        ref_cursor.close()
        cursor.close()
        conn.close()
        
        df.columns = [c.upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Database Function Error: {e}")
        return pd.DataFrame()

def build_zip_archive(candidates):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for c in candidates:
            if c["BLOB"] is not None and len(c["BLOB"]) > 0:
                zf.writestr(f"{c['NAME'].replace(' ', '_')}_Resume.pdf", c["BLOB"])
    buf.seek(0)
    return buf.getvalue()

def init_page_headers():
    st.set_page_config(page_title="Talent Search", layout="wide")
    st.title("☁️ Talent Search Workspace")
    st.write("Tabular workstation powered by Oracle Cloud Infrastructure.")
    st.markdown("<hr>", unsafe_allow_html=True)

from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def apply_corporate_styles(wb):
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
