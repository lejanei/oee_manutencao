import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from auth import can
from db import get_engine, TABLES, fetch_df, count_rows, insert_row, update_row


from nav import render_sidebar

st.set_page_config(
    page_title="Cori • Manutenção & OEE",
    layout="wide",
    initial_sidebar_state="expanded",  # 🔒 mantém o sidebar aberto
)

render_sidebar()  # ← garante o sidebar persistente nesta página


def _safe_to_dt(v):
    if v in (None, "", "0000-00-00 00:00:00", "0000-00-00"): return None
    try: return pd.to_datetime(v, errors="coerce")
    except: return None
def _as_date(v): t=_safe_to_dt(v); return (t.date() if t is not None else datetime.now().date())
def _as_time(v): t=_safe_to_dt(v); return (t.time().replace(microsecond=0) if t is not None else datetime.now().time().replace(second=0, microsecond=0))

st.title("📊 OEE — Lançamentos")
engine = get_engine()
T = TABLES["oee"]

with st.expander("➕ Novo OEE", expanded=False):
    if can("create_oee"):
        c1, c2, c3 = st.columns(3)
        with c1:
            linha_new = st.number_input("Linha (int)", 0, step=1, value=1, key="oee_new_linha")
            disponibilidade_new = st.number_input("Disponibilidade", step=0.01, format="%.2f", value=0.00, key="oee_new_disponibilidade")
            performance_new     = st.number_input("Performance",     step=0.01, format="%.2f", value=0.00, key="oee_new_performance")
            qualidade_new       = st.number_input("Qualidade",       step=0.01, format="%.2f", value=0.00, key="oee_new_qualidade")
            oee_new             = st.number_input("OEE",             step=0.01, format="%.2f", value=0.00, key="oee_new_oee")
        with c2:
            producao_new   = st.number_input("Produção (int)", 0, step=1, value=0, key="oee_new_producao")
            rejeito_new    = st.number_input("Rejeito (int)",   0, step=1, value=0, key="oee_new_rejeito")
            disponivel_new = st.number_input("Disponível (int)", 0, step=1, value=0, key="oee_new_disponivel")
            produzindo_new = st.number_input("Produzindo (int)", 0, step=1, value=0, key="oee_new_produzindo")
            parada_new     = st.number_input("Parada (int)",     0, step=1, value=0, key="oee_new_parada")
        with c3:
            dti_new = st.date_input("Data início", value=datetime.now().date(), key="oee_new_dti")
            ti_new  = st.time_input("Hora início", value=datetime.now().time().replace(second=0, microsecond=0), key="oee_new_ti")
            dtf_new = st.date_input("Data fim", value=datetime.now().date(), key="oee_new_dtf")
            tf_new  = st.time_input("Hora fim", value=datetime.now().time().replace(second=0, microsecond=0), key="oee_new_tf")
        if st.button("💾 Salvar novo OEE", type="primary", use_container_width=True, key="oee_btn_save_new"):
            dt_ini = datetime.combine(st.session_state["oee_new_dti"], st.session_state["oee_new_ti"])
            dt_fim = datetime.combine(st.session_state["oee_new_dtf"], st.session_state["oee_new_tf"])
            if dt_fim < dt_ini: st.error("Hora fim não pode ser menor que hora início.")
            else:
                insert_row(engine, T, {
                    "linha": int(st.session_state["oee_new_linha"]),
                    "inicio": dt_ini, "fim": dt_fim,
                    "disponibilidade": float(st.session_state["oee_new_disponibilidade"]),
                    "performance": float(st.session_state["oee_new_performance"]),
                    "qualidade": float(st.session_state["oee_new_qualidade"]),
                    "oee": float(st.session_state["oee_new_oee"]),
                    "producao": int(st.session_state["oee_new_producao"]),
                    "rejeito": int(st.session_state["oee_new_rejeito"]),
                    "disponivel": int(st.session_state["oee_new_disponivel"]),
                    "produzindo": int(st.session_state["oee_new_produzindo"]),
                    "parada": int(st.session_state["oee_new_parada"]),
                })
                st.success("Registro de OEE inserido!"); st.rerun()
    else:
        st.info("Seu perfil não permite lançar OEE.")


