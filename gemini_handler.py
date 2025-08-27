# -*- coding: utf-8 -*-
# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento da IA
# =========================================================================================
# FASE 9: Configurações de IA Detalhadas
#
# Autor: Seu Nome/Apelido
# Versão: 1.7.1
# Data: 26/08/2025
#
# Descrição: A função de geração de resposta agora aceita e utiliza os
#            parâmetros granulares (temperatura, etc.) carregados do DB.
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
        
        generation_config = genai.types.GenerationConfig(
            temperature=float(settings.get('temperature', 0.9)),
            top_p=float(settings.get('top_p', 1.0)),
            top_k=int(settings.get('top_k', 1)),
            max_output_tokens=int(settings.get('max_output_tokens', 256))
        )
        
        chat = interaction_model.start_chat(history=[])
        response = chat.send_message(prompt, generation_config=generation_config)
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

        generation_config = genai.types.GenerationConfig(
            temperature=float(settings.get('temperature', 0.9)),
            top_p=float(settings.get('top_p', 1.0)),
            top_k=int(settings.get('top_k', 1)),
            max_output_tokens=int(settings.get('max_output_tokens', 256))
        )

        chat = interaction_model.start_chat(history=[])
        response = chat.send_message(prompt, generation_config=generation_config)
        # Limita a resposta final ao máximo de tokens para evitar mensagens muito longas
        return response.text.replace('*', '').replace('`', '').strip()[:int(settings.get('max_output_tokens', 256))]
    except Exception as e:
        print(f"Erro na geração (com busca): {e}"); return "Ocorreu um erro ao pensar."

def summarize_conversation(conversation_history: list) -> str:
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Sumarização indisponível."
    try:
        transcript = "\n".join(f"{msg['role']}: {msg['parts'][0]}" for msg in conversation_history)
        prompt = f"Resuma os pontos principais da conversa a seguir em uma frase impessoal:\n\n{transcript}\n\nResumo:"
        response = summarizer_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar conversa: {e}"); return "Erro de sumarização."