# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
from database_handler import supabase_client, DB_ENABLED

st.set_page_config(page_title="Memórias | AI_Yuh", page_icon="🧠", layout="wide")
st.title("🧠 Visualizador de Memórias")

@st.cache_data(ttl=60)
def get_memories(table_name):
    try: return pd.DataFrame(supabase_client.table(table_name).select("*").order("created_at", desc=True).limit(100).execute().data)
    except: return pd.DataFrame()

if not DB_ENABLED: st.error("Conexão com DB falhou."); st.stop()

st.subheader("🌍 Memória Global (Hierárquica)")
st.markdown("Resumos generativos sobre os acontecimentos gerais do chat.")
hier_mem_df = get_memories('hierarchical_memory')
st.dataframe(hier_mem_df, use_container_width=True)

st.markdown("---")

st.subheader("👤 Memória Pessoal (Longo Prazo)")
st.markdown("Resumos de conversas diretas entre o bot e usuários.")
memory_df = get_memories('long_term_memory')
st.dataframe(memory_df, use_container_width=True)