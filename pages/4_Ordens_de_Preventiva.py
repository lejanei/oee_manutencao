import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time
from db import (
    get_engine, TABLES, fetch_df, count_rows, insert_row, update_row, delete_by_ids,
    options_maquinas, options_funcionarios
)

# ----------------- Helpers -----------------
def _as_date(v):
    try:
        return pd.to_datetime(v).date()
    except Exception:
        return datetime.now().date()

def _as_time(v):
    try:
        t = pd.to_datetime(v).time()
        return t.replace(microsecond=0)
    except Exception:
        return datetime.now().time().replace(second=0, microsecond=0)

def _load_prev_record(engine, prev_id: int):
    sql = """
        SELECT id, id_maquina, id_funcionario, datahora_inicio, datahora_fim,
               servico_realizado, status
        FROM ordens_preventiva
        WHERE id=:id
    """
    df = fetch_df(engine, sql, {"id": int(prev_id)})
    return None if df.empty else df.iloc[0].to_dict()

def _inject_edit_state_prev(rec, id2maqname, id2funcname):
    """
    Injeta valores no session_state ANTES de desenhar os widgets de edição.
    """
    st.session_state["prev_ed_maquina_name"] = id2maqname.get(int(rec["id_maquina"]), "") if rec.get("id_maquina") else ""
    st.session_state["prev_ed_resp_name"]    = id2funcname.get(int(rec["id_funcionario"]), "—") if rec.get("id_funcionario") else "—"

    st.session_state["prev_ed_servico"] = str(rec.get("servico_realizado") or "")
    st.session_state["prev_ed_status"]  = str(rec.get("status") or "Aberta")

    st.session_state["prev_ed_dti"] = _as_date(rec.get("datahora_inicio"))
    st.session_state["prev_ed_ti"]  = _as_time(rec.get("datahora_inicio"))
    st.session_state["prev_ed_dtf"] = _as_date(rec.get("datahora_fim"))
    st.session_state["prev_ed_tf"]  = _as_time(rec.get("datahora_fim"))

# ----------------- Setup -----------------
st.title("🧾 Ordens de Preventiva")
engine = get_engine()
T = TABLES["prev"]       # ordens_preventiva
T_MO = TABLES["mo_prev"] # mao_obra_preventiva

maqs  = options_maquinas(engine)
funcs = options_funcionarios(engine)

MAQ_OPTS  = maqs["nome"].tolist() if not maqs.empty else []
FUNC_OPTS = funcs["nome"].tolist() if not funcs.empty else []

name2maqid  = {r["nome"]: int(r["id"]) for _, r in maqs.iterrows()} if not maqs.empty else {}
name2funcid = {r["nome"]: int(r["id"]) for _, r in funcs.iterrows()} if not funcs.empty else {}
id2maqname  = {int(r["id"]): r["nome"] for _, r in maqs.iterrows()} if not maqs.empty else {}
id2funcname = {int(r["id"]): r["nome"] for _, r in funcs.iterrows()} if not funcs.empty else {}

# Estado
if "prev_edit_id" not in st.session_state:
    st.session_state["prev_edit_id"] = None
if "prev_ed_loaded_for" not in st.session_state:
    st.session_state["prev_ed_loaded_for"] = None