with st.expander("✏️ Editar OEE", expanded=False):
    # seletor
    df_sel = fetch_df(engine, f"""
        SELECT id, linha, NULLIF(inicio,'0000-00-00 00:00:00') AS inicio
        FROM {T} ORDER BY inicio DESC, id DESC LIMIT 200
    """, {})
    if df_sel.empty:
        st.info("Não há lançamentos de OEE para editar.")
    else:
        opt_values = df_sel["id"].astype(int).tolist()
        opt_labels = df_sel.apply(lambda r: f"#{int(r['id'])} • Linha {int(r['linha'])} • "
                                            f"{(_safe_to_dt(r['inicio']).strftime('%d/%m %H:%M') if _safe_to_dt(r['inicio']) is not None else '')}", axis=1).tolist()
        sel_id_quick = st.selectbox("🔎 Selecionar OEE para edição", options=opt_values,
                                    format_func=lambda v: opt_labels[opt_values.index(v)], key="oee_quick_select")

        # carregar
        if sel_id_quick is not None:
            df_one = fetch_df(engine, f"""
                SELECT id, linha, NULLIF(inicio,'0000-00-00 00:00:00') AS inicio,
                    NULLIF(fim,'0000-00-00 00:00:00') AS fim,
                    disponibilidade, performance, qualidade, oee,
                    producao, rejeito, disponivel, produzindo, parada
                FROM {T} WHERE id=:id
            """, {"id": int(sel_id_quick)})
            if not df_one.empty:
                r = df_one.iloc[0]
                # formulário de edição (somente admin por padrão)
                c1, c2, c3 = st.columns(3)
                with c1:
                    linha_ed = st.number_input("Linha (int)", 0, step=1, value=int(r["linha"]), key="oee_ed_linha", disabled=not can("edit_oee"))
                    disponibilidade_ed = st.number_input("Disponibilidade", step=0.01, format="%.2f", value=float(r["disponibilidade"]), key="oee_ed_disponibilidade", disabled=not can("edit_oee"))
                    performance_ed     = st.number_input("Performance",     step=0.01, format="%.2f", value=float(r["performance"]), key="oee_ed_performance", disabled=not can("edit_oee"))
                    qualidade_ed       = st.number_input("Qualidade",       step=0.01, format="%.2f", value=float(r["qualidade"]), key="oee_ed_qualidade", disabled=not can("edit_oee"))
                    oee_ed             = st.number_input("OEE",             step=0.01, format="%.2f", value=float(r["oee"]), key="oee_ed_oee", disabled=not can("edit_oee"))
                with c2:
                    producao_ed   = st.number_input("Produção (int)", 0, step=1, value=int(r["producao"]), key="oee_ed_producao", disabled=not can("edit_oee"))
                    rejeito_ed    = st.number_input("Rejeito (int)",   0, step=1, value=int(r["rejeito"]), key="oee_ed_rejeito", disabled=not can("edit_oee"))
                    disponivel_ed = st.number_input("Disponível (int)", 0, step=1, value=int(r["disponivel"]), key="oee_ed_disponivel", disabled=not can("edit_oee"))
                    produzindo_ed = st.number_input("Produzindo (int)", 0, step=1, value=int(r["produzindo"]), key="oee_ed_produzindo", disabled=not can("edit_oee"))
                    parada_ed     = st.number_input("Parada (int)",     0, step=1, value=int(r["parada"]), key="oee_ed_parada", disabled=not can("edit_oee"))
                with c3:
                    dti_ed = st.date_input("Data início", value=_as_date(r["inicio"]), key="oee_ed_dti", disabled=not can("edit_oee"))
                    ti_ed  = st.time_input("Hora início", value=_as_time(r["inicio"]), key="oee_ed_ti", disabled=not can("edit_oee"))
                    dtf_ed = st.date_input("Data fim", value=_as_date(r["fim"]), key="oee_ed_dtf", disabled=not can("edit_oee"))
                    tf_ed  = st.time_input("Hora fim", value=_as_time(r["fim"]), key="oee_ed_tf", disabled=not can("edit_oee"))

                if can("edit_oee") and st.button("💾 Salvar edições", type="primary", use_container_width=True, key="oee_btn_save_edit"):
                    dt_ini = datetime.combine(st.session_state["oee_ed_dti"], st.session_state["oee_ed_ti"])
                    dt_fim = datetime.combine(st.session_state["oee_ed_dtf"], st.session_state["oee_ed_tf"])
                    if dt_fim < dt_ini: st.error("Hora fim não pode ser menor que hora início.")
                    else:
                        update_row(engine, T, "id", {
                            "id": int(r["id"]),
                            "linha": int(st.session_state["oee_ed_linha"]),
                            "inicio": dt_ini, "fim": dt_fim,
                            "disponibilidade": float(st.session_state["oee_ed_disponibilidade"]),
                            "performance": float(st.session_state["oee_ed_performance"]),
                            "qualidade": float(st.session_state["oee_ed_qualidade"]),
                            "oee": float(st.session_state["oee_ed_oee"]),
                            "producao": int(st.session_state["oee_ed_producao"]),
                            "rejeito": int(st.session_state["oee_ed_rejeito"]),
                            "disponivel": int(st.session_state["oee_ed_disponivel"]),
                            "produzindo": int(st.session_state["oee_ed_produzindo"]),
                            "parada": int(st.session_state["oee_ed_parada"]),
                        })
                        st.success("Lançamento de OEE atualizado!"); st.rerun()


