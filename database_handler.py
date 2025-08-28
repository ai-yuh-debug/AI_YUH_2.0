# -*- coding: utf-8 -*-
import os
from datetime import datetime
import pytz
from supabase import create_client, Client
import logging

# Configuração do logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_ENABLED = False
supabase_client: Client = None

try:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Credenciais do Supabase não encontradas no arquivo .env")
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logging.info("Módulo de Banco de Dados inicializado com sucesso.")
    DB_ENABLED = True
except Exception as e:
    logging.critical(f"Não foi possível conectar ao Supabase. O bot não funcionará sem o DB. Erro: {e}")

def load_initial_data():
    if not DB_ENABLED: return None, []
    try:
        logging.info("Carregando dados iniciais do banco de dados...")
        settings_response = supabase_client.table('settings').select("*").limit(1).single().execute()
        settings = settings_response.data
        logging.info("Configurações carregadas.")
        
        lorebook_response = supabase_client.table('lorebook').select("entry").execute()
        lorebook = [item['entry'] for item in lorebook_response.data]
        logging.info(f"Lorebook carregado com {len(lorebook)} entradas.")
        return settings, lorebook
    except Exception as e:
        logging.error(f"Erro ao carregar dados iniciais: {e}")
        return None, []

def get_user_permission(username: str) -> str:
    if not DB_ENABLED: return 'normal'
    try:
        user_response = supabase_client.table('users').select("permission_level").eq("twitch_username", username.lower()).single().execute()
        return user_response.data.get('permission_level', 'normal') if user_response.data else 'normal'
    except Exception:
        # Se single() falhar (nenhum usuário), retorna normal sem logar erro
        return 'normal'

def add_lorebook_entry(entry: str, user: str) -> bool:
    if not DB_ENABLED: return False
    try:
        supabase_client.table('lorebook').insert({"entry": entry, "created_by": user}).execute()
        logging.info(f"Nova entrada no Lorebook adicionada por {user}.")
        return True
    except Exception as e:
        logging.error(f"Erro ao adicionar entrada no lorebook: {e}")
        return False
        
def get_current_lorebook() -> list[str]:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('lorebook').select("entry").execute()
        return [item['entry'] for item in response.data]
    except Exception as e:
        logging.error(f"Erro ao buscar o lorebook atual: {e}")
        return []

def save_long_term_memory(username: str, summary: str):
    if not DB_ENABLED: return
    try:
        supabase_client.table('long_term_memory').insert({"username": username, "summary": summary}).execute()
        logging.info(f"Memória pessoal salva para {username}.")
    except Exception as e:
        logging.error(f"Erro ao salvar memória pessoal para {username}: {e}")

def search_long_term_memory(username: str, limit: int = 5) -> list[str]:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('long_term_memory').select("summary").eq("username", username).order("created_at", desc=True).limit(limit).execute()
        return [item['summary'] for item in response.data]
    except Exception as e:
        logging.error(f"Erro ao buscar memória pessoal para {username}: {e}")
        return []

def save_hierarchical_memory(level: str, summary: str, metadata: dict = None):
    if not DB_ENABLED: return
    try:
        supabase_client.table('hierarchical_memory').insert({"memory_level": level, "summary": summary, "metadata": metadata}).execute()
        logging.info(f"Memória hierárquica (nível: {level}) salva.")
    except Exception as e:
        logging.error(f"Erro ao salvar memória hierárquica: {e}")

def search_hierarchical_memory(limit: int = 3) -> list[str]:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('hierarchical_memory').select("summary").order("created_at", desc=True).limit(limit).execute()
        return [item['summary'] for item in response.data]
    except Exception as e:
        logging.error(f"Erro ao buscar memória hierárquica: {e}")
        return []

def get_memories_for_consolidation(level: str, start_time: datetime, end_time: datetime) -> list:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('hierarchical_memory').select("id, summary").eq("memory_level", level).gte("created_at", start_time.isoformat()).lte("created_at", end_time.isoformat()).execute()
        return response.data
    except Exception as e:
        logging.error(f"Erro ao buscar memórias '{level}' para consolidação: {e}")
        return []

def delete_memories_by_ids(ids: list):
    if not DB_ENABLED or not ids: return
    try:
        supabase_client.table('hierarchical_memory').delete().in_('id', ids).execute()
        logging.info(f"Memórias antigas (IDs: {ids}) deletadas.")
    except Exception as e:
        logging.error(f"Erro ao deletar memórias antigas: {e}")

def delete_lorebook_entry(entry_id: int):
    if not DB_ENABLED: return
    try:
        supabase_client.table('lorebook').delete().eq('id', entry_id).execute()
        logging.info(f"Entrada do Lorebook (ID: {entry_id}) deletada.")
    except Exception as e:
        logging.error(f"Erro ao deletar entrada do lorebook (ID: {entry_id}): {e}")

# ==============================================================================
#                      FUNÇÃO CORRIGIDA ABAIXO
# ==============================================================================
def update_bot_status(status: str):
    """Atualiza o status do bot na tabela bot_status usando upsert."""
    if not DB_ENABLED: return
    try:
        # UPSERT garante que a linha será criada se não existir, ou atualizada se já existir.
        supabase_client.table('bot_status').upsert({
            "status_key": "bot_state", # A chave que identifica a linha
            "status_value": status,
            "last_updated": datetime.now(pytz.utc).isoformat()
        }).execute()
        logging.info(f"Status do bot atualizado para: {status}")
    except Exception as e:
        logging.error(f"Erro ao atualizar status do bot: {e}")