# =====================================================
# 1) FORMULÁRIO — NOVA PREVENTIVA
# =====================================================
with st.expander("➕ Nova Preventiva", expanded=False):

    col1, col2, col3 = st.columns(3)
    with col1:
        if MAQ_OPTS:
            nome_maquina_new = st.selectbox("Máquina", MAQ_OPTS, key="prev_new_maquina")
        else:
            nome_maquina_new = st.selectbox("Máquina", [], key="prev_new_maquina_empty")
        resp_opts_new = ["—"] + FUNC_OPTS
        nome_func_new = st.selectbox("Responsável (opcional)", resp_opts_new, index=0, key="prev_new_resp")
    with col2:
        dti_new = st.date_input("Data início", value=datetime.now().date(), key="prev_new_dti")
        ti_new  = st.time_input("Hora início", value=datetime.now().time().replace(second=0, microsecond=0), key="prev_new_ti")
        dtf_new = st.date_input("Data fim", value=datetime.now().date(), key="prev_new_dtf")
        tf_new  = st.time_input("Hora fim", value=datetime.now().time().replace(second=0, microsecond=0), key="prev_new_tf")
    with col3:
        servico_new = st.text_area("Serviço realizado", key="prev_new_servico")
        status_new  = st.text_input("Status", value="Aberta", key="prev_new_status")

    cA, _ = st.columns([1, 5])
    with cA:
        if st.button("💾 Salvar nova Preventiva", type="primary", use_container_width=True, key="prev_btn_save_new"):
            if not MAQ_OPTS and not st.session_state.get("prev_new_maquina_empty"):
                st.error("Cadastre máquinas antes de criar Preventivas.")
            else:
                # pega a escolha correta de máquina (um dos dois widgets)
                maquina_escolhida = st.session_state.get("prev_new_maquina") or st.session_state.get("prev_new_maquina_empty")
                dt_ini = datetime.combine(st.session_state["prev_new_dti"], st.session_state["prev_new_ti"])
                dt_fim = datetime.combine(st.session_state["prev_new_dtf"], st.session_state["prev_new_tf"])
                if dt_fim < dt_ini:
                    st.error("Hora fim não pode ser menor que hora início.")
                else:
                    payload = {
                        "id_maquina": int(name2maqid.get(maquina_escolhida)) if maquina_escolhida else None,
                        "id_funcionario": (None if st.session_state["prev_new_resp"] in ("—", "", None) else int(name2funcid.get(st.session_state["prev_new_resp"]))),
                        "datahora_inicio": dt_ini,
                        "datahora_fim": dt_fim,
                        "servico_realizado": st.session_state["prev_new_servico"],
                        "status": st.session_state["prev_new_status"] or "Aberta",
                    }
                    insert_row(engine, T, payload)
                    st.success("Preventiva inserida!")
                    st.rerun()



