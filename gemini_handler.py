# -*- coding: utf-8 -*-
import os
import google.generativeai as genai
from ddgs import DDGS
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import database_handler
import requests
from bs4 import BeautifulSoup
import re

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

    except Exception as e:
        print(f"Erro ao acessar a URL {url}: {e}")
        return f"Erro: Não foi possível acessar a URL. O site pode estar bloqueado ou fora do ar. Erro: {e}"

def generate_interactive_response(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list, hierarchical_memories: list, user_info: str, user_permission: str, current_time: str) -> str:
    if not GEMINI_ENABLED or not interaction_model: return "Erro: Modelo de interação indisponível."
    
    # 1. Montagem do prompt inicial
    prompt_parts = []
    personality_prompt = settings.get('personality_prompt', '')
    
    system_prompt = (
        f"**FATO DO SISTEMA:** A data e hora exatas agora são {current_time}. O usuário que está falando com você é '{user_info}', com permissão '{user_permission}'.\n\n"
        f"**REGRA DE NOMES:** Nomes de usuário não diferenciam maiúsculas/minúsculas. 'Spiq' é o mesmo que 'spiq'.\n\n"
        f"{personality_prompt}"
    )
    search_instructions = (
        "\n\n**REGRAS DE FERRAMENTAS (PRIORIDADE MÁXIMA):**\n"
        "Sua primeira tarefa é SEMPRE avaliar a pergunta. Se a pergunta exigir QUALQUER informação que não esteja na sua memória, sua resposta DEVE SER APENAS o placeholder da ferramenta apropriada. Ignore sua personalidade nesta primeira resposta.\n"
        "1. **BUSCA:** `[SEARCH]termo[/SEARCH]`\n"
        "2. **LEITURA DE URL:** `[READ_URL]url[/READ_URL]`\n"
        "3. **LEMBRETES (Apenas 'master'):** `[CREATE_REMINDER]content;trigger_type;trigger_value;target_user[/CREATE_REMINDER]`"
    )
    prompt_parts.append(system_prompt + search_instructions)
    
    if lorebook:
        lorebook_text = "\n".join(f"- {fact}" for fact in lorebook)
        prompt_parts.append(f"\n--- LOREBOOK ---\n{lorebook_text}")
    if long_term_memories:
        memories_text = "\n".join(f"- {mem}" for mem in long_term_memories)
        prompt_parts.append(f"\n--- MEMÓRIAS COM '{user_info}' ---\n{memories_text}")
    if hierarchical_memories:
        hier_mem_text = "\n".join([f"- {mem['summary']}" for mem in hierarchical_memories if mem.get('summary')])
        prompt_parts.append(f"\n--- MEMÓRIAS GLOBAIS RECENTES ---\n{hier_mem_text}")
        
    prompt_parts.append("\n--- CONVERSA ATUAL ---")
    for item in history:
        role = "Usuário" if item['role'] == 'user' else "Você"
        prompt_parts.append(f"{role}: {item['parts'][0]}")
    
    # 2. Loop de Ferramentas
    max_loops = 3
    current_question = f"Usuário '{user_info}': {question}"
    
    for i in range(max_loops):
        final_prompt = "\n".join(prompt_parts + [current_question, "\nSua resposta:"])
        database_handler.add_live_log("IA PENSANDO", f"Enviando prompt para IA (Iteração {i+1}).")
        
        try:
            response = interaction_model.generate_content(final_prompt, safety_settings=safety_settings)
            text_response = response.text.strip()
            database_handler.add_live_log("IA PENSANDO", f"Resposta bruta da IA: '{text_response}'")

            if text_response.startswith("[SEARCH]") and text_response.endswith("[/SEARCH]"):
                query = text_response.split("[SEARCH]")[1].split("[/SEARCH]")[0].strip()
                context = web_search_ddgs(query)
                current_question = f"**Contexto da Busca (Ferramenta):**\n{context}\n\n**Instrução:** Use o contexto acima para responder a pergunta original do usuário: '{question}'"
                continue # Volta para o início do loop com o novo prompt
            
            elif text_response.startswith("[READ_URL]") and text_response.endswith("[/READ_URL]"):
                url = text_response.split("[READ_URL]")[1].split("[/READ_URL]")[0].strip()
                context = read_url_content(url)
                current_question = f"**Conteúdo da URL (Ferramenta):**\n{context}\n\n**Instrução:** Use o conteúdo acima para responder a pergunta original do usuário: '{question}'"
                continue

            elif text_response.startswith("[CREATE_REMINDER]") and text_response.endswith("[/CREATE_REMINDER]"):
                params_str = text_response.split("[CREATE_REMINDER]")[1].split("[/CREATE_REMINDER]")[0]
                params = [p.strip() for p in params_str.split(';')]
                try:
                    content, trigger_type, trigger_value, target_user = params[0], params[1], params[2], params[3]
                    success = database_handler.save_reminder(created_by=user_info, channel_name=os.getenv('TTV_CHANNEL'),
                                                           trigger_type=trigger_type, trigger_value=trigger_value,
                                                           content=content, target_user=target_user)
                    if success:
                        return f"Entendido! Criei um lembrete para '{content}'."
                    else:
                        return "Não consegui criar o lembrete, ocorreu um erro ao salvar."
                except IndexError:
                    return "Não consegui entender todos os parâmetros para criar o lembrete."
            else:
                return text_response.replace('*', '').replace('`', '').strip()

        except Exception as e:
            print(f"Erro na geração de resposta: {e}"); return "Ocorreu um erro ao pensar."

    return "Puxa, entrei em um loop de ferramentas. Pode reformular a pergunta?"

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