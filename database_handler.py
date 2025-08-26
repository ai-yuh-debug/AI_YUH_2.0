# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento do Banco de Dados
# =========================================================================================
# FASE 5: A IA de Gerenciamento de Memória e o Ciclo de Vida
#
# Autor: Seu Nome/Apelido
# Versão: 1.1.0
# Data: 26/08/2025
#
# Descrição: Este módulo agora contém funções para carregar todas as configurações
#            iniciais do bot, gerenciar o lorebook e verificar permissões de usuário,
#            interagindo diretamente com as tabelas criadas no Supabase.
#
# =========================================================================================

import os
from supabase import create_client, Client

# --- Configuração do Cliente Supabase ---
DB_ENABLED = False
supabase_client: Client = None

try:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Credenciais do Supabase não encontradas no .env")

    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Módulo de Banco de Dados inicializado com sucesso.")
    DB_ENABLED = True

except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível conectar ao Supabase. Erro: {e}")

# --- Funções de Interface com o Banco de Dados ---

def load_initial_data():
    """
    Carrega todas as configurações iniciais, lorebook e usuários do DB.
    Esta função é chamada uma vez quando o bot inicia.
    """
    if not DB_ENABLED:
        return None, [], [] # Retorna dados vazios se o DB estiver offline

    try:
        print("Carregando dados iniciais do banco de dados...")
        
        # Carrega a única linha de configurações
        settings_response = supabase_client.table('settings').select("*").limit(1).single().execute()
        settings = settings_response.data
        print(f"Configurações carregadas: {settings['interaction_model']}")

        # Carrega todos os fatos do lorebook
        lorebook_response = supabase_client.table('lorebook').select("entry").execute()
        lorebook = [item['entry'] for item in lorebook_response.data]
        print(f"Lorebook carregado com {len(lorebook)} entradas.")
        
        return settings, lorebook

    except Exception as e:
        print(f"ERRO ao carregar dados iniciais: {e}")
        return None, [], []

def get_user_permission(username: str) -> str:
    """
    Verifica o nível de permissão de um usuário.
    Retorna 'normal' se o usuário não for encontrado.
    """
    if not DB_ENABLED:
        return 'normal'
    
    try:
        user_response = supabase_client.table('users').select("permission_level").eq("twitch_username", username.lower()).execute()
        if user_response.data:
            return user_response.data[0]['permission_level']
        return 'normal'
    except Exception as e:
        print(f"Erro ao verificar permissão para {username}: {e}")
        return 'normal'

def add_lorebook_entry(entry: str, user: str) -> bool:
    """Adiciona uma nova entrada ao lorebook."""
    if not DB_ENABLED:
        return False
        
    try:
        response = supabase_client.table('lorebook').insert({
            "entry": entry,
            "created_by": user
        }).execute()
        
        # Verifica se a inserção foi bem-sucedida
        if response.data:
            print(f"Nova entrada no Lorebook adicionada por {user}: {entry}")
            return True
        return False
    except Exception as e:
        print(f"Erro ao adicionar entrada no lorebook: {e}")
        return False