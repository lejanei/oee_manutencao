import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db import (
    get_engine, TABLES, fetch_df, count_rows, insert_row, update_row
)

# ----------------- Helpers -----------------
def _safe_to_dt(v):
    if v in (None, "", "0000-00-00 00:00:00", "0000-00-00"):
        return None
    try:
        return pd.to_datetime(v, errors="coerce")
    except Exception:
        return None

def _as_date(v):
    t = _safe_to_dt(v)
    return (t.date() if t is not None else datetime.now().date())

def _as_time(v):
    t = _safe_to_dt(v)
    return (t.time().replace(microsecond=0) if t is not None else datetime.now().time().replace(second=0, microsecond=0))

def _load_oee_record(engine, rec_id: int, table: str):
    sql = f"""
        SELECT
          id, linha,
          NULLIF(inicio,'0000-00-00 00:00:00') AS inicio,
          NULLIF(fim,'0000-00-00 00:00:00')    AS fim,
          disponibilidade, performance, qualidade, oee,
          producao, rejeito, disponivel, produzindo, parada
        FROM {table}
        WHERE id=:id
    """
    df = fetch_df(engine, sql, {"id": int(rec_id)})
    return None if df.empty else df.iloc[0].to_dict()

def _inject_edit_state_oee(rec):
    st.session_state["oee_ed_linha"] = int(rec.get("linha") or 0)

    st.session_state["oee_ed_disponibilidade"] = float(rec.get("disponibilidade") or 0.0)
    st.session_state["oee_ed_performance"]     = float(rec.get("performance") or 0.0)
    st.session_state["oee_ed_qualidade"]       = float(rec.get("qualidade") or 0.0)
    st.session_state["oee_ed_oee"]             = float(rec.get("oee") or 0.0)

    st.session_state["oee_ed_producao"]   = int(rec.get("producao") or 0)
    st.session_state["oee_ed_rejeito"]    = int(rec.get("rejeito") or 0)
    st.session_state["oee_ed_disponivel"] = int(rec.get("disponivel") or 0)
    st.session_state["oee_ed_produzindo"] = int(rec.get("produzindo") or 0)
    st.session_state["oee_ed_parada"]     = int(rec.get("parada") or 0)

    st.session_state["oee_ed_dti"] = _as_date(rec.get("inicio"))
    st.session_state["oee_ed_ti"]  = _as_time(rec.get("inicio"))
    st.session_state["oee_ed_dtf"] = _as_date(rec.get("fim"))
    st.session_state["oee_ed_tf"]  = _as_time(rec.get("fim"))

# ----------------- Setup -----------------
st.title("📊 OEE — Lançamentos")
engine = get_engine()
T = TABLES["oee"]  # nome da tabela, ex.: "oee"

# Estado de edição
if "oee_edit_id" not in st.session_state:
    st.session_state["oee_edit_id"] = None
if "oee_ed_loaded_for" not in st.session_state:
    st.session_state["oee_ed_loaded_for"] = None

