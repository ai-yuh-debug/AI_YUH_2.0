# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento da IA
# =========================================================================================
# FASE 6: O Ciclo Completo da Memória e Busca na Web
#
# Autor: Seu Nome/Apelido
# Versão: 1.3.0
# Data: 26/08/2025
#
# Descrição: Adiciona uma função de busca na web e a integra ao prompt,
#            junto com as memórias de longo prazo, para dar à IA um
#            conhecimento abrangente e atualizado.
#
# =========================================================================================

import os
import google.generativeai as genai
from duckduckgo_search import DDGS # NOVA IMPORTAÇÃO

# ... (Configuração das IAs como antes) ...
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

def load_interaction_model(model_name: str):
    # ... (código inalterado) ...
    global interaction_model
    try:
        interaction_model = genai.GenerativeModel(model_name=model_name, safety_settings=safety_settings)
        print(f"Modelo de interação '{model_name}' carregado com sucesso.")
    except Exception as e:
        print(f"ERRO ao carregar o modelo de interação '{model_name}': {e}")
        global GEMINI_ENABLED
        GEMINI_ENABLED = False

# --- NOVA FUNÇÃO DE BUSCA NA WEB ---
def web_search(query: str, num_results: int = 3) -> str:
    """Realiza uma busca na web e retorna um resumo dos resultados."""
    print(f"Realizando busca na web por: '{query}'")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=num_results)]
        
        if not results:
            return "Nenhum resultado encontrado na busca."
            
        # Formata os resultados para injeção no prompt
        formatted_results = "\n".join(f"- {res['body']}" for res in results)
        return f"Aqui estão alguns resultados da busca na web sobre '{query}':\n{formatted_results}"
    except Exception as e:
        print(f"Erro na busca da web: {e}")
        return "Ocorreu um erro ao tentar buscar na web."


def generate_response(question: str, history: list, settings: dict, lorebook: list, long_term_memories: list, web_context: str) -> str:
    """Gera uma resposta da IA usando todo o contexto disponível."""
    if not GEMINI_ENABLED or not interaction_model:
        return "Desculpe, meu cérebro de interação está offline."

    try:
        # --- Construção do Prompt Final ---
        full_prompt = []
        # 1. Personalidade
        full_prompt.append({'role': 'user', 'parts': [settings.get('personality_prompt', '')]})
        full_prompt.append({'role': 'model', 'parts': ["Entendido. Assumirei essa personalidade."]})
        
        # 2. Lorebook
        if lorebook:
            lorebook_text = "\n".join(f"- {fact}" for fact in lorebook)
            full_prompt.append({'role': 'user', 'parts': [f"{settings.get('lorebook_prompt', '')}\n{lorebook_text}"]})
            full_prompt.append({'role': 'model', 'parts': ["Compreendido."]})

        # 3. Memórias de Longo Prazo
        if long_term_memories:
            memories_text = "\n".join(f"- {mem}" for mem in long_term_memories)
            full_prompt.append({'role': 'user', 'parts': [f"Para referência, aqui estão alguns resumos de suas conversas passadas comigo:\n{memories_text}"]})
            full_prompt.append({'role': 'model', 'parts': ["Ok, vou considerar essas memórias."]})
        
        # 4. Contexto da Busca na Web
        if web_context:
            full_prompt.append({'role': 'user', 'parts': [f"Para te ajudar a responder, aqui está um contexto atualizado da internet:\n{web_context}"]})
            full_prompt.append({'role': 'model', 'parts': ["Obrigado pelo contexto da web."]})

        # 5. Histórico da conversa atual
        full_prompt.extend(history)
        
        convo = interaction_model.start_chat(history=full_prompt)
        convo.send_message(question)
        
        response_text = convo.last.text.replace('*', '').replace('`', '').strip()
        return response_text[:480]

    except Exception as e:
        print(f"Erro ao gerar resposta da IA: {e}")
        return "Ocorreu um erro enquanto eu pensava."


def summarize_conversation(conversation_history: list) -> str:
    # ... (código inalterado) ...
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Módulo de sumarização indisponível."
    try:
        transcript = "\n".join(f"{msg['role']}: {msg['parts'][0]}" for msg in conversation_history)
        prompt = f"Resuma os pontos principais da seguinte conversa em uma única frase impessoal:\n\n{transcript}\n\nResumo:"
        response = summarizer_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar conversa: {e}")
        return f"Erro de sumarização."