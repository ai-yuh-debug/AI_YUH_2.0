# database_handler.py

import os
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializa o cliente do Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Conexão com Supabase estabelecida com sucesso.")
except Exception as e:
    print(f"Erro ao conectar com Supabase: {e}")
    supabase = None

def insert_memory(level: str, content: str, start_date: datetime, end_date: datetime):
    """
    Insere um novo registro de memória no banco de dados.
    level: 'hourly', 'daily', 'weekly', 'monthly', 'yearly'
    """
    if not supabase:
        print("Cliente Supabase não inicializado.")
        return None
    try:
        data = {
            "level": level,
            "content": content,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        response = supabase.table("memories").insert(data).execute()
        print(f"Memória de nível '{level}' inserida com sucesso.")
        return response
    except Exception as e:
        print(f"Erro ao inserir memória: {e}")
        return None

def get_memories_between(level: str, start_date: datetime, end_date: datetime):
    """
    Busca memórias de um determinado nível dentro de um intervalo de datas.
    """
    if not supabase:
        print("Cliente Supabase não inicializado.")
        return []
    try:
        response = supabase.table("memories") \
            .select("content, start_date, end_date") \
            .eq("level", level) \
            .gte("start_date", start_date.isoformat()) \
            .lte("end_date", end_date.isoformat()) \
            .order("start_date", desc=False) \
            .execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar memórias: {e}")
        return []

def delete_memories_between(level: str, start_date: datetime, end_date: datetime):
    """
    Deleta memórias de um determinado nível dentro de um intervalo de datas.
    """
    if not supabase:
        print("Cliente Supabase não inicializado.")
        return None
    try:
        response = supabase.table("memories") \
            .delete() \
            .eq("level", level) \
            .gte("start_date", start_date.isoformat()) \
            .lte("end_date", end_date.isoformat()) \
            .execute()
        print(f"Memórias de nível '{level}' entre {start_date} e {end_date} deletadas.")
        return response
    except Exception as e:
        print(f"Erro ao deletar memórias: {e}")
        return None

def get_all_memories_for_context():
    """
    Busca um conjunto relevante de memórias recentes para dar contexto à IA.
    """
    if not supabase:
        print("Cliente Supabase não inicializado.")
        return []
    try:
        daily = supabase.table("memories").select("content").eq("level", "daily").order("start_date", desc=True).limit(5).execute()
        weekly = supabase.table("memories").select("content").eq("level", "weekly").order("start_date", desc=True).limit(2).execute()
        monthly = supabase.table("memories").select("content").eq("level", "monthly").order("start_date", desc=True).limit(1).execute()
        
        memories = []
        if daily.data: memories.extend(daily.data)
        if weekly.data: memories.extend(weekly.data)
        if monthly.data: memories.extend(monthly.data)

        return memories
    except Exception as e:
        print(f"Erro ao buscar memórias de contexto: {e}")
        return []

def get_bot_settings():
    """Busca todas as configurações da tabela 'settings'."""
    if not supabase: return {}
    try:
        response = supabase.table("settings").select("key, value").execute()
        return {item['key']: item['value'] for item in response.data}
    except Exception as e:
        print(f"Erro ao buscar configurações do bot: {e}")
        return {}

def get_user_roles():
    """Busca todos os usuários e seus papéis."""
    if not supabase: return [], []
    try:
        response = supabase.table("users").select("username", "role").execute()
        masters = [user['username'] for user in response.data if user['role'] == 'master']
        blacklisted = [user['username'] for user in response.data if user['role'] == 'blacklisted']
        return masters, blacklisted
    except Exception as e:
        print(f"Erro ao buscar papéis de usuário: {e}")
        return [], []

def get_lorebook_entries():
    """Busca todas as entradas do lorebook."""
    if not supabase: return ""
    try:
        response = supabase.table("lorebook").select("entry_key", "entry_value").execute()
        return "\n".join([f"- {entry['entry_key']}: {entry['entry_value']}" for entry in response.data])
    except Exception as e:
        print(f"Erro ao buscar entradas do lorebook: {e}")
        return ""