# =====================================================
# 1) FORMULÁRIO — NOVO OEE
# =====================================================
with st.expander("➕ Novo OEE", expanded=False):

    c1, c2, c3 = st.columns(3)
    with c1:
        linha_new = st.number_input("Linha (int)", min_value=0, step=1, value=1, key="oee_new_linha")
        disponibilidade_new = st.number_input("Disponibilidade", step=0.01, format="%.2f", value=0.00, key="oee_new_disponibilidade")
        performance_new     = st.number_input("Performance",     step=0.01, format="%.2f", value=0.00, key="oee_new_performance")
        qualidade_new       = st.number_input("Qualidade",       step=0.01, format="%.2f", value=0.00, key="oee_new_qualidade")
        oee_new             = st.number_input("OEE",             step=0.01, format="%.2f", value=0.00, key="oee_new_oee")
    with c2:
        producao_new   = st.number_input("Produção (int)", min_value=0, step=1, value=0, key="oee_new_producao")
        rejeito_new    = st.number_input("Rejeito (int)",   min_value=0, step=1, value=0, key="oee_new_rejeito")
        disponivel_new = st.number_input("Disponível (int)", min_value=0, step=1, value=0, key="oee_new_disponivel")
        produzindo_new = st.number_input("Produzindo (int)", min_value=0, step=1, value=0, key="oee_new_produzindo")
        parada_new     = st.number_input("Parada (int)",     min_value=0, step=1, value=0, key="oee_new_parada")
    with c3:
        dti_new = st.date_input("Data início", value=datetime.now().date(), key="oee_new_dti")
        ti_new  = st.time_input("Hora início", value=datetime.now().time().replace(second=0, microsecond=0), key="oee_new_ti")
        dtf_new = st.date_input("Data fim", value=datetime.now().date(), key="oee_new_dtf")
        tf_new  = st.time_input("Hora fim", value=datetime.now().time().replace(second=0, microsecond=0), key="oee_new_tf")

    cA, _ = st.columns([1, 5])
    with cA:
        if st.button("💾 Salvar novo OEE", type="primary", use_container_width=True, key="oee_btn_save_new"):
            dt_ini = datetime.combine(st.session_state["oee_new_dti"], st.session_state["oee_new_ti"])
            dt_fim = datetime.combine(st.session_state["oee_new_dtf"], st.session_state["oee_new_tf"])
            if dt_fim < dt_ini:
                st.error("Hora fim não pode ser menor que hora início.")
            else:
                payload = {
                    "linha": int(st.session_state["oee_new_linha"]),
                    "inicio": dt_ini,
                    "fim": dt_fim,
                    "disponibilidade": float(st.session_state["oee_new_disponibilidade"]),
                    "performance": float(st.session_state["oee_new_performance"]),
                    "qualidade": float(st.session_state["oee_new_qualidade"]),
                    "oee": float(st.session_state["oee_new_oee"]),
                    "producao": int(st.session_state["oee_new_producao"]),
                    "rejeito": int(st.session_state["oee_new_rejeito"]),
                    "disponivel": int(st.session_state["oee_new_disponivel"]),
                    "produzindo": int(st.session_state["oee_new_produzindo"]),
                    "parada": int(st.session_state["oee_new_parada"]),
                }
                insert_row(engine, T, payload)
                st.success("Registro de OEE inserido!")
                st.rerun()



