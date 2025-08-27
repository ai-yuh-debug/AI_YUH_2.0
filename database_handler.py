# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento do Banco de Dados
# =========================================================================================
# FASE 6: O Ciclo Completo da Memória e Busca na Web
#
# Autor: Seu Nome/Apelido
# Versão: 1.2.0
# Data: 26/08/2025
#
# Descrição: Adiciona funções para salvar e pesquisar na tabela de memória
#            de longo prazo, completando o ciclo de vida da memória.
#
# =========================================================================================

import os
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
        settings = settings_response.data
        print(f"Configurações carregadas: {settings['interaction_model']}")
        lorebook_response = supabase_client.table('lorebook').select("entry").execute()
        lorebook = [item['entry'] for item in lorebook_response.data]
        print(f"Lorebook carregado com {len(lorebook)} entradas.")
        return settings, lorebook
    except Exception as e:
        print(f"ERRO ao carregar dados iniciais: {e}")
        return None, []

def get_user_permission(username: str) -> str:
    if not DB_ENABLED: return 'normal'
    try:
        user_response = supabase_client.table('users').select("permission_level").eq("twitch_username", username.lower()).execute()
        if user_response.data:
            return user_response.data[0]['permission_level']
        return 'normal'
    except Exception as e:
        print(f"Erro ao verificar permissão para {username}: {e}")
        return 'normal'

def add_lorebook_entry(entry: str, user: str) -> bool:
    if not DB_ENABLED: return False
    try:
        response = supabase_client.table('lorebook').insert({"entry": entry, "created_by": user}).execute()
        if response.data:
            print(f"Nova entrada no Lorebook adicionada por {user}: {entry}")
            return True
        return False
    except Exception as e:
        print(f"Erro ao adicionar entrada no lorebook: {e}")
        return False

def save_long_term_memory(username: str, summary: str):
    """Salva um resumo de conversa na tabela de memória de longo prazo."""
    if not DB_ENABLED: return
    try:
        supabase_client.table('long_term_memory').insert({
            "username": username,
            "summary": summary,
            "embedding": None
        }).execute()
        print(f"Memória de longo prazo salva para {username}.")
    except Exception as e:
        print(f"Erro ao salvar memória de longo prazo para {username}: {e}")

def search_long_term_memory(username: str, limit: int = 5) -> list[str]:
    """Busca as memórias de longo prazo mais recentes de um usuário."""
    if not DB_ENABLED: return []
    try:
        response = supabase_client.table('long_term_memory').select("summary").eq("username", username).order("created_at", desc=True).limit(limit).execute()
        return [item['summary'] for item in response.data]
    except Exception as e:
        print(f"Erro ao buscar memória de longo prazo para {username}: {e}")
        return []