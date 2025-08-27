# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client

DB_ENABLED = False
supabase_client: Client = None

try:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Credenciais do Supabase não encontradas")
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Módulo de Banco de Dados inicializado com sucesso.")
    DB_ENABLED = True
except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível conectar ao Supabase. Erro: {e}")

def load_initial_data():
    if not DB_ENABLED: return None, []
    try:
        print("Carregando dados iniciais do banco de dados...")
        settings_response = supabase_client.table('settings').select("*").limit(1).single().execute()
        settings = settings_response.data; print(f"Configurações carregadas.")
        lorebook_response = supabase_client.table('lorebook').select("entry").execute()
        lorebook = [item['entry'] for item in lorebook_response.data]
        print(f"Lorebook carregado com {len(lorebook)} entradas.")
        return settings, lorebook
    except Exception as e:
        print(f"ERRO ao carregar dados iniciais: {e}"); return None, []

def get_user_permission(username: str) -> str:
    if not DB_ENABLED: return 'normal'
    try:
        user_response = supabase_client.table('users').select("permission_level").eq("twitch_username", username.lower()).execute()
        return user_response.data[0]['permission_level'] if user_response.data else 'normal'
    except Exception as e:
        print(f"Erro ao verificar permissão para {username}: {e}"); return 'normal'

def add_lorebook_entry(entry: str, user: str) -> bool:
    if not DB_ENABLED: return False
    try:
        response = supabase_client.table('lorebook').insert({"entry": entry, "created_by": user}).execute()
        return bool(response.data)
    except Exception as e:
        print(f"Erro ao adicionar entrada no lorebook: {e}"); return False

def save_long_term_memory(username: str, summary: str):
    if not DB_ENABLED: return
    try:
        supabase_client.table('long_term_memory').insert({"username": username, "summary": summary}).execute()
        print(f"Memória pessoal salva para {user}.")
    except Exception as e:
        print(f"Erro ao salvar memória pessoal para {username}: {e}")

def search_long_term_memory(username: str, limit: int = 5) -> list[str]:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('long_term_memory').select("summary").eq("username", username).order("created_at", desc=True).limit(limit).execute()
        return [item['summary'] for item in response.data]
    except Exception as e:
        print(f"Erro ao buscar memória pessoal para {username}: {e}"); return []

def save_hierarchical_memory(level: str, summary: str, metadata: dict = None):
    if not DB_ENABLED: return
    try:
        supabase_client.table('hierarchical_memory').insert({"memory_level": level, "summary": summary, "metadata": metadata}).execute()
        print(f"Memória hierárquica (nível: {level}) salva com sucesso.")
    except Exception as e:
        print(f"Erro ao salvar memória hierárquica: {e}")

def search_hierarchical_memory(limit: int = 3) -> list[str]:
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('hierarchical_memory').select("summary").order("created_at", desc=True).limit(limit).execute()
        return [item['summary'] for item in response.data]
    except Exception as e:
        print(f"Erro ao buscar memória hierárquica: {e}"); return []

def get_memories_for_consolidation(level: str, start_time: datetime, end_time: datetime) -> list:
    """Busca memórias de um nível específico dentro de um período de tempo."""
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('hierarchical_memory').select("id, summary").eq("memory_level", level).gte("created_at", start_time.isoformat()).lte("created_at", end_time.isoformat()).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar memórias '{level}' para consolidação: {e}"); return []

def delete_memories_by_ids(ids: list):
    """Deleta memórias da tabela hierárquica com base em uma lista de IDs."""
    if not DB_ENABLED or not ids: return
    try:
        supabase_client.table('hierarchical_memory').delete().in_('id', ids).execute()
        print(f"Memórias antigas (IDs: {ids}) deletadas com sucesso.")
    except Exception as e:
        print(f"Erro ao deletar memórias antigas: {e}")