# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import streamlit.components.v1 as components

load_dotenv()
from database_handler import supabase_client, DB_ENABLED, delete_lorebook_entry

st.set_page_config(page_title="Painel AI_Yuh", page_icon="🤖", layout="wide")

# Funções de cache para dados que não mudam com frequência
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

st.title("🤖 Painel de Controle do AI_Yuh Bot")
if not DB_ENABLED: st.error("ERRO GRAVE: Não foi possível conectar ao Supabase."); st.stop()

# --- Seção de Atividade ao Vivo ---
with st.container(border=True):
    st.subheader("Atividade ao Vivo e Status")
    
    # Placeholders para os elementos que o JavaScript irá preencher
    status_placeholder = st.empty()
    debug_placeholder = st.empty()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("##### ⚙️ Logs do Sistema")
        system_log_placeholder = st.empty()
    with col2:
        st.markdown("##### 🧠 Pensamento da IA")
        ai_log_placeholder = st.empty()
    with col3:
        st.markdown("##### 💬 Chat Processado")
        chat_log_placeholder = st.empty()

# ==============================================================================
#                      COMPONENTE CORRIGIDO (DE NOVO)
# ==============================================================================
# Definimos o JavaScript como uma string bruta (r"...") para que o Python
# não tente interpretar caracteres especiais como '\n'.
# Usamos o método .format() para inserir os IDs, que é seguro.
javascript_code = r"""
<script type="text/javascript">
    const statusPlaceholder = parent.document.getElementById('{status_id}');
    const debugPlaceholder = parent.document.getElementById('{debug_id}');
    const systemLogPlaceholder = parent.document.getElementById('{system_id}');
    const aiLogPlaceholder = parent.document.getElementById('{ai_id}');
    const chatLogPlaceholder = parent.document.getElementById('{chat_id}');

    function formatTimestamp(isoString) {{
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleTimeString('pt-BR', {{ timeZone: 'America/Sao_Paulo' }});
    }}

    async function fetchData() {{
        try {{
            const response = await fetch('http://localhost:10001/api/live_data');
            const data = await response.json();

            const statusText = data.status || 'Desconhecido';
            const statusColor = statusText.toLowerCase().includes('awake') ? 'green' : (statusText.toLowerCase().includes('asleep') ? 'orange' : 'red');
            statusPlaceholder.innerHTML = `<p><b>Status do Bot:</b> <span style="color:${{statusColor}}; font-weight:bold;">${{statusText}}</span></p>`;

            const debugText = data.debug_status || 'Aguardando depuração...';
            debugPlaceholder.innerHTML = `<textarea disabled style="width: 100%; height: 100px; font-family: monospace; background-color: #0E1117; color: #FAFAFA; border: 1px solid #262730; border-radius: 0.25rem;">${{debugText}}</textarea>`;

            const allLogs = data.logs || [];
            const systemLogs = allLogs.filter(log => !['CHAT', 'IA PENSANDO'].includes(log.log_type));
            const aiLogs = allLogs.filter(log => log.log_type === 'IA PENSANDO');
            const chatLogs = allLogs.filter(log => log.log_type === 'CHAT');

            const formatLogs = (logs) => logs.map(log => `${{formatTimestamp(log.created_at)}} | ${{log.log_type ? log.log_type + ':' : ''}} ${{log.message}`).join('\n');

            systemLogPlaceholder.innerHTML = `<textarea disabled style="width: 100%; height: 300px; font-family: monospace; background-color: #0E1117; color: #FAFAFA; border: 1px solid #262730; border-radius: 0.25rem;">${{formatLogs(systemLogs)}}</textarea>`;
            aiLogPlaceholder.innerHTML = `<textarea disabled style="width: 100%; height: 300px; font-family: monospace; background-color: #0E1117; color: #FAFAFA; border: 1px solid #262730; border-radius: 0.25rem;">${{formatLogs(aiLogs)}}</textarea>`;
            chatLogPlaceholder.innerHTML = `<textarea disabled style="width: 100%; height: 300px; font-family: monospace; background-color: #0E1117; color: #FAFAFA; border: 1px solid #262730; border-radius: 0.25rem;">${{formatLogs(chatLogs)}}</textarea>`;

        }} catch (e) {{
            console.error("Erro ao buscar dados da API:", e);
            statusPlaceholder.innerHTML = `<p><b>Status do Bot:</b> <span style="color:red; font-weight:bold;">Erro de conexão com a API</span></p>`;
        }}
    }}

    fetchData();
    setInterval(fetchData, 5000);
</script>
""".format(
    status_id=status_placeholder._id,
    debug_id=debug_placeholder._id,
    system_id=system_log_placeholder._id,
    ai_id=ai_log_placeholder._id,
    chat_id=chat_log_placeholder._id
)

components.html(javascript_code, height=0)
# ==============================================================================

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
                    st.success("Configurações Gerais salvas!"); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

    with st.expander("🧠 Configurações de Memória Generativa"):
        with st.form("memory_form"):
            col1, col2, col3 = st.columns(3)
            with col1: mem_exp = st.number_input("Expiração Mem. Pessoal (min)", value=int(settings.get('memory_expiration_minutes', 5)), min_value=1)
            with col2: glob_max_msg = st.number_input("Gatilho Sumarização (msgs)", value=int(settings.get('global_buffer_max_messages', 40)), min_value=10)
            with col3: glob_max_min = st.number_input("Gatilho Sumarização (min)", value=int(settings.get('global_buffer_max_minutes', 15)), min_value=1)
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
        permission = st.selectbox("Nível de Permissão", ["normal", "master", "blacklist", "bot"])
        if st.form_submit_button("Salvar Usuário"):
            if username:
                try:
                    supabase_client.table('users').upsert({'twitch_username': username, 'permission_level': permission}).execute()
                    st.success(f"Usuário '{username}' salvo como '{permission}'."); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"Erro ao salvar usuário: {e}")
            else: st.warning("O nome de usuário não pode estar vazio.")

with st.expander("📚 Gerenciar Lorebook", expanded=True):
    lorebook_df = get_lorebook()
    if not lorebook_df.empty:
        lorebook_df['delete'] = False
        edited_df = st.data_editor(lorebook_df, column_config={"delete": st.column_config.CheckboxColumn("Apagar?", default=False)}, use_container_width=True, hide_index=True)
        if st.button("Deletar Entradas Selecionadas", type="primary"):
            entries_to_delete = edited_df[edited_df['delete']]
            if not entries_to_delete.empty:
                for entry_id in entries_to_delete['id']: delete_lorebook_entry(entry_id)
                st.success(f"{len(entries_to_delete)} entrada(s) deletada(s)!"); st.cache_data.clear(); st.rerun()
            else: st.warning("Nenhuma entrada selecionada para deletar.")
    else: st.info("Nenhum fato no Lorebook.")
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
            else: st.warning("O fato não pode estar vazio.")

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

st.sidebar.header("Ações Rápidas")
if st.sidebar.button("Forçar Recarga do Painel"):
    st.cache_data.clear()
    st.rerun()