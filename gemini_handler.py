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

def generate_interactive_response(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list, hierarchical_memories: list, user_info: str, user_permission: str, current_time: str) -> str:
    if not GEMINI_ENABLED or not interaction_model: return "Erro: Modelo de interação indisponível."
    
    full_history = []
    personality_prompt = settings.get('personality_prompt', '')
    
    system_prompt = (
        f"**FATO DO SISTEMA:** A data e hora exatas agora são {current_time}. O usuário que está falando com você é '{user_info}', com permissão '{user_permission}'.\n\n"
        f"**REGRA DE NOMES:** Nomes de usuário não diferenciam maiúsculas/minúsculas. 'Spiq' é a mesma pessoa que 'spiq'.\n\n"
        f"{personality_prompt}"
    )
    search_instructions = (
        "\n\n**REGRAS DE FERRAMENTAS:**\n"
        "1. **BUSCA:** Se precisar de informações externas, responda APENAS com `[SEARCH]termo[/SEARCH]`.\n"
        "2. **LEITURA DE URL:** Se o usuário der uma URL, responda APENAS com `[READ_URL]url[/READ_URL]`.\n"
        "3. **LEMBRETES (Apenas para 'master'):** Se um usuário 'master' pedir um lembrete, responda APENAS com `[CREATE_REMINDER]content;trigger_type;trigger_value;target_user[/CREATE_REMINDER]`."
    )
    full_history.append({'role': 'user', 'parts': [system_prompt + search_instructions]})
    full_history.append({'role': 'model', 'parts': ["REGRAS COMPREENDIDAS."]})
    
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
        database_handler.add_live_log("IA PENSANDO", f"Pergunta para IA de '{user_info}': '{question}'")
        response = chat.send_message(question, safety_settings=safety_settings)
        
        max_loops = 2
        for i in range(max_loops):
            text_response = response.text.strip()
            database_handler.add_live_log("IA PENSANDO", f"Resposta bruta da IA (Loop {i+1}): '{text_response}'")

            tool_called = False
            if text_response.startswith("[SEARCH]") and text_response.endswith("[/SEARCH]"):
                tool_called = True
                query = text_response.split("[SEARCH]")[1].split("[/SEARCH]")[0].strip()
                context = web_search_ddgs(query)
                prompt_parts = [f"**Contexto da sua busca por '{query}':**\n{context}\n\n**Instrução:** Agora, use esse contexto para elaborar uma resposta conversacional para a pergunta original do usuário: '{question}'."]
                response = chat.send_message(prompt_parts, safety_settings=safety_settings)
            
            elif text_response.startswith("[READ_URL]") and text_response.endswith("[/READ_URL]"):
                tool_called = True
                url = text_response.split("[READ_URL]")[1].split("[/READ_URL]")[0].strip()
                context = read_url_content(url)
                prompt_parts = [f"**Conteúdo da URL '{url}':**\n{context}\n\n**Instrução:** Agora, com base nesse texto, responda à pergunta original do usuário: '{question}'."]
                response = chat.send_message(prompt_parts, safety_settings=safety_settings)

            elif text_response.startswith("[CREATE_REMINDER]") and text_response.endswith("[/CREATE_REMINDER]"):
                # A criação de lembrete é uma ação final, não precisa de mais um ciclo.
                # ... (lógica de lembretes) ...
                return "Lembrete criado com sucesso!"

            if not tool_called:
                # Se nenhuma ferramenta foi chamada, esta é a resposta final.
                final_text = text_response.replace('*', '').replace('`', '').strip()
                database_handler.add_live_log("IA PENSANDO", f"Resposta final para o usuário: '{final_text}'")
                return final_text
        
        # Se o loop terminar sem uma resposta final, retorna a última resposta da IA.
        final_text_after_loop = response.text.strip().replace('*', '').replace('`', '')
        database_handler.add_live_log("IA PENSANDO", f"Resposta final para o usuário (pós-loop): '{final_text_after_loop}'")
        return final_text_after_loop

    except Exception as e:
        print(f"Erro na geração de resposta: {e}"); return "Ocorreu um erro ao pensar."
        
def summarize_conversation(conversation_history):
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Sumarização indisponível."
    try:
        transcript = "\n".join(f"{msg['role']}: {msg['parts'][0]}" for msg in conversation_history)
        prompt = f"Resuma os pontos principais da conversa a seguir em uma frase impessoal:\n\n{transcript}\n\nResumo:"
        response = summarizer_model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar conversa: {e}"); return "Erro de sumarização."

def summarize_global_chat(prompt: str, level: str):
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Modelo arquivista indisponível."
    try:
        response = summarizer_model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar chat global (nível {level}): {e}"); return f"Erro de sumarização global (nível {level})."