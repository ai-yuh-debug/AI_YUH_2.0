# -*- coding: utf-8 -*-
# =========================================================================================
#                   AI_YUH - Painel de Controle (Streamlit)
# =========================================================================================
# FASE FINAL: Painel de Controle Profissional
#
# Autor: Seu Nome/Apelido
# Versão: 2.0.0
# Data: 26/08/2025
#
# Descrição: Uma aplicação web completa para gerenciar todas as facetas do
#            AI_Yuh Bot, usando um layout de expanders para melhor organização.
#
# Para rodar: streamlit run panel.py
# =========================================================================================

import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
from database_handler import supabase_client, DB_ENABLED, delete_lorebook_entry

# --- Configuração da Página ---
st.set_page_config(page_title="Painel AI_Yuh", page_icon="🤖", layout="wide")

# --- Funções de DB com Cache ---
@st.cache_data(ttl=10) # Cache baixo para status
def get_bot_status():
    try:
        response = supabase_client.table('bot_status').select("status_value").eq("status_key", "bot_state").single().execute()
        return response.data.get('status_value', 'Desconhecido')
    except Exception: return "Desconhecido"

@st.cache_data(ttl=60)
def get_settings():
    try: return supabase_client.table('settings').select("*").limit(1).single().execute().data
    except Exception as e: st.error(f"Erro ao carregar configs: {e}"); return None

@st.cache_data(ttl=60)
def get_users():
    try: return pd.DataFrame(supabase_client.table('users').select("*").order("twitch_username").execute().data)
    except Exception as e: st.error(f"Erro ao carregar usuários: {e}"); return pd.DataFrame()

@st.cache_data(ttl=60)
def get_lorebook():
    try: return pd.DataFrame(supabase_client.table('lorebook').select("*").order("created_at", desc=True).execute().data)
    except Exception as e: st.error(f"Erro ao carregar lorebook: {e}"); return pd.DataFrame()

@st.cache_data(ttl=300)
def get_long_term_memory():
    try: return pd.DataFrame(supabase_client.table('long_term_memory').select("*").order("created_at", desc=True).limit(100).execute().data)
    except Exception as e: st.error(f"Erro ao carregar memória pessoal: {e}"); return pd.DataFrame()
    
@st.cache_data(ttl=300)
def get_hierarchical_memory():
    try: return pd.DataFrame(supabase_client.table('hierarchical_memory').select("*").order("created_at", desc=True).limit(100).execute().data)
    except Exception as e: st.error(f"Erro ao carregar memória hierárquica: {e}"); return pd.DataFrame()


# --- Interface Principal ---
st.title("🤖 Painel de Controle do AI_Yuh Bot")

if not DB_ENABLED:
    st.error("ERRO GRAVE: Não foi possível conectar ao Supabase. Verifique o arquivo .env."); st.stop()

# --- Seção de Atividade ao Vivo e Status ---
with st.container(border=True):
    st.subheader("Atividade ao Vivo e Status")
    bot_status = get_bot_status()
    status_color = {"Online": "green", "Offline": "red"}.get(bot_status, "gray")
    st.markdown(f"Status do Bot: <span style='color:{status_color}; font-weight:bold;'>{bot_status}</span>", unsafe_allow_html=True)
    st.text_area("Chat da Twitch ao Vivo", "Recurso de chat ao vivo ainda não implementado...", height=200, disabled=True)

