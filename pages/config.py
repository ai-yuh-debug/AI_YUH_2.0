# -*- coding: utf-8 -*-
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
from database_handler import supabase_client, DB_ENABLED

st.set_page_config(page_title="Configurações | AI_Yuh", page_icon="⚙️", layout="wide")
st.title("⚙️ Configurações Gerais da IA")

@st.cache_data(ttl=300)
def get_settings():
    try: return supabase_client.table('settings').select("*").limit(1).single().execute().data
    except: return {}

if not DB_ENABLED: st.error("Conexão com DB falhou."); st.stop()
settings = get_settings()

if settings:
    with st.form("settings_form"):
        st.subheader("🎭 Personalidade e Modelos")
        personality = st.text_area("📄 Prompt de Personalidade", settings.get('personality_prompt', ''), height=250)
        col1, col2 = st.columns(2)
        with col1: interaction_model = st.text_input("🤖 Modelo de Interação", settings.get('interaction_model', ''))
        with col2: archivist_model = st.text_input("🗄️ Modelo Arquivista", settings.get('archivist_model', ''))
        
        st.markdown("---")
        
        st.subheader("🧠 Parâmetros de Geração e Memória")
        col1, col2, col3, col4 = st.columns(4)
        with col1: temp = st.slider("🌡️ Temperatura", 0.0, 2.0, float(settings.get('temperature', 0.9)), 0.05)
        with col2: max_tokens = st.slider("📏 Máx Tokens", 64, 8192, int(settings.get('max_output_tokens', 256)), 16)
        with col3: top_p = st.number_input("🎲 Top-P", 0.0, 1.0, float(settings.get('top_p', 1.0)), 0.05)
        with col4: top_k = st.number_input("🎯 Top-K", 1, value=int(settings.get('top_k', 1)), step=1)
            
        col1, col2, col3 = st.columns(3)
        with col1: mem_exp = st.number_input("Exp. Mem. Pessoal (min)", value=int(settings.get('memory_expiration_minutes', 5)), min_value=1)
        with col2: glob_max_msg = st.number_input("Gatilho Msgs (qtd)", value=int(settings.get('global_buffer_max_messages', 40)), min_value=10)
        with col3: glob_max_min = st.number_input("Gatilho Mins (min)", value=int(settings.get('global_buffer_max_minutes', 15)), min_value=1)

        if st.form_submit_button("Salvar Todas as Configurações", type="primary", use_container_width=True):
            try:
                supabase_client.table('settings').update({
                    'interaction_model': interaction_model, 'archivist_model': archivist_model,
                    'personality_prompt': personality, 'temperature': temp, 'max_output_tokens': max_tokens,
                    'memory_expiration_minutes': mem_exp, 'global_buffer_max_messages': glob_max_msg, 'global_buffer_max_minutes': glob_max_min,
                    'top_p': top_p, 'top_k': top_k
                }).eq('id', settings['id']).execute()
                st.success("Configurações salvas com sucesso!"); st.cache_data.clear()
            except Exception as e: st.error(f"Erro: {e}")
else:
    st.warning("Nenhuma configuração encontrada no banco de dados.")