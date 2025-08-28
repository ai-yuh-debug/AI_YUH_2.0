# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DB_ENABLED = False
supabase_client: Client = None
try:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    if not SUPABASE_URL or not SUPABASE_KEY: raise ValueError("Credenciais do Supabase não encontradas")
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logging.info("Módulo de Banco de Dados inicializado com sucesso.")
    DB_ENABLED = True
except Exception as e:
    logging.critical(f"Não foi possível conectar ao Supabase. Erro: {e}")

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
        logging.error(f"Erro ao carregar dados iniciais: {e}"); return None, []

def get_user_permission(username: str) -> str:
    if not DB_ENABLED: return 'normal'
    try:
        user_response = supabase_client.table('users').select("permission_level").eq("twitch_username", username.lower()).single().execute()
        return user_response.data.get('permission_level', 'normal') if user_response.data else 'normal'
    except Exception: return 'normal'

def add_lorebook_entry(entry: str, user: str) -> bool:
    if not DB_ENABLED: return False
    try:
        supabase_client.table('lorebook').insert({"entry": entry, "created_by": user}).execute()
        return True
    except Exception as e:
        logging.error(f"Erro ao adicionar entrada no lorebook: {e}"); return False
        
def get_current_lorebook() -> list[str]:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('lorebook').select("entry").execute()
        return [item['entry'] for item in response.data]
    except Exception as e:
        logging.error(f"Erro ao buscar o lorebook atual: {e}"); return []

def save_long_term_memory(username: str, summary: str):
    if not DB_ENABLED: return
    try:
        supabase_client.table('long_term_memory').insert({"username": username, "summary": summary}).execute()
    except Exception as e:
        logging.error(f"Erro ao salvar memória pessoal para {username}: {e}")

def search_long_term_memory(username: str, limit: int = 5) -> list[str]:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('long_term_memory').select("summary").eq("username", username).order("created_at", desc=True).limit(limit).execute()
        return [item['summary'] for item in response.data]
    except Exception as e:
        logging.error(f"Erro ao buscar memória pessoal para {username}: {e}"); return []

def save_hierarchical_memory(level: str, summary: str, metadata: dict = None):
    if not DB_ENABLED: return
    try:
        supabase_client.table('hierarchical_memory').insert({"memory_level": level, "summary": summary, "metadata": metadata}).execute()
    except Exception as e:
        logging.error(f"Erro ao salvar memória hierárquica: {e}")

def search_hierarchical_memory(limit: int = 3) -> list[str]:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('hierarchical_memory').select("summary").order("created_at", desc=True).limit(limit).execute()
        return [item['summary'] for item in response.data]
    except Exception as e:
        logging.error(f"Erro ao buscar memória hierárquica: {e}"); return []

def get_memories_for_consolidation(level: str, start_time: datetime, end_time: datetime) -> list:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('hierarchical_memory').select("id, summary").eq("memory_level", level).gte("created_at", start_time.isoformat()).lte("created_at", end_time.isoformat()).execute()
        return response.data
    except Exception as e:
        logging.error(f"Erro ao buscar memórias '{level}' para consolidação: {e}"); return []

def delete_memories_by_ids(ids: list):
    if not DB_ENABLED or not ids: return
    try:
        supabase_client.table('hierarchical_memory').delete().in_('id', ids).execute()
    except Exception as e:
        logging.error(f"Erro ao deletar memórias antigas: {e}")

def delete_lorebook_entry(entry_id: int):
    if not DB_ENABLED: return
    try:
        supabase_client.table('lorebook').delete().eq('id', entry_id).execute()
    except Exception as e:
        logging.error(f"Erro ao deletar entrada do lorebook (ID: {entry_id}): {e}")

def update_bot_status(status: str):
    if not DB_ENABLED: return
    try:
        update_response = supabase_client.table('bot_status').update({"status_value": status,"last_updated": datetime.now(pytz.utc).isoformat()}).eq('status_key', 'bot_state').execute()
        if not update_response.data:
            supabase_client.table('bot_status').insert({"status_key": "bot_state","status_value": status,"last_updated": datetime.now(pytz.utc).isoformat()}).execute()
        logging.info(f"Status do bot atualizado para: {status}")
    except Exception as e:
        logging.error(f"Erro ao atualizar status do bot: {e}")

def add_log(level: str, message: str, thread_name: str):
    if not DB_ENABLED: return
    try:
        supabase_client.table('logs').insert({"level": level, "message": message, "thread_name": thread_name}).execute()
    except Exception as e:
        print(f"ERRO DE LOGGING NO DB: {e}")

def get_logs(limit: int = 100) -> list:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('logs').select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        print(f"ERRO AO BUSCAR LOGS DO DB: {e}"); return []

def delete_old_logs():
    """Deleta logs com mais de 24 horas para manter a tabela limpa."""
    if not DB_ENABLED: return
    try:
        time_threshold = (datetime.now(pytz.utc) - timedelta(hours=24)).isoformat()
        supabase_client.table('logs').delete().lt('created_at', time_threshold).execute()
        logging.info("Limpeza de logs antigos executada com sucesso.")
        add_log("INFO", "Limpeza de logs antigos executada.", "SchedulerThread")
    except Exception as e:
        logging.error(f"Erro ao deletar logs antigos: {e}")