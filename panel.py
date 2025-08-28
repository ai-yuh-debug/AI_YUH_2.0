# panel.py

import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv

# --- Configuração da Página e Conexão com Supabase ---
st.set_page_config(
    page_title="Painel de Controle - AI YUH",
    page_icon="🤖",
    layout="wide",
)

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@st.cache_resource
def init_supabase_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Erro ao conectar com Supabase: {e}")
        return None

supabase = init_supabase_connection()
if not supabase:
    st.error("A conexão com o Supabase falhou. Verifique as credenciais no .env.")
    st.stop()

# --- Funções de Lógica do Painel ---
def fetch_data(table_name):
    """Função genérica para buscar todos os dados de uma tabela."""
    try:
        response = supabase.table(table_name).select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao buscar dados da tabela {table_name}: {e}")
        return []

def upsert_setting(key, value):
    """Insere ou atualiza uma configuração na tabela 'settings'."""
    try:
        supabase.table("settings").upsert({"key": key, "value": value}).execute()
        st.success(f"Configuração '{key}' atualizada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao atualizar configuração '{key}': {e}")

def manage_user(username, role, action):
    """Adiciona ou remove um usuário da tabela 'users'."""
    try:
        username = username.lower().strip()
        if not username:
            st.warning("O nome de usuário não pode estar vazio.")
            return
        if action == "add":
            supabase.table("users").upsert({"username": username, "role": role}).execute()
            st.success(f"Usuário '{username}' adicionado à lista de '{role}'.")
        elif action == "remove":
            supabase.table("users").delete().match({"username": username, "role": role}).execute()
            st.success(f"Usuário '{username}' removido da lista de '{role}'.")
    except Exception as e:
        st.error(f"Erro ao gerenciar usuário '{username}': {e}")

# --- Layout da Interface ---
st.title("🤖 Painel de Controle da AI YUH")
st.sidebar.title("Navegação")
page = st.sidebar.radio("Selecione uma página", ["Dashboard", "Gerenciador de Memória", "Gerenciador de Usuários", "Configurações da IA"])

# --- Página: Dashboard ---
if page == "Dashboard":
    st.header("📊 Dashboard")
    st.markdown("Visão geral do status e atividade recente do bot.")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        try:
            mem_count_result = supabase.table("memories").select('id', count='exact').execute()
            st.metric("Total de Memórias", mem_count_result.count)
        except Exception as e:
            st.metric("Total de Memórias", f"Erro: {e}")
    
    with col2:
        try:
            master_count_result = supabase.table("users").select('username', count='exact').eq('role', 'master').execute()
            st.metric("Usuários Mestres", master_count_result.count)
        except Exception as e:
            st.metric("Usuários Mestres", f"Erro: {e}")

    with col3:
        try:
            blacklist_count_result = supabase.table("users").select('username', count='exact').eq('role', 'blacklisted').execute()
            st.metric("Usuários na Blacklist", blacklist_count_result.count)
        except Exception as e:
            st.metric("Usuários na Blacklist", f"Erro: {e}")

    st.subheader("Últimas Memórias Horárias Registradas")
    try:
        recent_memories = supabase.table("memories").select("*").eq("level", "hourly").order("created_at", desc=True).limit(5).execute().data
        if recent_memories:
            for mem in recent_memories:
                with st.expander(f"**{mem['start_date']}** - Nível: {mem['level']}"):
                    st.write(mem['content'])
        else:
            st.info("Nenhuma memória horária encontrada.")
    except Exception as e:
        st.error(f"Não foi possível carregar as memórias recentes: {e}")

# --- Página: Gerenciador de Memória ---
elif page == "Gerenciador de Memória":
    st.header("🧠 Gerenciador de Memória")
    
    levels = ["hourly", "daily", "weekly", "monthly", "yearly"]
    selected_level = st.selectbox("Filtrar por nível de memória", options=levels)
    
    search_term = st.text_input("Buscar por palavra-chave no conteúdo")
    
    try:
        query = supabase.table("memories").select("*").eq("level", selected_level)
        if search_term:
            query = query.ilike("content", f"%{search_term}%")
            
        memories = query.order("start_date", desc=True).execute().data
        
        if not memories:
            st.warning(f"Nenhuma memória encontrada para o nível '{selected_level}' com os filtros aplicados.")
        else:
            st.info(f"Exibindo {len(memories)} memórias.")
            for mem in memories:
                with st.expander(f"ID: {mem['id']} | Período: {mem['start_date']} a {mem['end_date']}"):
                    edited_content = st.text_area("Conteúdo", value=mem['content'], height=150, key=f"text_{mem['id']}")
                    
                    col1, col2 = st.columns([1, 6])
                    with col1:
                        if st.button("Salvar Alterações", key=f"save_{mem['id']}"):
                            supabase.table("memories").update({"content": edited_content}).eq("id", mem['id']).execute()
                            st.success(f"Memória {mem['id']} atualizada!")
                            st.rerun()
                    with col2:
                        if st.button("Deletar Memória", key=f"delete_{mem['id']}", type="primary"):
                            supabase.table("memories").delete().eq("id", mem['id']).execute()
                            st.success(f"Memória {mem['id']} deletada!")
                            st.rerun()
    except Exception as e:
        st.error(f"Erro ao carregar memórias: {e}")

