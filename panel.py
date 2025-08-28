# -*- coding: utf-8 -*-
# =========================================================================================
#                   AI_YUH - Painel de Controle (Streamlit)
# =========================================================================================
# FASE FINAL: Painel de Controle Profissional (UI/UX Rework)
#
# Autor: Seu Nome/Apelido
# Versão: 3.0.0
# Data: 26/08/2025
#
# Descrição: Uma refatoração completa da interface do painel para um design
#            mais profissional, limpo e intuitivo, usando uma barra lateral
#            para navegação e uma estrutura de containers para organização.
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

# --- Configuração da Página ---
st.set_page_config(page_title="Painel AI_Yuh", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

# --- Estilo CSS Customizado (Opcional, mas melhora a aparência) ---
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
    }
    .st-emotion-cache-16txtl3 {
        padding-top: 2rem;
    }
    h1, h2, h3 {
        color: #FAFAFA;
    }
</style>
""", unsafe_allow_html=True)

# --- Funções de DB com Cache ---
@st.cache_data(ttl=10)
def get_bot_status():
    try:
        response = supabase_client.table('bot_status').select("status_value").eq("status_key", "bot_state").single().execute()
        return response.data.get('status_value', 'Desconhecido')
    except: return "Desconhecido"

@st.cache_data(ttl=60)
def get_settings():
    try: return supabase_client.table('settings').select("*").limit(1).single().execute().data
    except Exception as e: st.sidebar.error(f"Erro ao carregar configs: {e}"); return None

@st.cache_data(ttl=60)
def get_users():
    try: return pd.DataFrame(supabase_client.table('users').select("*").order("twitch_username").execute().data)
    except Exception as e: st.sidebar.error(f"Erro ao carregar usuários: {e}"); return pd.DataFrame()

@st.cache_data(ttl=60)
def get_lorebook():
    try: return pd.DataFrame(supabase_client.table('lorebook').select("*").order("id", desc=True).execute().data)
    except Exception as e: st.sidebar.error(f"Erro ao carregar lorebook: {e}"); return pd.DataFrame()

@st.cache_data(ttl=300)
def get_memories(table_name):
    try: return pd.DataFrame(supabase_client.table(table_name).select("*").order("created_at", desc=True).limit(100).execute().data)
    except Exception as e: st.sidebar.error(f"Erro ao carregar memórias de {table_name}: {e}"); return pd.DataFrame()


# --- Barra Lateral (Sidebar) para Navegação ---
with st.sidebar:
    st.title("🤖 AI_Yuh")
    st.markdown("---")
    
    bot_status = get_bot_status()
    if bot_status == 'Online':
        st.success(f"Status: **{bot_status}**", icon="🟢")
    elif bot_status == 'Offline':
        st.error(f"Status: **{bot_status}**", icon="🔴")
    else:
        st.warning(f"Status: **{bot_status}**", icon="⚪")
    
    st.markdown("---")
    
    page = st.radio("Navegação", 
                    ["Dashboard", "Configurações", "Gerenciar Usuários", "Gerenciar Lorebook", "Visualizar Memórias"])
    
    st.markdown("---")
    if st.button("Forçar Recarga do Painel"):
        st.cache_data.clear()
        st.rerun()

    st.info("Painel v3.0.0")


# --- Conteúdo Principal ---
st.header(page)

if not DB_ENABLED:
    st.error("ERRO GRAVE: Não foi possível conectar ao Supabase. Verifique o arquivo .env."); st.stop()

# --- Página 1: Dashboard ---
if page == "Dashboard":
    st.subheader("Atividade Recente e Estatísticas")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Usuários Gerenciados", len(get_users()))
    with col2: st.metric("Fatos no Lorebook", len(get_lorebook()))
    with col3: st.metric("Memórias Pessoais", len(get_memories('long_term_memory')))
    with col4: st.metric("Memórias Globais", len(get_memories('hierarchical_memory')))
    
    st.subheader("Log de Atividade do Bot (Últimas 20 Ações)")
    # (Implementação do Log ao Vivo da Fase anterior)

# --- Página 2: Configurações ---
if page == "Configurações":
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
                        'interaction_model': interaction_model, 'archivist_model': archivist_model,
                        'personality_prompt': personality, 'temperature': temp, 'max_output_tokens': max_tokens,
                        'memory_expiration_minutes': mem_exp, 'global_buffer_max_messages': glob_max_msg,
                        'top_p': top_p, 'top_k': top_k
                    }).eq('id', settings['id']).execute()
                    st.success("Configurações salvas com sucesso!"); st.cache_data.clear()
                except Exception as e: st.error(f"Erro: {e}")
    else:
        st.warning("Nenhuma configuração encontrada no banco de dados.")

# --- Página 3: Gerenciar Usuários ---
if page == "Gerenciar Usuários":
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Lista de Usuários")
        users_df = get_users()
        if not users_df.empty: st.dataframe(users_df, use_container_width=True)
        else: st.info("Nenhum usuário com permissões especiais encontrado.")
    with col2:
        st.subheader("Adicionar ou Atualizar")
        with st.form("user_form", clear_on_submit=True):
            username = st.text_input("Nome de Usuário (Twitch)").lower()
            permission = st.selectbox("Nível de Permissão", ["master", "blacklist", "normal"])
            if st.form_submit_button("Salvar Usuário", use_container_width=True):
                if username:
                    try:
                        supabase_client.table('users').upsert({'twitch_username': username, 'permission_level': permission}).execute()
                        st.success(f"Usuário '{username}' salvo."); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro ao salvar: {e}")
                else: st.warning("O nome de usuário é obrigatório.")

# --- Página 4: Gerenciar Lorebook ---
if page == "Gerenciar Lorebook":
    st.subheader("Adicionar Novo Fato")
    with st.form("lorebook_form", clear_on_submit=True):
        entry = st.text_area("Fato a ser lembrado", height=100)
        if st.form_submit_button("Adicionar Fato", use_container_width=True):
            if entry:
                try:
                    supabase_client.table('lorebook').insert({'entry': entry, 'created_by': 'painel_admin'}).execute()
                    st.success("Fato adicionado!"); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"Erro ao adicionar: {e}")
            else: st.warning("O fato não pode estar vazio.")
            
    st.subheader("Base de Conhecimento Atual")
    lorebook_df = get_lorebook()
    if not lorebook_df.empty:
        lorebook_df['delete'] = False
        edited_df = st.data_editor(lorebook_df, column_config={"delete": st.column_config.CheckboxColumn("Apagar?", default=False)}, use_container_width=True, hide_index=True)
        if st.button("Deletar Entradas Selecionadas", type="primary", use_container_width=True):
            entries_to_delete = edited_df[edited_df['delete']]
            if not entries_to_delete.empty:
                for entry_id in entries_to_delete['id']: delete_lorebook_entry(entry_id)
                st.success(f"{len(entries_to_delete)} entrada(s) deletada(s)!"); st.cache_data.clear(); st.rerun()
            else: st.warning("Nenhuma entrada selecionada.")
    else:
        st.info("Nenhum fato no Lorebook.")

# --- Página 5: Visualizar Memórias ---
if page == "Visualizar Memórias":
    st.subheader("🧠 Memória Pessoal")
    st.markdown("Resumos de conversas diretas entre o bot e usuários.")
    memory_df = get_memories('long_term_memory')
    if not memory_df.empty:
        memory_df['created_at'] = pd.to_datetime(memory_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(memory_df, use_container_width=True, height=300)
    else: st.info("Nenhuma memória pessoal encontrada.")

    st.subheader("🌍 Memória Global")
    st.markdown("Resumos generativos sobre os acontecimentos do chat.")
    hier_mem_df = get_memories('hierarchical_memory')
    if not hier_mem_df.empty:
        hier_mem_df['created_at'] = pd.to_datetime(hier_mem_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(hier_mem_df, use_container_width=True, height=300)
    else: st.info("Nenhuma memória hierárquica encontrada.")