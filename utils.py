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

def query_all_profiles_from_oracle():
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT id, name, email, experience_years, location, skills_matrix, resume_blob FROM skills", conn)
        conn.close()
        df.columns = [c.upper() for c in df.columns]
        return df
    except: return pd.DataFrame()

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
