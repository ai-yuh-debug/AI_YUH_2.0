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

# --- Funções de DB ---
@st.cache_data(ttl=5)
def get_live_data(table_name, limit=50):
    try:
        response = supabase_client.table(table_name).select("*").order("created_at", desc=True).limit(limit).execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=10)
def get_bot_status(key):
    try:
        response = supabase_client.table('bot_status').select("status_value").eq("status_key", key).single().execute()
        return response.data.get('status_value', 'Aguardando...')
    except:
        return "Aguardando..."

@st.cache_data(ttl=60)
def get_management_data(table_name):
    try:
        return pd.DataFrame(supabase_client.table(table_name).select("*").order("id", desc=True).execute().data)
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar {table_name}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_settings():
    try:
        return supabase_client.table('settings').select("*").limit(1).single().execute().data
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar configs: {e}")
        return None

# --- Barra Lateral ---
with st.sidebar:
    st.title("🤖 AI_Yuh C.C.")
    st.caption("Centro de Comando")
    selected = option_menu(None, ["Dashboard", "Configurações", "Gerenciamento"],
                           icons=["speedometer2", "sliders", "people-fill"], menu_icon="cast", default_index=0)
    st.markdown("---")
    bot_status = get_bot_status('bot_state')
    if bot_status == 'Online':
        st.success(f"Status: **{bot_status}**", icon="🟢")
    else:
        st.error(f"Status: **{bot_status}**", icon="🔴")
    if st.button("Forçar Recarga do Painel"):
        st.cache_data.clear()
        st.rerun()

# --- Conteúdo Principal ---
if not DB_ENABLED:
    st.error("ERRO GRAVE: Não foi possível conectar ao Supabase."); st.stop()

if selected == "Dashboard":
    st.title("Dashboard de Atividade")
    col_main, col_side = st.columns([2, 1])

    with col_main:
        st.subheader("Linha do Tempo de Eventos")
        
        chat_df = get_live_data('live_chat')
        logs_df = get_live_data('live_logs')
        
        # --- CORREÇÃO DO KEYERROR ---
        # Garantir que os dataframes não estejam vazios antes de processar
        df_list = []
        if not chat_df.empty:
            df_list.append(chat_df.rename(columns={'message': 'event', 'username': 'source'})[['created_at', 'source', 'event']])
        if not logs_df.empty:
            df_list.append(logs_df.rename(columns={'message': 'event', 'log_type': 'source'})[['created_at', 'source', 'event']])
        
        if df_list:
            merged_df = pd.concat(df_list).sort_values(by='created_at', ascending=False)
            st.dataframe(merged_df, use_container_width=True, height=600, hide_index=True)
        else:
            st.info("Aguardando atividade do bot ou mensagens no chat...")

    with col_side:
        st.subheader("Estatísticas e Cognição")
        with st.container(border=True):
            cols = st.columns(4)
            cols[0].metric("Usuários", len(get_management_data('users')))
            cols[1].metric("Fatos", len(get_management_data('lorebook')))
            cols[2].metric("Mem. Pessoal", len(get_management_data('long_term_memory')))
            cols[3].metric("Mem. Global", len(get_management_data('hierarchical_memory')))
            
        with st.container(border=True):
            st.markdown("##### 🧠 Último Pensamento")
            last_thought = get_bot_status('last_thought')
            st.code(last_thought, language="text")
        
        with st.container(border=True):
            st.markdown("##### 💾 Últimas Memórias Geradas")
            st.caption("Memória Pessoal")
            st.dataframe(get_management_data('long_term_memory').head(3), hide_index=True, use_container_width=True)
            st.caption("Memória Global")
            st.dataframe(get_management_data('hierarchical_memory').head(3), hide_index=True, use_container_width=True)

if selected == "Configurações":
    st.title("Configurações da IA e Memória")
    settings = get_settings()
    if settings:
        with st.form("settings_form"):
            st.subheader("🎭 Personalidade e Modelos")
            col1, col2 = st.columns(2)
            with col1:
                interaction_model = st.text_input("🤖 Modelo de Interação", settings.get('interaction_model', ''))
            with col2:
                archivist_model = st.text_input("🗄️ Modelo Arquivista", settings.get('archivist_model', ''))
            personality = st.text_area("📄 Prompt de Personalidade", settings.get('personality_prompt', ''), height=250)
            
            st.subheader("🧠 Parâmetros de Geração e Memória")
            col1, col2, col3 = st.columns(3)
            with col1:
                temp = st.slider("🌡️ Temperatura", 0.0, 2.0, float(settings.get('temperature', 0.9)), 0.05)
                max_tokens = st.slider("📏 Máx Tokens", 64, 2048, int(settings.get('max_output_tokens', 256)), 16)
            with col2:
                top_p = st.number_input("🎲 Top-P", 0.0, 1.0, float(settings.get('top_p', 1.0)), 0.05)
                top_k = st.number_input("🎯 Top-K", 1, value=int(settings.get('top_k', 1)), step=1)
            with col3:
                mem_exp = st.number_input("Exp. Mem. Pessoal (min)", value=int(settings.get('memory_expiration_minutes', 5)), min_value=1)
                glob_max_msg = st.number_input("Gatilho Msgs (qtd)", value=int(settings.get('global_buffer_max_messages', 40)), min_value=10)

            if st.form_submit_button("Salvar Todas as Configurações", type="primary", use_container_width=True):
                try:
                    # ... (lógica de update)
                    st.success("Configurações salvas!"); st.cache_data.clear()
                except Exception as e: st.error(f"Erro: {e}")

if selected == "Gerenciamento":
    st.title("Gerenciamento de Usuários e Lorebook")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("👥 Usuários")
            users_df = get_management_data('users')
            st.dataframe(users_df, use_container_width=True)
            with st.form("user_form", clear_on_submit=True):
                username = st.text_input("Nome de Usuário").lower()
                permission = st.selectbox("Nível de Permissão", ["master", "blacklist", "normal"])
                if st.form_submit_button("Salvar Usuário", use_container_width=True):
                    # ... (lógica de upsert)
    with col2:
        with st.container(border=True):
            st.subheader("📚 Lorebook")
            lorebook_df = get_management_data('lorebook')
            st.dataframe(lorebook_df, use_container_width=True, height=300)
            with st.form("lorebook_form", clear_on_submit=True):
                entry = st.text_area("Novo Fato", height=100)
                if st.form_submit_button("Adicionar Fato", use_container_width=True):
                    # ... (lógica de insert)

# Atualização automática
time.sleep(5)
st.rerun()