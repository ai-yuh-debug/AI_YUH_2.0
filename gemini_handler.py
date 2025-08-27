# -*- coding: utf-8 -*-
# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento da IA
# =========================================================================================
# FASE 10: Versão de Compatibilidade Final
#
# Autor: Seu Nome/Apelido
# Versão: 1.8.1 (Removendo safety_settings das chamadas de geração)
# Data: 26/08/2025
#
# Descrição: Adaptação final para a biblioteca google-generativeai==0.8.5.
#            Remove a passagem explícita de safety_settings das chamadas de
#            geração, pois a v0.8.5 parece ter problemas com isso.
#
# =========================================================================================

import os
import google.generativeai as genai
from ddgs import DDGS

GEMINI_ENABLED = False
interaction_model = None
summarizer_model = None

# Mantemos a definição, mas não a passaremos mais para o modelo
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

try:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=GEMINI_API_KEY)
    print("Módulo Gemini inicializado.")
    GEMINI_ENABLED = True
except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível inicializar o módulo Gemini. Erro: {e}")

def load_models_from_settings(settings: dict):
    global interaction_model, summarizer_model
    try:
        interaction_model_name = settings.get('interaction_model', 'gemini-1.5-flash')
        archivist_model_name = settings.get('archivist_model', 'gemini-1.5-flash')
        
        # Inicializamos os modelos sem passar safety_settings aqui também
        interaction_model = genai.GenerativeModel(model_name=interaction_model_name)
        print(f"Modelo de interação '{interaction_model_name}' carregado.")
        
        summarizer_model = genai.GenerativeModel(model_name=archivist_model_name)
        print(f"Modelo arquivista '{archivist_model_name}' carregado.")
    except Exception as e:
        print(f"ERRO ao carregar modelos de IA: {e}"); global GEMINI_ENABLED; GEMINI_ENABLED = False

def web_search(query: str, num_results: int = 3) -> str:
    print(f"Realizando busca na web (DDGS) por: '{query}'")
    try:
        results = DDGS().text(query, max_results=num_results)
        if not results: return ""
        return "Contexto da busca na web:\n" + "\n".join(f"- {res['body']}" for res in results)
    except Exception as e:
        print(f"Erro na busca da web: {e}"); return ""

def _build_base_prompt(settings: dict, lorebook: list, long_term_memories: list, history: list, hierarchical_memories: list) -> str:
    prompt_text = settings.get('personality_prompt', '') + "\n\n"
    if lorebook:
        prompt_text += f"{settings.get('lorebook_prompt', '')}\n" + "\n".join(f"- {fact}" for fact in lorebook) + "\n\n"
    if long_term_memories:
        prompt_text += "Resumos de suas conversas passadas comigo:\n" + "\n".join(f"- {mem}" for mem in long_term_memories) + "\n\n"
    if hierarchical_memories:
        prompt_text += "Para te dar contexto sobre o que aconteceu recentemente no chat, aqui estão os últimos resumos de eventos:\n" + "\n".join(f"- {mem}" for mem in hierarchical_memories) + "\n\n"
    for msg in history:
        prompt_text += f"{msg['role']}: {msg['parts'][0]}\n"
    return prompt_text

def _generate_response(prompt: str, settings: dict) -> str:
    """Função auxiliar unificada para gerar respostas."""
    try:
        chat = interaction_model.start_chat(history=[])
        
        config = genai.types.GenerationConfig(
            temperature=float(settings.get('temperature', 0.9)),
            top_p=float(settings.get('top_p', 1.0)),
            top_k=int(settings.get('top_k', 1)),
            max_output_tokens=int(settings.get('max_output_tokens', 256))
        )
        
        # --- MODIFICAÇÃO: Removendo o parâmetro safety_settings da chamada send_message ---
        response = chat.send_message(prompt, generation_config=config)
        
        if not response.parts:
            print("AVISO: A resposta da IA foi bloqueada por filtros de segurança (sem override).")
            return "Minha resposta foi bloqueada pelos meus filtros de segurança principais. Por favor, tente outro assunto."
        
        return response.text.replace('*', '').replace('`', '').strip()
    except Exception as e:
        if "response.text" in str(e) and "none were returned" in str(e):
             print("AVISO: A resposta da IA foi bloqueada por filtros de segurança (capturado por exceção).")
             return "Minha resposta foi bloqueada pelos meus filtros de segurança. Tente reformular a pergunta."
        print(f"Erro na geração de resposta: {e}"); return "Ocorreu um erro ao pensar."

def generate_response_without_search(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list, hierarchical_memories: list) -> str:
    if not GEMINI_ENABLED or not interaction_model: return "Erro: Cérebro offline."
    prompt = _build_base_prompt(settings, lorebook, long_term_memories, history, hierarchical_memories) + f"user: {question}\nmodel:"
    return _generate_response(prompt, settings)

def generate_response_with_search(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list, hierarchical_memories: list, web_context: str) -> str:
    if not GEMINI_ENABLED or not interaction_model: return "Erro: Cérebro offline."
    prompt = _build_base_prompt(settings, lorebook, long_term_memories, history, hierarchical_memories)
    if web_context: prompt += f"{web_context}\n\n"
    prompt += f"user: {question}\nmodel:"
    return _generate_response(prompt, settings)

def summarize_conversation(conversation_history):
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Sumarização indisponível."
    try:
        transcript = "\n".join(f"{msg['role']}: {msg['parts'][0]}" for msg in conversation_history)
        prompt = f"Resuma os pontos principais da conversa a seguir em uma frase impessoal:\n\n{transcript}\n\nResumo:"
        # --- MODIFICAÇÃO: Removendo o parâmetro safety_settings da chamada generate_content ---
        response = summarizer_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar conversa: {e}"); return "Erro de sumarização."

def summarize_global_chat(chat_transcript: str) -> str:
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Modelo arquivista indisponível."
    try:
        prompt = f"A seguir está uma transcrição do chat de uma live. Resuma os eventos, piadas e tópicos mais importantes. Ignore spam.\n\n{chat_transcript}\n\nResumo dos Eventos:"
        # --- MODIFICAÇÃO: Removendo o parâmetro safety_settings da chamada generate_content ---
        response = summarizer_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar chat global: {e}"); return "Erro de sumarização global."