# ======================================================================
# 2) FORMULÁRIO — EDITAR OEE (via selectbox)
# ======================================================================
with st.expander("✏️ Editar OEE", expanded=False):

    # Opções (200 mais recentes) — tolerante a zero date
    sql_sel = f"""
        SELECT id, linha,
            NULLIF(inicio,'0000-00-00 00:00:00') AS inicio
        FROM {T}
        ORDER BY inicio DESC, id DESC
        LIMIT 200
    """
    df_sel = fetch_df(engine, sql_sel, {})

    if df_sel.empty:
        st.info("Não há lançamentos de OEE para editar.")
        sel_id_quick = None
    else:
        opt_values = df_sel["id"].astype(int).tolist()
        opt_labels = df_sel.apply(
            lambda r: f"#{int(r['id'])} • Linha {int(r['linha'])} • "
                    f"{(_safe_to_dt(r['inicio']).strftime('%d/%m %H:%M') if _safe_to_dt(r['inicio']) is not None else '')}",
            axis=1
        ).tolist()

        idx_default = 0
        if st.session_state.get("oee_edit_id") in opt_values:
            idx_default = opt_values.index(int(st.session_state["oee_edit_id"]))

        sel_id_quick = st.selectbox(
            "🔎 Selecionar OEE para edição",
            options=opt_values,
            format_func=lambda v: opt_labels[opt_values.index(v)],
            index=idx_default if len(opt_values) else 0,
            key="oee_quick_select",
        )

        # Se mudou o ID, carrega e injeta
        if sel_id_quick and st.session_state.get("oee_ed_loaded_for") != int(sel_id_quick):
            rec = _load_oee_record(engine, int(sel_id_quick), T)
            if rec:
                st.session_state["oee_edit_id"] = int(sel_id_quick)
                _inject_edit_state_oee(rec)
                st.session_state["oee_ed_loaded_for"] = int(sel_id_quick)

        # Primeiro carregamento
        if st.session_state.get("oee_ed_loaded_for") is None and sel_id_quick:
            rec = _load_oee_record(engine, int(sel_id_quick), T)
            if rec:
                st.session_state["oee_edit_id"] = int(sel_id_quick)
                _inject_edit_state_oee(rec)
                st.session_state["oee_ed_loaded_for"] = int(sel_id_quick)

    # Formulário de edição (usa session_state)
    rec_ok = st.session_state.get("oee_ed_loaded_for") is not None
    if not rec_ok:
        st.warning("Selecione um lançamento para carregar os campos de edição.")
    else:
        e1, e2, e3 = st.columns(3)
        with e1:
            st.number_input("Linha (int)", min_value=0, step=1, value=int(st.session_state.get("oee_ed_linha", 0)), key="oee_ed_linha")
            st.number_input("Disponibilidade", step=0.01, format="%.2f", value=float(st.session_state.get("oee_ed_disponibilidade", 0.0)), key="oee_ed_disponibilidade")
            st.number_input("Performance",     step=0.01, format="%.2f", value=float(st.session_state.get("oee_ed_performance", 0.0)), key="oee_ed_performance")
            st.number_input("Qualidade",       step=0.01, format="%.2f", value=float(st.session_state.get("oee_ed_qualidade", 0.0)), key="oee_ed_qualidade")
            st.number_input("OEE",             step=0.01, format="%.2f", value=float(st.session_state.get("oee_ed_oee", 0.0)), key="oee_ed_oee")
        with e2:
            st.number_input("Produção (int)",   min_value=0, step=1, value=int(st.session_state.get("oee_ed_producao", 0)), key="oee_ed_producao")
            st.number_input("Rejeito (int)",    min_value=0, step=1, value=int(st.session_state.get("oee_ed_rejeito", 0)), key="oee_ed_rejeito")
            st.number_input("Disponível (int)", min_value=0, step=1, value=int(st.session_state.get("oee_ed_disponivel", 0)), key="oee_ed_disponivel")
            st.number_input("Produzindo (int)", min_value=0, step=1, value=int(st.session_state.get("oee_ed_produzindo", 0)), key="oee_ed_produzindo")
            st.number_input("Parada (int)",     min_value=0, step=1, value=int(st.session_state.get("oee_ed_parada", 0)), key="oee_ed_parada")
        with e3:
            st.date_input("Data início", value=st.session_state.get("oee_ed_dti", datetime.now().date()), key="oee_ed_dti")
            st.time_input("Hora início", value=st.session_state.get("oee_ed_ti", datetime.now().time().replace(second=0, microsecond=0)), key="oee_ed_ti")
            st.date_input("Data fim", value=st.session_state.get("oee_ed_dtf", datetime.now().date()), key="oee_ed_dtf")
            st.time_input("Hora fim", value=st.session_state.get("oee_ed_tf", datetime.now().time().replace(second=0, microsecond=0)), key="oee_ed_tf")

        cE, _ = st.columns([1, 5])
        with cE:
            if st.button("💾 Salvar edições", type="primary", use_container_width=True, key="oee_btn_save_edit"):
                dt_ini = datetime.combine(st.session_state["oee_ed_dti"], st.session_state["oee_ed_ti"])
                dt_fim = datetime.combine(st.session_state["oee_ed_dtf"], st.session_state["oee_ed_tf"])
                if dt_fim < dt_ini:
                    st.error("Hora fim não pode ser menor que hora início.")
                else:
                    payload = {
                        "id": int(st.session_state["oee_edit_id"]),
                        "linha": int(st.session_state["oee_ed_linha"]),
                        "inicio": dt_ini,
                        "fim": dt_fim,
                        "disponibilidade": float(st.session_state["oee_ed_disponibilidade"]),
                        "performance": float(st.session_state["oee_ed_performance"]),
                        "qualidade": float(st.session_state["oee_ed_qualidade"]),
                        "oee": float(st.session_state["oee_ed_oee"]),
                        "producao": int(st.session_state["oee_ed_producao"]),
                        "rejeito": int(st.session_state["oee_ed_rejeito"]),
                        "disponivel": int(st.session_state["oee_ed_disponivel"]),
                        "produzindo": int(st.session_state["oee_ed_produzindo"]),
                        "parada": int(st.session_state["oee_ed_parada"]),
                    }
                    update_row(engine, T, "id", payload)
                    rec = _load_oee_record(engine, int(st.session_state["oee_edit_id"]), T)
                    if rec:
                        _inject_edit_state_oee(rec)
                    st.success("Lançamento de OEE atualizado!")



