# -*- coding: utf-8 -*-
# =========================================================================================
#                   AI_YUH - Painel de Controle (Streamlit)
# =========================================================================================
# FASE FINAL: Painel de Controle Profissional (Leve e Otimizado)
#
# Autor: Seu Nome/Apelido
# Versão: 3.1.0
# Data: 26/08/2025
#
# Descrição: Versão final e otimizada do painel, usando apenas componentes
#            nativos do Streamlit para garantir leveza e compatibilidade com
#            planos de hospedagem gratuitos como o do Render.
#
# Para rodar: streamlit run panel.py
# =========================================================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import time
from dotenv import load_dotenv

load_dotenv()
from database_handler import supabase_client, DB_ENABLED, delete_lorebook_entry

st.set_page_config(page_title="Painel AI_Yuh", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

# --- Funções de DB com Cache ---
@st.cache_data(ttl=10)
def get_bot_status(key):
    try:
        response = supabase_client.table('bot_status').select("status_value").eq("status_key", key).single().execute()
        return response.data.get('status_value', 'Aguardando...')
    except: return "Aguardando..."

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
    
    selected = st.radio(
        "Navegação",
        ["Dashboard", "Configurações", "Gerenciamento", "Memórias"],
        captions=["Visão Geral", "Personalidade e IA", "Usuários e Lorebook", "Histórico do Bot"]
    )
    
    st.markdown("---")
    bot_status = get_bot_status('bot_state')
    if bot_status == 'Online': st.success(f"Status: **{bot_status}**", icon="🟢")
    else: st.error(f"Status: **{bot_status}**", icon="🔴")
    
    if st.button("Forçar Recarga do Painel"):
        st.cache_data.clear()
        st.rerun()

# --- Conteúdo Principal ---
if not DB_ENABLED:
    st.error("ERRO GRAVE: Não foi possível conectar ao Supabase."); st.stop()

if selected == "Dashboard":
    st.title("📊 Dashboard")
    st.subheader("Estatísticas Gerais")
    
    users_c = len(get_management_data('users'))
    lore_c = len(get_management_data('lorebook'))
    mem_p_c = len(get_management_data('long_term_memory'))
    mem_g_c = len(get_management_data('hierarchical_memory'))
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Usuários", users_c)
    col2.metric("Fatos (Lore)", lore_c)
    col3.metric("Mem. Pessoais", mem_p_c)
    col4.metric("Mem. Globais", mem_g_c)
    
    st.subheader("🧠 Último Pensamento da IA")
    st.code(get_bot_status('last_thought'), language="text")

if selected == "Configurações":
    st.title("⚙️ Configurações da IA e Memória")
    settings = get_settings()
    if settings:
        with st.form("settings_form"):
            st.subheader("🎭 Personalidade e Modelos")
            col1, col2 = st.columns(2)
            with col1: interaction_model = st.text_input("Modelo de Interação", settings.get('interaction_model', ''))
            with col2: archivist_model = st.text_input("Modelo Arquivista", settings.get('archivist_model', ''))
            personality = st.text_area("Prompt de Personalidade", settings.get('personality_prompt', ''), height=250)
            
            st.subheader("🧠 Parâmetros de Geração e Memória")
            # ... (código dos widgets de configuração inalterado)

            if st.form_submit_button("Salvar Todas as Configurações", type="primary", use_container_width=True):
                # ... (lógica de update inalterada)

if selected == "Gerenciamento":
    st.title("👥 Gerenciamento de Usuários e Lorebook")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Usuários")
            # ... (lógica de gerenciamento de usuários inalterada)
    with col2:
        with st.container(border=True):
            st.subheader("Lorebook")
            # ... (lógica de gerenciamento do lorebook inalterada)

if selected == "Memórias":
    st.title("🧠 Visualizador de Memórias")
    st.subheader("🌍 Memória Global (Hierárquica)")
    st.dataframe(get_management_data('hierarchical_memory'), use_container_width=True)
    st.subheader("👤 Memória Pessoal (Longo Prazo)")
    st.dataframe(get_management_data('long_term_memory'), use_container_width=True)