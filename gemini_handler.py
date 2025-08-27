# -*- coding: utf-8 -*-
# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento da IA
# =========================================================================================
# FASE 11: Reativação de Todas as Camadas de Memória
#
# Autor: Seu Nome/Apelido
# Versão: 1.8.3 (Final de Compatibilidade)
# Data: 26/08/2025
#
# Descrição: Reintegra o Lorebook e as memórias de longo prazo/hierárquica
#            dentro da nova estrutura de passagem de histórico, que se provou
#            estável com a biblioteca v0.8.5.
#
# =========================================================================================

import os
import google.generativeai as genai
from ddgs import DDGS

GEMINI_ENABLED = False
interaction_model = None
summarizer_model = None
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

def _generate_response(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list, hierarchical_memories: list, web_context: str) -> str:
    """Função unificada que usa a passagem de histórico via start_chat."""
    try:
        full_history = []
        
        full_history.append({'role': 'user', 'parts': [settings.get('personality_prompt', '')]})
        full_history.append({'role': 'model', 'parts': ["Entendido. Assumirei essa personalidade e seguirei todas as instruções a seguir."]})
        
        if lorebook:
            lorebook_text = "\n".join(f"- {fact}" for fact in lorebook)
            full_history.append({'role': 'user', 'parts': [f"{settings.get('lorebook_prompt', '')}\n{lorebook_text}"]})
            full_history.append({'role': 'model', 'parts': ["Compreendido."]})

        if long_term_memories:
            memories_text = "\n".join(f"- {mem}" for mem in long_term_memories)
            full_history.append({'role': 'user', 'parts': [f"Resumos de conversas passadas comigo:\n{memories_text}"]})
            full_history.append({'role': 'model', 'parts': ["Ok."]})
        
        if hierarchical_memories:
            hier_mem_text = "\n".join(f"- {mem}" for mem in hierarchical_memories)
            full_history.append({'role': 'user', 'parts': [f"Resumos de eventos recentes no chat:\n{hier_mem_text}"]})
            full_history.append({'role': 'model', 'parts': ["Ok."]})
            
        if web_context:
            full_history.append({'role': 'user', 'parts': [web_context]})
            full_history.append({'role': 'model', 'parts': ["Obrigado pelo contexto da web."]})

        full_history.extend(history)
        
        chat = interaction_model.start_chat(history=full_history)
        
        response = chat.send_message(question, safety_settings=safety_settings)
        
        if not response.parts:
            print("AVISO: Resposta bloqueada por segurança.")
            return "Minha resposta foi bloqueada. Tente outro assunto."
            
        return response.text.replace('*', '').replace('`', '').strip()
        
    except Exception as e:
        if "response.text" in str(e):
             print("AVISO: Resposta bloqueada por segurança (exceção).")
             return "Minha resposta foi bloqueada."
        print(f"Erro na geração de resposta: {e}"); return "Ocorreu um erro ao pensar."

def generate_response_without_search(question, history, settings, lorebook, long_term_memories, hierarchical_memories):
    return _generate_response(question, history, settings, lorebook, long_term_memories, hierarchical_memories, "")

def generate_response_with_search(question, history, settings, lorebook, long_term_memories, hierarchical_memories, web_context):
    return _generate_response(question, history, settings, lorebook, long_term_memories, hierarchical_memories, web_context)
    
def summarize_conversation(conversation_history):
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Sumarização indisponível."
    try:
        transcript = "\n".join(f"{msg['role']}: {msg['parts'][0]}" for msg in conversation_history)
        prompt = f"Resuma os pontos principais da conversa a seguir em uma frase impessoal:\n\n{transcript}\n\nResumo:"
        response = summarizer_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar conversa: {e}"); return "Erro de sumarização."

def summarize_global_chat(chat_transcript: str) -> str:
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Modelo arquivista indisponível."
    try:
        prompt = f"A seguir está uma transcrição do chat de uma live. Resuma os eventos, piadas e tópicos mais importantes. Ignore spam.\n\n{chat_transcript}\n\nResumo dos Eventos:"
        response = summarizer_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar chat global: {e}"); return "Erro de sumarização global."