# ======================================================================
# 2) FORMULÁRIO — EDITAR PREVENTIVA (via selectbox)
# ======================================================================
with st.expander("✏️ Editar Preventiva", expanded=False):

    # Monta opções (200 mais recentes)
    sql_sel = """
        SELECT p.id, m.nome AS maquina, p.datahora_inicio
        FROM ordens_preventiva p
        JOIN maquinas m ON m.id = p.id_maquina
        ORDER BY p.datahora_inicio DESC, p.id DESC
        LIMIT 200
    """
    df_sel = fetch_df(engine, sql_sel, {})

    if df_sel.empty:
        st.info("Não há preventivas para editar.")
        sel_id_quick = None
        # zera estados de edição para evitar IDs antigos/None inconsistentes
        st.session_state["prev_edit_id"] = None
        st.session_state["prev_ed_loaded_for"] = None

    else:
        opt_values = df_sel["id"].astype(int).tolist()
        opt_labels = df_sel.apply(
            lambda r: f"#{int(r['id'])} • {r['maquina']} • "
                    f"{pd.to_datetime(r['datahora_inicio']).strftime('%d/%m %H:%M') if pd.notna(r['datahora_inicio']) else ''}",
            axis=1
        ).tolist()

        idx_default = 0
        if st.session_state.get("prev_edit_id") in opt_values:
            idx_default = opt_values.index(int(st.session_state["prev_edit_id"]))

        sel_id_quick = st.selectbox(
            "🔎 Selecionar Preventiva para edição",
            options=opt_values,
            format_func=lambda v: opt_labels[opt_values.index(v)],
            index=idx_default if len(opt_values) else 0,
            key="prev_quick_select",
        )

        # Se mudou o ID, injeta valores no session_state
        if sel_id_quick and st.session_state.get("prev_ed_loaded_for") != int(sel_id_quick):
            rec = _load_prev_record(engine, int(sel_id_quick))
            if rec:
                st.session_state["prev_edit_id"] = int(sel_id_quick)
                _inject_edit_state_prev(rec, id2maqname, id2funcname)
                st.session_state["prev_ed_loaded_for"] = int(sel_id_quick)

        # Primeiro carregamento (se necessário)
        if st.session_state.get("prev_ed_loaded_for") is None and sel_id_quick:
            rec = _load_prev_record(engine, int(sel_id_quick))
            if rec:
                st.session_state["prev_edit_id"] = int(sel_id_quick)
                _inject_edit_state_prev(rec, id2maqname, id2funcname)
                st.session_state["prev_ed_loaded_for"] = int(sel_id_quick)

    # Formulário de edição (usa session_state)
    rec_ok = st.session_state.get("prev_ed_loaded_for") is not None
    if not rec_ok:
        st.warning("Selecione uma preventiva para carregar os campos de edição.")
    else:
        col1e, col2e, col3e = st.columns(3)
        with col1e:
            if MAQ_OPTS:
                try:
                    idx_maq = MAQ_OPTS.index(st.session_state.get("prev_ed_maquina_name", "")) if st.session_state.get("prev_ed_maquina_name", "") in MAQ_OPTS else 0
                except Exception:
                    idx_maq = 0
                nome_maquina_ed = st.selectbox("Máquina", MAQ_OPTS, index=idx_maq, key="prev_ed_maquina_name")
            else:
                nome_maquina_ed = st.selectbox("Máquina", [], key="prev_ed_maquina_name_empty")

            resp_opts_ed = ["—"] + FUNC_OPTS
            try:
                idx_resp = resp_opts_ed.index(st.session_state.get("prev_ed_resp_name", "—")) if st.session_state.get("prev_ed_resp_name", "—") in resp_opts_ed else 0
            except Exception:
                idx_resp = 0
            nome_func_ed = st.selectbox("Responsável (opcional)", resp_opts_ed, index=idx_resp, key="prev_ed_resp_name")

        with col2e:
            dti_ed = st.date_input("Data início", value=st.session_state.get("prev_ed_dti", datetime.now().date()), key="prev_ed_dti")
            ti_ed  = st.time_input("Hora início", value=st.session_state.get("prev_ed_ti", datetime.now().time().replace(second=0, microsecond=0)), key="prev_ed_ti")
            dtf_ed = st.date_input("Data fim", value=st.session_state.get("prev_ed_dtf", datetime.now().date()), key="prev_ed_dtf")
            tf_ed  = st.time_input("Hora fim", value=st.session_state.get("prev_ed_tf", datetime.now().time().replace(second=0, microsecond=0)), key="prev_ed_tf")

        with col3e:
            servico_ed = st.text_area("Serviço realizado", value=st.session_state.get("prev_ed_servico", ""), key="prev_ed_servico")
            status_ed  = st.text_input("Status", value=st.session_state.get("prev_ed_status", "Aberta"), key="prev_ed_status")

        cE, _ = st.columns([1, 5])
        with cE:
            if st.button("💾 Salvar edições", type="primary", use_container_width=True, key="prev_btn_save_edit"):
                dt_ini = datetime.combine(st.session_state["prev_ed_dti"], st.session_state["prev_ed_ti"])
                dt_fim = datetime.combine(st.session_state["prev_ed_dtf"], st.session_state["prev_ed_tf"])
                if dt_fim < dt_ini:
                    st.error("Hora fim não pode ser menor que hora início.")
                else:
                    # pega máquina da edição (considera o widget vazio quando não há opções)
                    maquina_ed = st.session_state.get("prev_ed_maquina_name") or st.session_state.get("prev_ed_maquina_name_empty")
                    payload = {
                        "id": int(st.session_state["prev_edit_id"]),
                        "id_maquina": int(name2maqid.get(maquina_ed)) if maquina_ed else None,
                        "id_funcionario": (None if st.session_state["prev_ed_resp_name"] in ("—", "", None) else int(name2funcid.get(st.session_state["prev_ed_resp_name"]))),
                        "datahora_inicio": dt_ini,
                        "datahora_fim": dt_fim,
                        "servico_realizado": st.session_state["prev_ed_servico"],
                        "status": st.session_state["prev_ed_status"] or "Aberta",
                    }
                    update_row(engine, T, "id", payload)
                    # Recarrega e reinjeta para manter sincronizado
                    rec = _load_prev_record(engine, int(st.session_state["prev_edit_id"]))
                    if rec:
                        _inject_edit_state_prev(rec, id2maqname, id2funcname)
                    st.success("Preventiva alterada com sucesso!")

