# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento da IA
# =========================================================================================
# FASE 7: Busca Condicional Inteligente
#
# Autor: Seu Nome/Apelido
# Versão: 1.7.0 (Busca Condicional)
# Data: 26/08/2025
#
# Descrição: O módulo agora tem duas funções de geração de resposta: uma rápida
#            sem busca e uma completa com busca, para permitir a lógica
#            de busca condicional no bot principal.
#
# =========================================================================================

import os
import google.generativeai as genai
from ddgs import DDGS

# ... (Configuração inicial e load_interaction_model permanecem os mesmos) ...
GEMINI_ENABLED = False
interaction_model = None
summarizer_model = None

try:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=GEMINI_API_KEY)
    safety_settings = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, # etc.
    ]
    summarizer_model = genai.GenerativeModel("gemini-1.5-flash")
    print("Módulo Gemini inicializado.")
    GEMINI_ENABLED = True
except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível inicializar o módulo Gemini. Erro: {e}")

def load_interaction_model(model_name: str):
    global interaction_model
    try:
        interaction_model = genai.GenerativeModel(model_name=model_name, safety_settings=safety_settings)
        print(f"Modelo de interação '{model_name}' carregado.")
    except Exception as e:
        print(f"ERRO ao carregar o modelo de interação '{model_name}': {e}")
        global GEMINI_ENABLED
        GEMINI_ENABLED = False

def web_search(query: str, num_results: int = 3) -> str:
    print(f"Realizando busca na web (DDGS) por: '{query}'")
    try:
        results = DDGS().text(query, max_results=num_results)
        if not results: return ""
        return "Contexto da busca na web:\n" + "\n".join(f"- {res['body']}" for res in results)
    except Exception as e:
        print(f"Erro na busca da web: {e}"); return ""

def _build_base_prompt(settings: dict, lorebook: list, long_term_memories: list, history: list) -> str:
    """Função auxiliar para construir o prompt base sem busca na web."""
    prompt_text = settings.get('personality_prompt', '') + "\n\n"
    if lorebook:
        lorebook_text = "\n".join(f"- {fact}" for fact in lorebook)
        prompt_text += f"{settings.get('lorebook_prompt', '')}\n{lorebook_text}\n\n"
    if long_term_memories:
        memories_text = "\n".join(f"- {mem}" for mem in long_term_memories)
        prompt_text += f"Resumos de conversas passadas:\n{memories_text}\n\n"
    for msg in history:
        prompt_text += f"{msg['role']}: {msg['parts'][0]}\n"
    return prompt_text

def generate_response_without_search(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list) -> str:
    """PRIMEIRA TENTATIVA: Gera uma resposta usando apenas o contexto interno."""
    if not GEMINI_ENABLED or not interaction_model: return "Erro: Cérebro offline."
    try:
        prompt = _build_base_prompt(settings, lorebook, long_term_memories, history)
        prompt += f"user: {question}\nmodel:"
        
        chat = interaction_model.start_chat(history=[])
        response = chat.send_message(prompt)
        return response.text.replace('*', '').replace('`', '').strip()
    except Exception as e:
        print(f"Erro na geração (sem busca): {e}"); return "Ocorreu um erro ao pensar."

def generate_response_with_search(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list, web_context: str) -> str:
    """SEGUNDA TENTATIVA: Gera uma resposta usando o contexto interno E a busca na web."""
    if not GEMINI_ENABLED or not interaction_model: return "Erro: Cérebro offline."
    try:
        prompt = _build_base_prompt(settings, lorebook, long_term_memories, history)
        if web_context:
            prompt += f"{web_context}\n\n"
        prompt += f"user: {question}\nmodel:"

        chat = interaction_model.start_chat(history=[])
        response = chat.send_message(prompt)
        return response.text.replace('*', '').replace('`', '').strip()[:480]
    except Exception as e:
        print(f"Erro na geração (com busca): {e}"); return "Ocorreu um erro ao pensar."

# A função summarize_conversation permanece inalterada
def summarize_conversation(conversation_history: list) -> str:
    # ... (código inalterado) ...
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Sumarização indisponível."
    try:
        transcript = "\n".join(f"{msg['role']}: {msg['parts'][0]}" for msg in conversation_history)
        prompt = f"Resuma os pontos principais da conversa a seguir em uma frase impessoal:\n\n{transcript}\n\nResumo:"
        response = summarizer_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar conversa: {e}"); return "Erro de sumarização."