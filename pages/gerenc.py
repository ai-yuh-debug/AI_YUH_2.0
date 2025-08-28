# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
from database_handler import supabase_client, DB_ENABLED, delete_lorebook_entry

st.set_page_config(page_title="Gerenciamento | AI_Yuh", page_icon="👥", layout="wide")
st.title("👥 Gerenciamento de Usuários e Lorebook")

@st.cache_data(ttl=60)
def get_management_data(table_name):
    try: return pd.DataFrame(supabase_client.table(table_name).select("*").order("id", desc=True).execute().data)
    except: return pd.DataFrame()

if not DB_ENABLED: st.error("Conexão com DB falhou."); st.stop()

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.subheader("Gerenciar Usuários")
        users_df = get_management_data('users')
        st.dataframe(users_df, use_container_width=True, hide_index=True)
        with st.form("user_form", clear_on_submit=True):
            username = st.text_input("Nome de Usuário").lower()
            permission = st.selectbox("Nível de Permissão", ["master", "blacklist", "normal"])
            if st.form_submit_button("Salvar Usuário", use_container_width=True):
                if username:
                    try:
                        supabase_client.table('users').upsert({'twitch_username': username, 'permission_level': permission}).execute()
                        st.success(f"Usuário '{username}' salvo."); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro ao salvar: {e}")

with col2:
    with st.container(border=True):
        st.subheader("Gerenciar Lorebook")
        lorebook_df = get_management_data('lorebook')
        if not lorebook_df.empty:
            lorebook_df['delete'] = False
            edited_df = st.data_editor(lorebook_df, column_config={"delete": st.column_config.CheckboxColumn("Apagar?", default=False)}, use_container_width=True, height=300, hide_index=True)
            if st.button("Deletar Selecionadas", type="primary", use_container_width=True):
                entries_to_delete = edited_df[edited_df['delete']]
                if not entries_to_delete.empty:
                    for entry_id in entries_to_delete['id']: delete_lorebook_entry(entry_id)
                    st.success(f"{len(entries_to_delete)} entrada(s) deletada(s)!"); st.cache_data.clear(); st.rerun()
        
        with st.form("lorebook_form", clear_on_submit=True):
            entry = st.text_area("Novo Fato", height=100)
            if st.form_submit_button("Adicionar Fato", use_container_width=True):
                if entry:
                    try:
                        supabase_client.table('lorebook').insert({'entry': entry, 'created_by': 'painel_admin'}).execute()
                        st.success("Fato adicionado!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro ao adicionar: {e}")