# ======================================================================
# 2.1) MÃO DE OBRA — abaixo do formulário de edição (com edição/exclusão)
# ======================================================================

with st.expander("🧑‍🔧 Mão de Obra da Preventiva selecionada", expanded=False):

    # pega e valida o ID selecionado
    prev_id_raw = st.session_state.get("prev_edit_id", None)
    try:
        prev_id_ref = int(prev_id_raw) if prev_id_raw is not None else None
    except (TypeError, ValueError):
        prev_id_ref = None

    if prev_id_ref is None:
        st.info("Selecione uma Preventiva no seletor acima para lançar mão de obra.")
    else:
        st.caption(f"Preventiva selecionada: **#{prev_id_ref}**")

        # --- Formulário de inserção de MO ---
        with st.form("form_mo_prev_inline"):
            colm1, colm2, colm3 = st.columns(3)
            with colm1:
                func_nome = st.selectbox("Funcionário", FUNC_OPTS, key="moprev_func")
                func_id   = name2funcid.get(func_nome) if func_nome else None
            with colm2:
                data_mo = st.date_input("Data", value=date.today(), key="moprev_data")
                hi_mo   = st.time_input("Hora início", value=time(8, 0, 0), key="moprev_hi")
                hf_mo   = st.time_input("Hora fim",    value=time(12, 0, 0), key="moprev_hf")
            with colm3:
                st.write("")
                st.write("")
                submitted = st.form_submit_button("➕ Inserir apontamento", type="primary", use_container_width=True)

            if submitted:
                if func_id is None:
                    st.error("Selecione o funcionário.")
                elif hf_mo < hi_mo:
                    st.error("Hora fim não pode ser menor que hora início (MO).")
                else:
                    insert_row(engine, T_MO, {
                        "id_ordem_preventiva": int(prev_id_ref),
                        "id_funcionario": int(func_id),
                        "data": data_mo,
                        "hora_inicio": hi_mo,
                        "hora_fim": hf_mo
                    })
                    st.success("Apontamento inserido!")
                    st.rerun()

    # --- Listagem de MOs da Preventiva selecionada (com edição/exclusão) ---
    st.markdown("### Apontamentos lançados")
    sql_mo = """
        SELECT mo.id, mo.id_funcionario, f.nome AS funcionario, mo.data, mo.hora_inicio, mo.hora_fim
        FROM mao_obra_preventiva mo
        JOIN funcionarios f ON f.id = mo.id_funcionario
        WHERE mo.id_ordem_preventiva = :id
        ORDER BY mo.data ASC, mo.hora_inicio ASC
    """
    df_mo = fetch_df(engine, sql_mo, {"id": prev_id_ref})
    if df_mo.empty:
        st.info("Nenhum apontamento para esta Preventiva.")
    else:
        for _, row in df_mo.iterrows():
            mo_id = int(row["id"])
            func_nome_row = str(row["funcionario"])
            idx_func = FUNC_OPTS.index(func_nome_row) if func_nome_row in FUNC_OPTS else 0

            with st.expander(f"MO #{mo_id} • {func_nome_row} • {row['data']} • {str(row['hora_inicio'])}–{str(row['hora_fim'])}", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    novo_func = st.selectbox("Funcionário", FUNC_OPTS, index=idx_func, key=f"moprev_edit_func_{mo_id}")
                with c2:
                    nova_data = st.date_input("Data", value=pd.to_datetime(str(row["data"])).date(), key=f"moprev_edit_data_{mo_id}")
                with c3:
                    novo_hi = st.time_input("Hora início", value=_as_time(row["hora_inicio"]), key=f"moprev_edit_hi_{mo_id}")
                with c4:
                    novo_hf = st.time_input("Hora fim", value=_as_time(row["hora_fim"]), key=f"moprev_edit_hf_{mo_id}")

                cA, cB = st.columns(2)
                with cA:
                    if st.button("💾 Salvar", key=f"moprev_btn_save_{mo_id}", use_container_width=True):
                        if novo_hf < novo_hi:
                            st.error("Hora fim não pode ser menor que hora início.")
                        else:
                            update_row(engine, T_MO, "id", {
                                "id": mo_id,
                                "id_funcionario": int(name2funcid.get(novo_func)),
                                "data": nova_data,
                                "hora_inicio": novo_hi,
                                "hora_fim": novo_hf
                            })
                            st.success("Apontamento atualizado.")
                            st.rerun()
                with cB:
                    if st.button("🗑️ Excluir", key=f"moprev_btn_del_{mo_id}", use_container_width=True):
                        delete_by_ids(engine, T_MO, [mo_id])
                        st.success("Apontamento excluído.")
                        st.rerun()



# =========================================
# 3) FILTROS (para a listagem)
# =========================================
with st.expander("🔎 Filtros", expanded=False):
    f_maquina = st.selectbox("Máquina", ["Todas"] + MAQ_OPTS, key="prev_f_maquina")
    f_status  = st.text_input("Status contém", key="prev_f_status")
    f_dt_ini  = st.date_input("Data inicial", value=datetime.now().date() - timedelta(days=30), key="prev_f_di")
    f_dt_fim  = st.date_input("Data final", value=datetime.now().date(), key="prev_f_df")
    page_size = st.number_input("Itens por página", 5, 200, 25, 5, key="prev_page_size")

where, params = ["WHERE 1=1"], {}
if f_maquina != "Todas" and f_maquina in name2maqid:
    where.append("AND p.id_maquina = :m"); params["m"] = name2maqid[f_maquina]
if f_status:
    where.append("AND p.status LIKE :st"); params["st"] = f"%{f_status}%"
if f_dt_ini:
    where.append("AND p.datahora_inicio >= :di"); params["di"] = datetime(f_dt_ini.year, f_dt_ini.month, f_dt_ini.day, 0, 0, 0)
if f_dt_fim:
    where.append("AND p.datahora_inicio <= :df"); params["df"] = datetime(f_dt_fim.year, f_dt_fim.month, f_dt_fim.day, 23, 59, 59)

where_sql = " " + " ".join(where)
order_sql = " ORDER BY p.datahora_inicio DESC, p.id DESC"
total = count_rows(engine, T + " p", where_sql, params)
st.caption(f"Total com filtros: **{total}**")

# =========================================
# 4) TABELA (sem checkbox de seleção)
# =========================================
page = st.number_input("Página", 1, max(1, (total - 1) // st.session_state["prev_page_size"] + 1), 1, key="prev_page")
offset = (page - 1) * st.session_state["prev_page_size"]

sql_list = f"""
    SELECT
      p.id,
      m.nome AS maquina,
      f.nome AS responsavel,
      p.datahora_inicio,
      p.datahora_fim,
      p.servico_realizado,
      p.status
    FROM {T} p
    JOIN maquinas m           ON m.id = p.id_maquina
    LEFT JOIN funcionarios f  ON f.id = p.id_funcionario
    {where_sql}{order_sql}
    LIMIT :lim OFFSET :off
"""
df_list = fetch_df(engine, sql_list, {**params, "lim": int(st.session_state["prev_page_size"]), "off": int(offset)})

st.subheader("📋 Listagem")
if df_list.empty:
    st.info("Nada encontrado com os filtros.")
else:
    st.dataframe(df_list, use_container_width=True)
    st.download_button(
        "⬇️ Exportar CSV",
        df_list.to_csv(index=False).encode("utf-8"),
        "ordens_preventiva.csv",
        "text/csv",
        use_container_width=True,
        key="prev_btn_csv"
    )
