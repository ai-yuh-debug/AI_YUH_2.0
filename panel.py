# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
import time
from dotenv import load_dotenv
from streamlit_option_menu import option_menu

load_dotenv()
from database_handler import supabase_client, DB_ENABLED, delete_lorebook_entry

st.set_page_config(page_title="Painel AI_Yuh", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

# --- Funções de DB com Cache ---
@st.cache_data(ttl=5)
def get_bot_status(key):
    try:
        response = supabase_client.table('bot_status').select("status_value").eq("status_key", key).single().execute()
        return response.data.get('status_value', 'Aguardando...')
    except: return "Aguardando..."

@st.cache_data(ttl=5)
def get_live_data(table_name, limit):
    try: return pd.DataFrame(supabase_client.table(table_name).select("*").order("created_at", desc=True).limit(limit).execute().data)
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def get_management_data(table_name):
    try: return pd.DataFrame(supabase_client.table(table_name).select("*").order("id", desc=True).execute().data)
    except Exception as e: st.sidebar.error(f"Erro ao carregar {table_name}: {e}"); return pd.DataFrame()

@st.cache_data(ttl=60)
def get_settings():
    try: return supabase_client.table('settings').select("*").limit(1).single().execute().data
    except Exception as e: st.sidebar.error(f"Erro ao carregar configs: {e}"); return None

# --- Barra Lateral ---
with st.sidebar:
    st.title("🤖 AI_Yuh C.C.")
    st.caption("Centro de Comando")
    selected = option_menu(None, ["Dashboard", "Configurações", "Gerenciamento"], icons=["bi-grid-1x2-fill", "bi-sliders", "bi-people-fill"], default_index=0)
    st.markdown("---")
    bot_status = get_bot_status('bot_state')
    if bot_status == 'Online': st.success(f"Status: **{bot_status}**", icon="🟢")
    else: st.error(f"Status: **{bot_status}**", icon="🔴")
    if st.button("Forçar Recarga"): st.cache_data.clear(); st.rerun()

# --- Conteúdo Principal ---
if not DB_ENABLED: st.error("ERRO GRAVE: Não foi possível conectar ao Supabase."); st.stop()

if selected == "Dashboard":
    st.header("Visão Geral e Atividade ao Vivo")
    col_main, col_side = st.columns([2, 1.2])
    
    with col_main:
        st.subheader("Linha do Tempo de Eventos")
        chat_df = get_live_data('live_chat', 50)
        logs_df = get_live_data('live_logs', 20)
        
        merged_df = pd.concat([
            chat_df.rename(columns={'message': 'event', 'username': 'source'})[['created_at', 'source', 'event']],
            logs_df.rename(columns={'message': 'event', 'log_type': 'source'})[['created_at', 'source', 'event']]
        ]).sort_values(by='created_at', ascending=False)
        
        st.dataframe(merged_df, use_container_width=True, height=600, hide_index=True)

    with col_side:
        st.subheader("Processo Cognitivo")
        with st.container(border=True):
            st.markdown("##### 🧠 Pensamento em Tempo Real")
            last_thought = get_bot_status('last_thought')
            st.code(last_thought, language="text")
        
        with st.container(border=True):
            st.markdown("##### 💾 Últimas Memórias Geradas")
            st.caption("Memória Pessoal")
            st.dataframe(get_management_data('long_term_memory').head(3), hide_index=True)
            st.caption("Memória Global")
            st.dataframe(get_management_data('hierarchical_memory').head(3), hide_index=True)

if selected == "Configurações":
    st.header("Configurações da IA e Memória")
    settings = get_settings()
    if settings:
        with st.form("settings_form"):
            st.subheader("Personalidade e Modelos")
            personality = st.text_area("📄 Prompt de Personalidade", settings.get('personality_prompt', ''), height=250)
            col1_model, col2_model = st.columns(2)
            with col1_model: interaction_model = st.text_input("🤖 Modelo de Interação", settings.get('interaction_model', ''))
            with col2_model: archivist_model = st.text_input("🗄️ Modelo Arquivista", settings.get('archivist_model', ''))
            
            st.subheader("Parâmetros de Geração e Memória")
            col1, col2, col3 = st.columns(3)
            with col1:
                temp = st.slider("🌡️ Temperatura", 0.0, 1.0, float(settings.get('temperature', 0.9)), 0.05)
                max_tokens = st.slider("📏 Máx Tokens", 64, 2048, int(settings.get('max_output_tokens', 256)), 16)
            with col2:
                mem_exp = st.number_input("Expiração Mem. Pessoal (min)", value=int(settings.get('memory_expiration_minutes', 5)), min_value=1)
                glob_max_msg = st.number_input("Gatilho Sumarização (msgs)", value=int(settings.get('global_buffer_max_messages', 40)), min_value=10)
            with col3:
                top_p = st.number_input("🎲 Top-P", 0.0, 1.0, float(settings.get('top_p', 1.0)), 0.05)
                top_k = st.number_input("🎯 Top-K", 1, value=int(settings.get('top_k', 1)), step=1)

            if st.form_submit_button("Salvar Todas as Configurações", type="primary", use_container_width=True):
                try:
                    supabase_client.table('settings').update({
                        'personality_prompt': personality,
                        'interaction_model': interaction_model, 'archivist_model': archivist_model,
                        'temperature': temp, 'max_output_tokens': max_tokens,
                        'memory_expiration_minutes': mem_exp, 'global_buffer_max_messages': glob_max_msg,
                        'top_p': top_p, 'top_k': top_k
                    }).eq('id', settings['id']).execute()
                    st.success("Configurações salvas com sucesso!"); st.cache_data.clear()
                except Exception as e: st.error(f"Erro: {e}")

if selected == "Gerenciamento":
    st.header("Gerenciamento de Usuários e Lorebook")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👥 Gerenciar Usuários")
        users_df = get_management_data('users')
        if not users_df.empty: st.dataframe(users_df, use_container_width=True)
        with st.form("user_form", clear_on_submit=True):
            username = st.text_input("Nome de Usuário (Twitch)").lower()
            permission = st.selectbox("Nível de Permissão", ["master", "blacklist", "normal"])
            if st.form_submit_button("Salvar Usuário", use_container_width=True):
                if username:
                    try:
                        supabase_client.table('users').upsert({'twitch_username': username, 'permission_level': permission}).execute()
                        st.success(f"Usuário '{username}' salvo."); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro ao salvar: {e}")
    with col2:
        st.subheader("📚 Gerenciar Lorebook")
        lorebook_df = get_management_data('lorebook')
        if not lorebook_df.empty:
            lorebook_df['delete'] = False
            edited_df = st.data_editor(lorebook_df, column_config={"delete": st.column_config.CheckboxColumn("Apagar?", default=False)}, use_container_width=True, hide_index=True)
            if st.button("Deletar Entradas Selecionadas", type="primary", use_container_width=True):
                entries_to_delete = edited_df[edited_df['delete']]
                if not entries_to_delete.empty:
                    for entry_id in entries_to_delete['id']: delete_lorebook_entry(entry_id)
                    st.success(f"{len(entries_to_delete)} entrada(s) deletada(s)!"); st.cache_data.clear(); st.rerun()
        with st.form("lorebook_form", clear_on_submit=True):
            entry = st.text_area("Fato a ser lembrado", height=100)
            if st.form_submit_button("Adicionar Fato", use_container_width=True):
                if entry:
                    try:
                        supabase_client.table('lorebook').insert({'entry': entry, 'created_by': 'painel_admin'}).execute()
                        st.success("Fato adicionado!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro ao adicionar: {e}")

# Atualização automática
time.sleep(5)
st.rerun()