# --- Página: Gerenciador de Usuários ---
elif page == "Gerenciador de Usuários":
    st.header("👥 Gerenciador de Usuários")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Usuários Mestres")
        masters_data = [user for user in fetch_data('users') if user.get('role') == 'master']
        masters_usernames = [user['username'] for user in masters_data]
        st.dataframe(pd.DataFrame(masters_usernames, columns=["Username"]), use_container_width=True)
        
        new_master = st.text_input("Adicionar novo Mestre", key="new_master")
        if st.button("Adicionar Mestre"):
            manage_user(new_master, "master", "add")
            st.rerun()
            
        remove_master = st.selectbox("Remover Mestre", options=[""] + masters_usernames, key="remove_master")
        if st.button("Remover Mestre Selecionado"):
            manage_user(remove_master, "master", "remove")
            st.rerun()

    with col2:
        st.subheader("Blacklist de Usuários")
        blacklisted_data = [user for user in fetch_data('users') if user.get('role') == 'blacklisted']
        blacklisted_usernames = [user['username'] for user in blacklisted_data]
        st.dataframe(pd.DataFrame(blacklisted_usernames, columns=["Username"]), use_container_width=True)

        new_blacklisted = st.text_input("Adicionar à Blacklist", key="new_blacklisted")
        if st.button("Adicionar à Blacklist"):
            manage_user(new_blacklisted, "blacklisted", "add")
            st.rerun()

        remove_blacklisted = st.selectbox("Remover da Blacklist", options=[""] + blacklisted_usernames, key="remove_blacklisted")
        if st.button("Remover Usuário Selecionado"):
            manage_user(remove_blacklisted, "blacklisted", "remove")
            st.rerun()

# --- Página: Configurações da IA ---
elif page == "Configurações da IA":
    st.header("⚙️ Configurações e Personalidade da IA")
    
    tab1, tab2, tab3 = st.tabs(["Personalidade (Prompt)", "Lorebook", "Configurações Gerais"])
    
    with tab1:
        st.subheader("Prompt Principal do Sistema")
        st.markdown("Este é o prompt que define a personalidade base da AI_YUH. Ele é enviado antes de cada interação.")
        
        try:
            prompt_data = supabase.table("settings").select("value").eq("key", "system_prompt").execute().data
            current_prompt = prompt_data[0]['value'] if prompt_data else "Você é a AI_YUH, uma IA amigável na Twitch."
        except Exception:
            current_prompt = "Erro ao carregar o prompt."

        system_prompt = st.text_area("Edite o prompt do sistema:", value=current_prompt, height=250)
        
        if st.button("Salvar Prompt do Sistema"):
            upsert_setting("system_prompt", system_prompt)

    with tab2:
        st.subheader("📖 Lorebook")
        st.markdown("Adicione fatos e informações permanentes que a IA deve sempre lembrar.")
        
        with st.form("new_lore_entry_form"):
            new_key = st.text_input("Chave do Fato (ex: 'usuário beanja')")
            new_value = st.text_area("Descrição do Fato (ex: 'Sempre lembra os outros de se hidratarem.')")
            submitted = st.form_submit_button("Adicionar ao Lorebook")
            if submitted:
                if new_key and new_value:
                    supabase.table("lorebook").insert({"entry_key": new_key, "entry_value": new_value}).execute()
                    st.success("Nova entrada adicionada ao Lorebook!")
                else:
                    st.warning("Ambos os campos 'Chave' e 'Descrição' são obrigatórios.")
        
        st.divider()
        
        st.markdown("#### Entradas Atuais do Lorebook")
        lore_entries = fetch_data('lorebook')
        if lore_entries:
            for entry in lore_entries:
                with st.container(border=True):
                    st.markdown(f"**{entry['entry_key']}**")
                    st.markdown(entry['entry_value'])
                    if st.button("Deletar Entrada", key=f"del_lore_{entry['id']}", type="primary"):
                        supabase.table("lorebook").delete().eq("id", entry['id']).execute()
                        st.rerun()
        else:
            st.info("O Lorebook está vazio.")

    with tab3:
        st.subheader("Modelos de IA e Configurações Gerais")
        st.markdown("Selecione os modelos Gemini a serem usados e outras configurações do bot.")

        settings_data = {item['key']: item['value'] for item in fetch_data('settings')}
        current_interaction_model = settings_data.get("interaction_model", "gemini-1.5-pro-latest")
        current_archivist_model = settings_data.get("archivist_model", "gemini-1.5-flash-latest")
        current_bot_prefix = settings_data.get("bot_prefix", "!ask")
        
        available_models = ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest", "gemini-pro"]
        
        interaction_model = st.selectbox(
            "Modelo de Interação (Conversa)", 
            options=available_models, 
            index=available_models.index(current_interaction_model) if current_interaction_model in available_models else 0
        )
        archivist_model = st.selectbox(
            "Modelo Arquivista (Resumos)", 
            options=available_models,
            index=available_models.index(current_archivist_model) if current_archivist_model in available_models else 0
        )
        bot_prefix = st.text_input("Prefixo de Comando do Bot", value=current_bot_prefix)
        
        if st.button("Salvar Configurações Gerais"):
            upsert_setting("interaction_model", interaction_model)
            upsert_setting("archivist_model", archivist_model)
            upsert_setting("bot_prefix", bot_prefix)
        
        st.markdown("Depois de salvar, use o comando `!reload` no chat da Twitch para que o bot aplique as novas configurações.")