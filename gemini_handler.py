# -*- coding: utf-8 -*-
import os
import google.generativeai as genai
from ddgs import DDGS
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import database_handler

GEMINI_ENABLED = False
interaction_model = None
summarizer_model = None
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

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
        interaction_model_name = settings.get('interaction_model', 'gemini-1.5-flash-latest')
        archivist_model_name = settings.get('archivist_model', 'gemini-1.5-flash-latest')
        interaction_model = genai.GenerativeModel(model_name=interaction_model_name)
        summarizer_model = genai.GenerativeModel(model_name=archivist_model_name)
        print(f"Modelo de interação '{interaction_model_name}' carregado.")
        print(f"Modelo arquivista '{archivist_model_name}' carregado.")
    except Exception as e:
        print(f"ERRO ao carregar modelos de IA: {e}"); global GEMINI_ENABLED; GEMINI_ENABLED = False

def web_search_ddgs(query: str, num_results: int = 3) -> str:
    database_handler.add_live_log("IA PENSANDO", f"Executando busca DDGS por: '{query}'")
    try:
        results = DDGS().text(query, max_results=num_results)
        if not results: return "Nenhum resultado encontrado na web."
        return "Contexto da busca na web:\n" + "\n".join(f"- {res['title']}: {res['body']}" for res in results)
    except Exception as e:
        print(f"Erro na busca DDGS: {e}"); return "Erro ao tentar buscar na web."

def generate_interactive_response(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list, hierarchical_memories: list) -> str:
    if not GEMINI_ENABLED or not interaction_model: return "Erro: Modelo de interação indisponível."
    
    full_history = []
    personality_prompt = settings.get('personality_prompt', '')
    search_instructions = (
        "\n\n**REGRA CRÍTICA DE BUSCA:** Sua primeira tarefa é avaliar a pergunta do usuário. Se a pergunta exigir "
        "qualquer tipo de conhecimento externo ou atual (notícias, datas, fatos específicos que não estariam no seu Lorebook), "
        "sua PRIMEIRA E ÚNICA resposta DEVE ser `[SEARCH]termo de busca otimizado[/SEARCH]`. "
        "NÃO tente responder de outra forma. NÃO se desculpe. NÃO adicione texto extra. A falha em seguir esta regra resultará em um erro."
    )
    full_history.append({'role': 'user', 'parts': [personality_prompt + search_instructions]})
    full_history.append({'role': 'model', 'parts': ["REGRA COMPREENDIDA. Se for necessário conhecimento externo, minha única resposta inicial será `[SEARCH]query[/SEARCH]`."]})
    
    if lorebook:
        lorebook_text = "\n".join(f"- {fact}" for fact in lorebook)
        full_history.append({'role': 'user', 'parts': [f"{settings.get('lorebook_prompt', '')}\n{lorebook_text}"]})
        full_history.append({'role': 'model', 'parts': ["Lorebook assimilado."]})
    if long_term_memories:
        memories_text = "\n".join(f"- {mem}" for mem in long_term_memories)
        full_history.append({'role': 'user', 'parts': [f"Resumos de conversas passadas com este usuário:\n{memories_text}"]})
        full_history.append({'role': 'model', 'parts': ["Memórias do usuário assimiladas."]})
    if hierarchical_memories:
        hier_mem_text = "\n".join(f"- {mem['summary']}" for mem in hierarchical_memories) # Acessa a chave 'summary'
        full_history.append({'role': 'user', 'parts': [f"Resumos de eventos recentes no chat:\n{hier_mem_text}"]})
        full_history.append({'role': 'model', 'parts': ["Memórias do chat assimiladas."]})
        
    full_history.extend(history)
    chat = interaction_model.start_chat(history=full_history)
    
    try:
        database_handler.add_live_log("IA PENSANDO", f"Pergunta para IA: '{question}'")
        response = chat.send_message(question, safety_settings=safety_settings)
        initial_text = response.text.strip()
        database_handler.add_live_log("IA PENSANDO", f"Resposta bruta da IA: '{initial_text}'")
        
        if initial_text.startswith("[SEARCH]") and initial_text.endswith("[/SEARCH]"):
            query = initial_text.split("[SEARCH]")[1].split("[/SEARCH]")[0].strip()
            search_context = web_search_ddgs(query)
            database_handler.add_live_log("IA PENSANDO", f"Contexto da busca retornado para a IA.")
            
            final_prompt_parts = ["Com base nos resultados da pesquisa a seguir, formule sua resposta final para o usuário.", search_context]
            response = chat.send_message(final_prompt_parts, safety_settings=safety_settings)
            
        if not response.parts: return "Minha resposta foi bloqueada por segurança."
        final_text = response.text.replace('*', '').replace('`', '').strip()
        database_handler.add_live_log("IA PENSANDO", f"Resposta final para o usuário: '{final_text}'")
        return final_text
        
    except Exception as e:
        print(f"Erro na geração de resposta: {e}"); return "Ocorreu um erro ao pensar."
        
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