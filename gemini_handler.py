# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento da IA
# =========================================================================================
# FASE 6: O Ciclo Completo da Memória e Busca na Web (DDGS)
#
# Autor: Seu Nome/Apelido
# Versão: 1.6.1 (Fallback para DDGS Apenas)
# Data: 26/08/2025
#
# Descrição: O código foi adaptado para usar DDGS como o único método de
#            busca na web, garantindo compatibilidade com ambientes Python
#            mais antigos e a biblioteca google-generativeai==0.8.5.
#
# =========================================================================================

import os
import google.generativeai as genai
from ddgs import DDGS

GEMINI_ENABLED = False
interaction_model = None
summarizer_model = None

try:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=GEMINI_API_KEY)

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    # Modelo de sumarização
    summarizer_model = genai.GenerativeModel("gemini-1.5-flash")

    print("Módulo Gemini inicializado.")
    GEMINI_ENABLED = True

except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível inicializar o módulo Gemini. Erro: {e}")

def load_interaction_model(model_name: str):
    """Carrega o modelo de IA de interação (sem ferramentas de busca nativa)."""
    global interaction_model
    try:
        interaction_model = genai.GenerativeModel(
            model_name=model_name,
            safety_settings=safety_settings
        )
        print(f"Modelo de interação '{model_name}' carregado.")
    except Exception as e:
        print(f"ERRO ao carregar o modelo de interação '{model_name}': {e}")
        global GEMINI_ENABLED
        GEMINI_ENABLED = False

def web_search(query: str, num_results: int = 3) -> str:
    """Realiza uma busca na web e retorna um resumo dos resultados."""
    print(f"Realizando busca na web (DDGS) por: '{query}'")
    try:
        results = DDGS().text(query, max_results=num_results)
        if not results: return ""
        return "Contexto da busca na web:\n" + "\n".join(f"- {res['body']}" for res in results)
    except Exception as e:
        print(f"Erro na busca da web: {e}"); return ""

def generate_response(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list, web_context: str) -> str:
    """Gera uma resposta da IA usando todo o contexto disponível."""
    if not GEMINI_ENABLED or not interaction_model:
        return "Desculpe, meu cérebro de interação está offline."
    try:
        # A biblioteca antiga usa um construtor de chat diferente
        chat = interaction_model.start_chat(history=[])
        
        # Construímos o prompt como um único bloco de texto
        full_prompt_text = ""
        full_prompt_text += settings.get('personality_prompt', '') + "\n\n"
        
        if lorebook:
            lorebook_text = "\n".join(f"- {fact}" for fact in lorebook)
            full_prompt_text += f"{settings.get('lorebook_prompt', '')}\n{lorebook_text}\n\n"
        
        if long_term_memories:
            memories_text = "\n".join(f"- {mem}" for mem in long_term_memories)
            full_prompt_text += f"Resumos de conversas passadas:\n{memories_text}\n\n"
        
        if web_context:
            full_prompt_text += f"{web_context}\n\n"
        
        for msg in history:
            full_prompt_text += f"{msg['role']}: {msg['parts'][0]}\n"

        full_prompt_text += f"user: {question}\nmodel:"

        response = chat.send_message(full_prompt_text)
        response_text = response.text.replace('*', '').replace('`', '').strip()
        return response_text[:480]
    except Exception as e:
        print(f"Erro ao gerar resposta da IA: {e}"); return "Ocorreu um erro enquanto eu pensava."

def summarize_conversation(conversation_history: list) -> str:
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Sumarização indisponível."
    try:
        transcript = "\n".join(f"{msg['role']}: {msg['parts'][0]}" for msg in conversation_history)
        prompt = f"Resuma os pontos principais da conversa a seguir em uma frase impessoal:\n\n{transcript}\n\nResumo:"
        response = summarizer_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar conversa: {e}"); return "Erro de sumarização."