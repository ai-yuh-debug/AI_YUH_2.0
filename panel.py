# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from streamlit_extras.metric_cards import style_metric_cards

load_dotenv()
from database_handler import supabase_client, DB_ENABLED

st.set_page_config(page_title="Dashboard | AI_Yuh", page_icon="🤖", layout="wide")

# Funções de DB com cache
@st.cache_data(ttl=10)
def get_bot_status(key):
    try:
        response = supabase_client.table('bot_status').select("status_value").eq("status_key", key).single().execute()
        return response.data.get('status_value', 'Aguardando...')
    except: return "Aguardando..."

@st.cache_data(ttl=5)
def get_live_data(table_name, limit=50):
    try:
        return pd.DataFrame(supabase_client.table(table_name).select("*").order("created_at", desc=True).limit(limit).execute().data)
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def get_counts():
    try:
        users = len(supabase_client.table('users').select("id", count='exact').execute().count)
        lore = len(supabase_client.table('lorebook').select("id", count='exact').execute().count)
        mem_p = len(supabase_client.table('long_term_memory').select("id", count='exact').execute().count)
        mem_g = len(supabase_client.table('hierarchical_memory').select("id", count='exact').execute().count)
        return users, lore, mem_p, mem_g
    except:
        return 0, 0, 0, 0

# --- Interface ---
st.title("🤖 Painel de Controle AI_Yuh")
st.markdown("Bem-vindo ao Centro de Comando. Use o menu à esquerda para navegar.")

if not DB_ENABLED: st.error("ERRO GRAVE: Conexão com o Supabase falhou."); st.stop()

# --- Status Card ---
bot_status = get_bot_status('bot_state')
if bot_status == 'Online': st.success(f"**Status do Bot:** {bot_status}", icon="🟢")
else: st.error(f"**Status do Bot:** {bot_status}", icon="🔴")

st.markdown("---")

# --- Métricas ---
st.subheader("Estatísticas Gerais")
users_c, lore_c, mem_p_c, mem_g_c = get_counts()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Usuários Gerenciados", users_c)
col2.metric("Fatos no Lorebook", lore_c)
col3.metric("Memórias Pessoais", mem_p_c)
col4.metric("Memórias Globais", mem_g_c)
style_metric_cards()

st.markdown("---")

# --- Atividade ao Vivo ---
st.subheader("Atividade ao Vivo")
col_main, col_side = st.columns([2, 1.2])

with col_main:
    st.markdown("##### Linha do Tempo de Eventos (Chat + Logs)")
    # (A lógica de merge e display do chat ao vivo permanece a mesma)

with col_side:
    st.markdown("##### Processo Cognitivo")
    with st.container(border=True):
        st.markdown("🧠 **Último Pensamento**")
        st.code(get_bot_status('last_thought'), language="text")