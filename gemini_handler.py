# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento da IA
# =========================================================================================
# FASE 2: Integração com a IA de Interação
#
# Autor: Seu Nome/Apelido
# Versão: 1.0.0
# Data: 26/08/2025
#
# Descrição: Este módulo é responsável por toda a comunicação com a API do
#            Google Gemini. Ele inicializa o modelo e fornece uma função
#            simples para gerar respostas a partir de um prompt.
#
# =========================================================================================

import os
import google.generativeai as genai

# --- Configuração da API do Gemini ---

try:
    # Carrega a API Key a partir das variáveis de ambiente
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Configurações do modelo de IA
    # Usaremos o gemini-1.5-flash por ser rápido e eficiente para chat.
    # TODO: Na Fase 7, tornaremos essas configurações editáveis pelo painel.
    generation_config = {
        "temperature": 0.9,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 256, # Limita o tamanho da resposta para não floodar o chat
    }

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    # Inicializa o modelo
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    
    # Inicia a "conversa" com a IA. Vamos construir o histórico aqui.
    convo = model.start_chat(history=[
        # TODO: Fases 4 e 5 - O histórico será preenchido com a memória de curto e longo prazo.
    ])

    print("Módulo Gemini inicializado com sucesso.")
    GEMINI_ENABLED = True

except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível inicializar o módulo Gemini. Verifique sua API Key. Erro: {e}")
    GEMINI_ENABLED = False

# --- Função Principal de Geração de Resposta ---

def generate_response(question: str) -> str:
    """
    Envia uma pergunta para o modelo Gemini e retorna a resposta.
    
    Args:
        question: A pergunta feita pelo usuário no chat.
        
    Returns:
        A resposta gerada pela IA ou uma mensagem de erro.
    """
    if not GEMINI_ENABLED:
        return "Desculpe, meu cérebro (a API do Gemini) está offline no momento."

    try:
        # TODO: Fases Futuras - Aqui vamos adicionar o Lorebook e a Personalidade ao prompt.
        # Por enquanto, enviamos a pergunta diretamente.
        prompt = f"Um usuário na Twitch perguntou: '{question}'. Responda de forma concisa e útil para um chat de live stream."
        
        convo.send_message(prompt)
        
        # Remove markdown e formatações indesejadas da resposta
        response_text = convo.last.text.replace('*', '').replace('`', '').strip()
        
        # Garante que a resposta não exceda o limite de caracteres da Twitch (500)
        return response_text[:480]

    except Exception as e:
        print(f"Erro ao gerar resposta da IA: {e}")
        return "Ocorreu um erro enquanto eu pensava na sua pergunta. Por favor, tente novamente."