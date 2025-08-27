# -*- coding: utf-8 -*-

import os
import google.generativeai as genai
from google.generativeai.types import Tool
from ddgs import DDGS

GEMINI_ENABLED = False
interaction_model = None
summarizer_model = None

try:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=GEMINI_API_KEY)
    summarizer_model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
    print("Módulo Gemini inicializado.")
    GEMINI_ENABLED = True
except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível inicializar o módulo Gemini. Erro: {e}")

def load_interaction_model(model_name: str, use_native_search: bool):
    global interaction_model
    try:
        tools = None
        if use_native_search:
            google_search_tool = Tool.from_google_search_retrieval({})
            tools = [google_search_tool]
        
        interaction_model = genai.GenerativeModel(
            model_name=model_name, 
            safety_settings=safety_settings,
            tools=tools
        )
        
        search_status = "com" if use_native_search else "sem"
        print(f"Modelo de interação '{model_name}' carregado {search_status} a ferramenta 'google_search'.")

    except Exception as e:
        print(f"ERRO ao carregar o modelo de interação '{model_name}': {e}")
        global GEMINI_ENABLED
        GEMINI_ENABLED = False

def web_search_fallback(query: str, num_results: int = 3) -> str:
    print(f"Usando fallback DDGS para buscar por: '{query}'")
    try:
        results = DDGS().text(query, max_results=num_results)
        if not results: return ""
        return f"Resultados da busca na web sobre '{query}':\n" + "\n".join(f"- {res['body']}" for res in results)
    except Exception as e:
        print(f"Erro na busca fallback (DDGS): {e}"); return ""

def generate_response(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list) -> str:
    if not GEMINI_ENABLED or not interaction_model:
        return "Desculpe, meu cérebro de interação está offline."
    try:
        use_native_search = settings.get('use_native_google_search', True)
        web_context = ""

        if not use_native_search:
            web_context = web_search_fallback(question)
        
        full_prompt = []
        full_prompt.append({'role': 'user', 'parts': [settings.get('personality_prompt', '')]})
        full_prompt.append({'role': 'model', 'parts': ["Entendido. Assumirei essa personalidade."]})
        
        if lorebook:
            lorebook_text = "\n".join(f"- {fact}" for fact in lorebook)
            full_prompt.append({'role': 'user', 'parts': [f"{settings.get('lorebook_prompt', '')}\n{lorebook_text}"]})
            full_prompt.append({'role': 'model', 'parts': ["Compreendido."]})
        if long_term_memories:
            memories_text = "\n".join(f"- {mem}" for mem in long_term_memories)
            full_prompt.append({'role': 'user', 'parts': [f"Para referência, aqui estão alguns resumos de suas conversas passadas comigo:\n{memories_text}"]})
            full_prompt.append({'role': 'model', 'parts': ["Ok, vou considerar essas memórias."]})
        
        if web_context:
            full_prompt.append({'role': 'user', 'parts': [f"Para te ajudar a responder, aqui está um contexto atualizado da internet:\n{web_context}"]})
            full_prompt.append({'role': 'model', 'parts': ["Obrigado pelo contexto da web."]})

        full_prompt.extend(history)
        
        convo = interaction_model.start_chat(history=full_prompt)
        response = convo.send_message(question)
        
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