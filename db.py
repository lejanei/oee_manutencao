import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

TABLES = {
    "funcionarios": "funcionarios",
    "maquinas": "maquinas",
    "os": "ordens_servico",
    "prev": "ordens_preventiva",
    "mo_os": "mao_obra_os",
    "mo_prev": "mao_obra_preventiva",
    "oee": "tbl_oee_moinho",
}

@st.cache_resource
def get_engine() -> Engine:
    cfg = st.secrets["mysql"]
    url = f"mysql+pymysql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg.get('port',3306)}/{cfg['database']}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, pool_size=5, max_overflow=10, connect_args={"connect_timeout": 10})

def fetch_df(engine: Engine, sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        rs = conn.execute(text(sql), params or {})
        return pd.DataFrame(rs.fetchall(), columns=rs.keys())

def count_rows(engine: Engine, table_or_alias: str, where_sql: str, params: dict | None = None) -> int:
    df = fetch_df(engine, f"SELECT COUNT(*) AS n FROM {table_or_alias}{where_sql}", params or {})
    return int(df.iloc[0]["n"]) if not df.empty else 0

def insert_row(engine: Engine, table: str, payload: dict):
    cols = ", ".join(payload.keys())
    binds = ", ".join([f":{k}" for k in payload.keys()])
    sql = f"INSERT INTO {table} ({cols}) VALUES ({binds})"
    with engine.begin() as conn:
        conn.execute(text(sql), payload)

def update_row(engine: Engine, table: str, pk_name: str, payload: dict):
    assert pk_name in payload, "payload precisa conter a PK"
    sets = ", ".join([f"{k} = :{k}" for k in payload.keys() if k != pk_name])
    sql = f"UPDATE {table} SET {sets} WHERE {pk_name} = :{pk_name}"
    with engine.begin() as conn:
        conn.execute(text(sql), payload)

def delete_by_ids(engine: Engine, table: str, ids: list[int]):
    if not ids: return
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE id IN :ids"), {"ids": tuple(ids)})

def delete_where(engine: Engine, table: str, where_sql: str, params: dict):
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE {where_sql}"), params)

def options_maquinas(engine: Engine) -> pd.DataFrame:
    return fetch_df(engine, "SELECT id, nome, ativo FROM maquinas ORDER BY nome ASC", {})

def options_funcionarios(engine: Engine) -> pd.DataFrame:
    return fetch_df(engine, "SELECT id, nome, cargo FROM funcionarios ORDER BY nome ASC", {})
