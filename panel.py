# -*- coding: utf-8 -*-
# =========================================================================================
#                   AI_YUH - Painel de Controle (Streamlit)
# =========================================================================================
# FASE 8: O Painel de Controle
#
# Autor: Seu Nome/Apelido
# Versão: 1.0.1 (Correção do dotenv)
# Data: 26/08/2025
#
# Descrição: Uma aplicação web construída com Streamlit para gerenciar
#            todas as configurações do AI_Yuh Bot. Este painel interage
#            diretamente com o banco de dados Supabase.
#
# Para rodar: streamlit run panel.py
# =========================================================================================

import streamlit as st
import pandas as pd
from datetime import datetime

# --- CORREÇÃO: Carrega as variáveis de ambiente ANTES de qualquer outra coisa ---
from dotenv import load_dotenv
load_dotenv()
# --------------------------------------------------------------------------

# Importa o cliente supabase já configurado do nosso handler
# Isso garante que estamos usando as mesmas credenciais do bot
from database_handler import supabase_client, DB_ENABLED

# --- Configuração da Página ---
st.set_page_config(
    page_title="Painel de Controle - AI_Yuh",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# O restante do arquivo permanece EXATAMENTE O MESMO
# ... (todo o resto do seu código do painel) ...

# --- Funções de Interação com o Banco de Dados ---
# (Algumas funções são específicas para o painel para lidar com o cache do Streamlit)

@st.cache_data(ttl=60) # Cache de 1 minuto
def get_settings():
    try:
        response = supabase_client.table('settings').select("*").limit(1).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao carregar configurações: {e}")
        return None

@st.cache_data(ttl=60)
def get_users():
    try:
        response = supabase_client.table('users').select("*").order("twitch_username").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erro ao carregar usuários: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_lorebook():
    try:
        response = supabase_client.table('lorebook').select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erro ao carregar lorebook: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300) # Cache de 5 minutos
def get_long_term_memory():
    try:
        response = supabase_client.table('long_term_memory').select("*").order("created_at", desc=True).limit(100).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erro ao carregar memória de longo prazo: {e}")
        return pd.DataFrame()


# --- Interface Principal ---

st.title("🤖 Painel de Controle do AI_Yuh Bot")
st.markdown("Gerencie a personalidade, conhecimento e usuários do seu bot de IA da Twitch.")

if not DB_ENABLED:
    st.error("ERRO GRAVE: Não foi possível conectar ao banco de dados Supabase. Verifique as credenciais no arquivo .env e reinicie o painel.")
    st.stop()


# --- Abas para Organização ---
tab_dashboard, tab_settings, tab_users, tab_lorebook, tab_memory = st.tabs([
    "📊 Dashboard", "⚙️ Configurações da IA", "👥 Gerenciar Usuários", "📚 Lorebook", "🧠 Memória de Longo Prazo"
])


# --- Aba 1: Dashboard ---
with tab_dashboard:
    st.header("📊 Status Geral")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        users_df = get_users()
        st.metric("Usuários Gerenciados", len(users_df))
    
    with col2:
        lorebook_df = get_lorebook()
        st.metric("Fatos no Lorebook", len(lorebook_df))
        
    with col3:
        memory_df = get_long_term_memory()
        st.metric("Memórias Salvas", len(memory_df))
        
    st.info("Este painel lê e escreve diretamente no banco de dados do bot. As alterações podem exigir uma reinicialização do bot para terem efeito imediato.", icon="ℹ️")


# --- Aba 2: Configurações da IA ---
with tab_settings:
    st.header("⚙️ Personalidade e Modelo da IA")
    settings = get_settings()
    
    if settings:
        with st.form("settings_form"):
            personality = st.text_area("📄 Personalidade da IA", value=settings.get('personality_prompt', ''), height=200, help="Descreva em detalhes como a IA deve se comportar. Esta é a 'alma' do seu bot.")
            
            lorebook_header = st.text_area("📖 Cabeçalho do Lorebook", value=settings.get('lorebook_prompt', ''), height=100, help="O texto que a IA vê antes de ler os fatos do lorebook.")
            
            st.subheader("Configurações Avançadas")
            model = st.text_input("🤖 Modelo de Interação", value=settings.get('interaction_model', ''), help="O modelo do Gemini usado para as respostas. Ex: gemini-2.5-flash")
            
            # NOTA: A busca nativa foi removida por compatibilidade, então esta opção está desabilitada.
            # use_native_search = st.toggle("🛰️ Usar Busca Nativa do Google", value=settings.get('use_native_google_search', False), disabled=True, help="Desabilitado. O bot está usando o fallback DDGS por compatibilidade.")
            
            submitted = st.form_submit_button("Salvar Configurações", type="primary")
            if submitted:
                try:
                    supabase_client.table('settings').update({
                        'personality_prompt': personality,
                        'lorebook_prompt': lorebook_header,
                        'interaction_model': model,
                        # 'use_native_google_search': use_native_search
                    }).eq('id', settings['id']).execute()
                    st.success("Configurações salvas com sucesso! O bot aplicará na próxima reinicialização.")
                    st.cache_data.clear() # Limpa o cache para recarregar os dados
                except Exception as e:
                    st.error(f"Erro ao salvar configurações: {e}")
    else:
        st.warning("Nenhuma configuração encontrada no banco de dados.")

# --- Aba 3: Gerenciar Usuários ---
with tab_users:
    st.header("👥 Gerenciar Usuários")
    
    users_df = get_users()
    if not users_df.empty:
        st.dataframe(users_df, use_container_width=True)
    else:
        st.info("Nenhum usuário encontrado.")
        
    st.subheader("Adicionar ou Atualizar Usuário")
    with st.form("user_form"):
        username = st.text_input("Nome de Usuário (Twitch)", help="O nome de usuário exato, sem o '@'.").lower()
        permission = st.selectbox("Nível de Permissão", ["normal", "master", "blacklist"])
        
        submitted = st.form_submit_button("Salvar Usuário")
        if submitted and username:
            try:
                # Upsert: atualiza se o usuário existir, insere se não existir.
                supabase_client.table('users').upsert({
                    'twitch_username': username,
                    'permission_level': permission
                }).execute()
                st.success(f"Usuário '{username}' salvo como '{permission}'.")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erro ao salvar usuário: {e}")

# --- Aba 4: Lorebook ---
with tab_lorebook:
    st.header("📚 Lorebook (Base de Conhecimento)")
    lorebook_df = get_lorebook()
    if not lorebook_df.empty:
        st.dataframe(lorebook_df, use_container_width=True)
    else:
        st.info("Nenhum fato no Lorebook.")

    st.subheader("Adicionar Novo Fato")
    with st.form("lorebook_form"):
        entry = st.text_area("Fato a ser lembrado", height=100)
        author = st.text_input("Autor (seu nick)", value="painel_admin")
        
        submitted = st.form_submit_button("Adicionar Fato")
        if submitted and entry:
            try:
                supabase_client.table('lorebook').insert({
                    'entry': entry,
                    'created_by': author
                }).execute()
                st.success("Fato adicionado ao Lorebook!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erro ao adicionar fato: {e}")

# --- Aba 5: Memória de Longo Prazo ---
with tab_memory:
    st.header("🧠 Memória de Longo Prazo")
    st.markdown("Aqui estão os últimos 100 resumos de conversas que o bot salvou.")
    
    memory_df = get_long_term_memory()
    if not memory_df.empty:
        # Formata a data para melhor leitura
        memory_df['created_at'] = pd.to_datetime(memory_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(memory_df, use_container_width=True, height=600)
    else:
        st.info("Nenhuma memória de longo prazo foi encontrada.")