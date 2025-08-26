# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento do Banco de Dados
# =========================================================================================
# FASE 3: A Base da Memória - Conexão com o Banco de Dados
#
# Autor: Seu Nome/Apelido
# Versão: 1.0.0
# Data: 26/08/2025
#
# Descrição: Este módulo gerencia toda a comunicação com o banco de dados Supabase.
#            Ele é responsável por inicializar o cliente e fornecer funções para
#            ler e escrever dados, como configurações, memórias e lorebook.
#
# =========================================================================================

import os
from supabase import create_client, Client

# --- Configuração do Cliente Supabase ---

try:
    # Carrega as credenciais do Supabase a partir das variáveis de ambiente
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("As credenciais do Supabase (URL e Key) não foram encontradas no arquivo .env")

    # Cria o cliente Supabase que será usado em todo o projeto
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("Módulo de Banco de Dados inicializado com sucesso. Conectado ao Supabase.")
    DB_ENABLED = True

except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível conectar ao Supabase. Verifique suas credenciais no .env. Erro: {e}")
    supabase_client = None
    DB_ENABLED = False

# --- Funções de Interface com o Banco de Dados ---

# Exemplo de função que usaremos nas próximas fases.
# Por enquanto, ela não faz nada, mas serve para estruturar o código.
def fetch_bot_settings():
    """
    Busca as configurações do bot no banco de dados.
    (Personalidade, Prompt do Sistema, etc.)
    
    TODO: Implementar a lógica real na Fase 4, após criarmos a tabela.
    """
    if not DB_ENABLED:
        print("AVISO: O banco de dados está desabilitado. Usando configurações padrão.")
        # Retorna um dicionário padrão para que o bot possa funcionar mesmo sem DB
        return {
            'personality': 'Você é uma IA assistente em um chat da Twitch.',
            'system_prompt': 'Responda de forma curta e amigável.',
            'model': 'gemini-1.5-flash'
        }
        
    try:
        # Futuramente, aqui faremos a chamada real:
        # response = supabase_client.table('settings').select("*").limit(1).single().execute()
        # return response.data
        print("Função fetch_bot_settings chamada (ainda não implementada).")
        # Por enquanto, retornamos o mesmo padrão.
        return {
            'personality': 'Você é uma IA assistente em um chat da Twitch.',
            'system_prompt': 'Responda de forma curta e amigável.',
            'model': 'gemini-1.5-flash'
        }
    except Exception as e:
        print(f"Erro ao buscar configurações no banco de dados: {e}")
        return None # Em caso de erro, retornamos None

# Adicionaremos mais funções aqui à medida que o projeto crescer (fetch_lorebook, save_memory, etc.)