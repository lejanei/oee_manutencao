import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ---------- Mapas de tabelas ----------
TABLES = {
    "funcionarios": "funcionarios",
    "maquinas": "maquinas",
    "os": "ordens_servico",
    "prev": "ordens_preventiva",
    "mo_os": "mao_obra_os",
    "mo_prev": "mao_obra_preventiva",
    "oee": "tbl_oee_moinho",
}

# ---------- Engine ----------
@st.cache_resource
def get_engine() -> Engine:
    cfg = st.secrets["mysql"]
    user = cfg["user"]
    pwd  = cfg["password"]
    host = cfg["host"]
    port = cfg.get("port", 3306)
    db   = cfg["database"]
    url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 10},
    )
    return engine

# ---------- Helpers SQL ----------
def fetch_df(engine: Engine, sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        rs = conn.execute(text(sql), params or {})
        df = pd.DataFrame(rs.fetchall(), columns=rs.keys())
    return df

def count_rows(engine: Engine, table_or_alias: str, where_sql: str, params: dict | None = None) -> int:
    # table_or_alias pode ser "tabela" ou "tabela alias"
    sql = f"SELECT COUNT(*) AS n FROM {table_or_alias}{where_sql}"
    df = fetch_df(engine, sql, params or {})
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
    sql = f"DELETE FROM {table} WHERE id IN :ids"
    with engine.begin() as conn:
        conn.execute(text(sql), {"ids": tuple(ids)})

# ---------- Combos ----------
def options_maquinas(engine: Engine) -> pd.DataFrame:
    sql = "SELECT id, nome, ativo FROM maquinas ORDER BY nome ASC"
    return fetch_df(engine, sql)

def options_funcionarios(engine: Engine) -> pd.DataFrame:
    sql = "SELECT id, nome, cargo FROM funcionarios ORDER BY nome ASC"
    return fetch_df(engine, sql)
