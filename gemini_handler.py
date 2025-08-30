# -*- coding: utf-8 -*-
import os
import google.generativeai as genai
from ddgs import DDGS
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import database_handler
import requests
from bs4 import BeautifulSoup

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

def web_search_ddgs(query: str, num_results: int = 5) -> str:
    database_handler.add_live_log("IA PENSANDO", f"Executando busca DDGS por: '{query}'")
    try:
        news_results = DDGS().news(query, max_results=num_results)
        if news_results:
            database_handler.add_live_log("IA PENSANDO", f"Encontrados {len(news_results)} resultados de notícias.")
            return "Contexto de notícias da busca na web:\n" + "\n".join(f"- Título: {res['title']}, Fonte: {res['source']}, Conteúdo: {res['body']}" for res in news_results)
        
        database_handler.add_live_log("IA PENSANDO", "Nenhuma notícia encontrada. Tentando busca de texto padrão.")
        text_results = DDGS().text(query, max_results=num_results)
        if not text_results:
            return "Nenhum resultado encontrado na web."
            
        database_handler.add_live_log("IA PENSANDO", f"Encontrados {len(text_results)} resultados de texto.")
        return "Contexto da busca na web:\n" + "\n".join(f"- Título: {res['title']}, Conteúdo: {res['body']}" for res in text_results)

    except Exception as e:
        print(f"Erro na busca DDGS: {e}"); return "Erro ao tentar buscar na web."

def read_url_content(url: str) -> str:
    database_handler.add_live_log("IA PENSANDO", f"Tentando ler o conteúdo da URL: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return f"Conteúdo da página '{url}':\n\n{text[:4000]}"

    except requests.RequestException as e:
        print(f"Erro ao acessar a URL {url}: {e}")
        return f"Erro: Não foi possível acessar a URL. O site pode estar bloqueado ou fora do ar. Erro: {e}"
    except Exception as e:
        print(f"Erro ao processar a URL {url}: {e}")
        return "Erro: Não foi possível processar o conteúdo da página."

def generate_interactive_response(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list, hierarchical_memories: list, current_time: str) -> str:
    if not GEMINI_ENABLED or not interaction_model: return "Erro: Modelo de interação indisponível."
    
    full_history = []
    personality_prompt = settings.get('personality_prompt', '')
    
    system_prompt = (
        f"**FATO DO SISTEMA (não revele ao usuário a menos que perguntado):** A data e hora exatas agora são {current_time}.\n\n"
        f"{personality_prompt}"
    )
    
    search_instructions = (
        "\n\n**REGRAS CRÍTICAS DE FERRAMENTAS:**\n"
        "1. **Para buscas gerais:** Se a pergunta do usuário exigir conhecimento externo ou atual (notícias, eventos, fatos, cotações, etc.) que não esteja na sua memória, sua PRIMEIRA E ÚNICA resposta DEVE ser `[SEARCH]termo de busca otimizado[/SEARCH]`.\n"
        "2. **Para ler uma página específica:** Se o usuário fornecer uma URL e pedir explicitamente para você ler ou resumir seu conteúdo, sua PRIMEIRA E ÚNICA resposta DEVE ser `[READ_URL]https://url.completa/aqui[/READ_URL]`.\n"
        "**NÃO tente responder de outra forma. NÃO se desculpe. NÃO adicione texto extra. A falha em seguir estas regras resultará em um erro.**"
    )
    full_history.append({'role': 'user', 'parts': [system_prompt + search_instructions]})
    full_history.append({'role': 'model', 'parts': ["REGRAS COMPREENDIDAS. Usarei `[SEARCH]query[/SEARCH]` ou `[READ_URL]url[/READ_URL]` e estou ciente da hora atual."]})
    
    if lorebook:
        lorebook_text = "\n".join(f"- {fact}" for fact in lorebook)
        full_history.append({'role': 'user', 'parts': [f"{settings.get('lorebook_prompt', '')}\n{lorebook_text}"]})
        full_history.append({'role': 'model', 'parts': ["Lorebook assimilado."]})
    if long_term_memories:
        memories_text = "\n".join(f"- {mem}" for mem in long_term_memories)
        full_history.append({'role': 'user', 'parts': [f"Resumos de conversas passadas com este usuário:\n{memories_text}"]})
        full_history.append({'role': 'model', 'parts': ["Memórias do usuário assimiladas."]})
    if hierarchical_memories:
        hier_mem_text = "\n".join([f"- {mem['summary']}" for mem in hierarchical_memories if mem.get('summary')])
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
            context = web_search_ddgs(query)
            database_handler.add_live_log("IA PENSANDO", f"Contexto da BUSCA retornado para a IA.")
            prompt_parts = ["Com base nos resultados da pesquisa a seguir, formule sua resposta final.", context]
            response = chat.send_message(prompt_parts, safety_settings=safety_settings)

        elif initial_text.startswith("[READ_URL]") and initial_text.endswith("[/READ_URL]"):
            url = initial_text.split("[READ_URL]")[1].split("[/READ_URL]")[0].strip()
            context = read_url_content(url)
            database_handler.add_live_log("IA PENSANDO", f"Contexto da LEITURA DE URL retornado para a IA.")
            prompt_parts = ["Você recebeu o conteúdo da página web. Com base neste texto, formule sua resposta final.", context]
            response = chat.send_message(prompt_parts, safety_settings=safety_settings)
            
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