# =========================================
# 3) FILTROS (para a listagem)
# =========================================
with st.expander("🔎 Filtros", expanded=False):
    f_linha   = st.number_input("Linha (filtrar; 0 = todas)", min_value=0, step=1, value=0, key="oee_f_linha")
    f_ignore_period = st.checkbox("Mostrar tudo (ignorar período)", value=True, key="oee_f_ignore")
    f_dt_ini  = st.date_input("Data inicial", value=datetime.now().date() - timedelta(days=30), key="oee_f_di")
    f_dt_fim  = st.date_input("Data final", value=datetime.now().date(), key="oee_f_df")
    page_size = st.number_input("Itens por página", 5, 200, 25, 5, key="oee_page_size")

where, params = ["WHERE 1=1"], {}
if f_linha and int(f_linha) > 0:
    where.append("AND linha = :ln"); params["ln"] = int(f_linha)

# só filtra por período se o checkbox estiver DESLIGADO
if not st.session_state.get("oee_f_ignore", True):
    if f_dt_ini:
        params["di"] = datetime(f_dt_ini.year, f_dt_ini.month, f_dt_ini.day, 0, 0, 0)
        where.append("AND inicio >= :di")
    if f_dt_fim:
        params["df"] = datetime(f_dt_fim.year, f_dt_fim.month, f_dt_fim.day, 23, 59, 59)
        where.append("AND inicio <= :df")

where_sql = " " + " ".join(where)
order_sql = " ORDER BY inicio DESC, id DESC"
total = count_rows(engine, T, where_sql, params)
st.caption(f"Total com filtros: **{total}**")

# =========================================
# 4) TABELA (sem checkbox de seleção)
# =========================================
page = st.number_input("Página", 1, max(1, (total - 1) // st.session_state["oee_page_size"] + 1), 1, key="oee_page")
offset = (page - 1) * st.session_state["oee_page_size"]

sql_list = f"""
    SELECT
      id, linha,
      NULLIF(inicio,'0000-00-00 00:00:00') AS inicio,
      NULLIF(fim,'0000-00-00 00:00:00')    AS fim,
      disponibilidade, performance, qualidade, oee,
      producao, rejeito, disponivel, produzindo, parada
    FROM {T}
    {where_sql}{order_sql}
    LIMIT :lim OFFSET :off
"""
df_list = fetch_df(engine, sql_list, {**params, "lim": int(st.session_state["oee_page_size"]), "off": int(offset)})

st.subheader("📋 Listagem")
if df_list.empty:
    st.info("Nada encontrado com os filtros atuais. Tente marcar “Mostrar tudo (ignorar período)”.")
else:
    # Render amigável das datas, tolerante a NULL
    df_show = df_list.copy()
    for col in ["inicio", "fim"]:
        df_show[col] = df_show[col].apply(lambda v: (_safe_to_dt(v).strftime("%d/%m/%Y %H:%M") if _safe_to_dt(v) is not None else ""))
    st.dataframe(df_show, use_container_width=True)
    st.download_button(
        "⬇️ Exportar CSV",
        df_list.to_csv(index=False).encode("utf-8"),
        "oee.csv",
        "text/csv",
        use_container_width=True,
        key="oee_btn_csv"
    )