# --- Seções de Configuração com Expanders ---
settings = get_settings()
if settings:
    with st.expander("⚙️ Configurações Gerais da IA"):
        with st.form("general_settings_form"):
            st.subheader("Personalidade e Modelo")
            personality = st.text_area("📄 Personalidade", settings.get('personality_prompt', ''), height=200)
            lorebook_header = st.text_area("📖 Cabeçalho do Lorebook", settings.get('lorebook_prompt', ''), height=100)
            
            col1_model, col2_model = st.columns(2)
            with col1_model: interaction_model = st.text_input("🤖 Modelo de Interação", settings.get('interaction_model', ''))
            with col2_model: archivist_model = st.text_input("🗄️ Modelo Arquivista", settings.get('archivist_model', ''))
            
            st.subheader("Parâmetros de Geração")
            col1, col2 = st.columns(2)
            with col1:
                temp = st.slider("🌡️ Temperatura", 0.0, 1.0, float(settings.get('temperature', 0.9)), 0.05)
                max_tokens = st.slider("📏 Máx Tokens", 64, 1024, int(settings.get('max_output_tokens', 256)), 16)
            with col2:
                top_p = st.number_input("🎲 Top-P", 0.0, 1.0, float(settings.get('top_p', 1.0)), 0.05)
                top_k = st.number_input("🎯 Top-K", 1, value=int(settings.get('top_k', 1)), step=1)

            if st.form_submit_button("Salvar Configurações Gerais", type="primary"):
                try:
                    supabase_client.table('settings').update({
                        'personality_prompt': personality, 'lorebook_prompt': lorebook_header,
                        'interaction_model': interaction_model, 'archivist_model': archivist_model,
                        'temperature': temp, 'top_p': top_p, 'top_k': top_k, 'max_output_tokens': max_tokens
                    }).eq('id', settings['id']).execute()
                    st.success("Configurações Gerais salvas!"); st.cache_data.clear()
                except Exception as e: st.error(f"Erro: {e}")

    with st.expander("🧠 Configurações de Memória Generativa"):
        with st.form("memory_form"):
            col1, col2 = st.columns(2)
            with col1:
                mem_exp = st.number_input("Expiração da Memória Pessoal (minutos)", value=int(settings.get('memory_expiration_minutes', 5)), min_value=1)
            with col2:
                glob_max_msg = st.number_input("Gatilho de Sumarização (mensagens)", value=int(settings.get('global_buffer_max_messages', 40)), min_value=10)
                glob_max_min = st.number_input("Gatilho de Sumarização (minutos)", value=int(settings.get('global_buffer_max_minutes', 15)), min_value=1)
            if st.form_submit_button("Salvar Configurações de Memória"):
                try:
                    supabase_client.table('settings').update({'memory_expiration_minutes': mem_exp, 'global_buffer_max_messages': glob_max_msg, 'global_buffer_max_minutes': glob_max_min}).eq('id', settings['id']).execute()
                    st.success("Configurações de Memória salvas!"); st.cache_data.clear()
                except Exception as e: st.error(f"Erro: {e}")

with st.expander("👥 Gerenciar Usuários"):
    users_df = get_users()
    if not users_df.empty: st.dataframe(users_df, use_container_width=True)
    else: st.info("Nenhum usuário encontrado.")
    st.subheader("Adicionar ou Atualizar Usuário")
    with st.form("user_form", clear_on_submit=True):
        username = st.text_input("Nome de Usuário (Twitch)").lower()
        permission = st.selectbox("Nível de Permissão", ["normal", "master", "blacklist"])
        if st.form_submit_button("Salvar Usuário"):
            if username:
                try:
                    supabase_client.table('users').upsert({'twitch_username': username, 'permission_level': permission}).execute()
                    st.success(f"Usuário '{username}' salvo como '{permission}'."); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"Erro ao salvar usuário: {e}")
            else:
                st.warning("O nome de usuário não pode estar vazio.")

with st.expander("📚 Gerenciar Lorebook", expanded=True):
    lorebook_df = get_lorebook()
    if not lorebook_df.empty:
        lorebook_df['delete'] = False
        edited_df = st.data_editor(lorebook_df, column_config={"delete": st.column_config.CheckboxColumn("Apagar?", default=False)}, use_container_width=True, hide_index=True)
        if st.button("Deletar Entradas Selecionadas", type="primary"):
            entries_to_delete = edited_df[edited_df['delete']]
            if not entries_to_delete.empty:
                for entry_id in entries_to_delete['id']:
                    delete_lorebook_entry(entry_id)
                st.success(f"{len(entries_to_delete)} entrada(s) deletada(s)!"); st.cache_data.clear(); st.rerun()
            else:
                st.warning("Nenhuma entrada selecionada para deletar.")
    else:
        st.info("Nenhum fato no Lorebook.")
    st.subheader("Adicionar Novo Fato")
    with st.form("lorebook_form", clear_on_submit=True):
        entry = st.text_area("Fato a ser lembrado", height=100)
        author = st.text_input("Autor", value="painel_admin")
        if st.form_submit_button("Adicionar Fato"):
            if entry:
                try:
                    supabase_client.table('lorebook').insert({'entry': entry, 'created_by': author}).execute()
                    st.success("Fato adicionado!"); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"Erro ao adicionar fato: {e}")
            else:
                st.warning("O fato não pode estar vazio.")

with st.expander("🧠 Visualizar Memória Pessoal"):
    st.markdown("Resumos de conversas diretas entre o bot e usuários.")
    memory_df = get_long_term_memory()
    if not memory_df.empty:
        memory_df['created_at'] = pd.to_datetime(memory_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(memory_df, use_container_width=True, height=600)
    else: st.info("Nenhuma memória pessoal encontrada.")

with st.expander("🌍 Visualizar Memória Global"):
    st.markdown("Resumos generativos sobre os acontecimentos do chat.")
    hier_mem_df = get_hierarchical_memory()
    if not hier_mem_df.empty:
        hier_mem_df['created_at'] = pd.to_datetime(hier_mem_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(hier_mem_df, use_container_width=True, height=600)
    else: st.info("Nenhuma memória hierárquica encontrada.")