with st.expander("🔎 Filtros", expanded=False):
    f_linha   = st.number_input("Linha (filtrar; 0 = todas)", min_value=0, step=1, value=0, key="oee_f_linha")
    f_ignore_period = st.checkbox("Mostrar tudo (ignorar período)", value=True, key="oee_f_ignore")
    f_dt_ini  = st.date_input("Data inicial", value=datetime.now().date() - timedelta(days=30), key="oee_f_di")
    f_dt_fim  = st.date_input("Data final", value=datetime.now().date(), key="oee_f_df")
    page_size = st.number_input("Itens por página", 5, 200, 25, 5, key="oee_page_size")

where, params = ["WHERE 1=1"], {}
if f_linha and int(f_linha) > 0: where.append("AND linha = :ln"); params["ln"] = int(f_linha)
if not st.session_state.get("oee_f_ignore", True):
    if f_dt_ini: params["di"] = datetime(f_dt_ini.year, f_dt_ini.month, f_dt_ini.day, 0,0,0); where.append("AND inicio >= :di")
    if f_dt_fim: params["df"] = datetime(f_dt_fim.year, f_dt_fim.month, f_dt_fim.day, 23,59,59); where.append("AND inicio <= :df")

total = count_rows(engine, T, " " + " ".join(where), params)
st.caption(f"Total com filtros: **{total}**")
page = st.number_input("Página", 1, max(1, (total - 1)//st.session_state["oee_page_size"] + 1), 1, key="oee_page")
offset = (page - 1) * st.session_state["oee_page_size"]

df_list = fetch_df(engine, f"""
    SELECT id, linha,
           NULLIF(inicio,'0000-00-00 00:00:00') AS inicio,
           NULLIF(fim,'0000-00-00 00:00:00')    AS fim,
           disponibilidade, performance, qualidade, oee,
           producao, rejeito, disponivel, produzindo, parada
    FROM {T} {" " + " ".join(where)} ORDER BY inicio DESC, id DESC
    LIMIT :lim OFFSET :off
""", {**params, "lim": int(st.session_state["oee_page_size"]), "off": int(offset)})
st.subheader("📋 Listagem")
if df_list.empty:
    st.info("Nada encontrado com os filtros atuais.")
else:
    df_show = df_list.copy()
    for col in ["inicio","fim"]:
        df_show[col] = df_show[col].apply(lambda v: (_safe_to_dt(v).strftime("%d/%m/%Y %H:%M") if _safe_to_dt(v) is not None else ""))
    st.dataframe(df_show, use_container_width=True)
    st.download_button("⬇️ Exportar CSV", df_list.to_csv(index=False).encode("utf-8"),
                       "oee.csv", "text/csv", use_container_width=True, key="oee_btn_csv")
