# gemini_handler.py

import os
import google.generativai as genai
from duckduckgo_search import DDGS
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

def get_generative_model(model_name: str):
    try:
        return genai.GenerativeModel(model_name=model_name, safety_settings=safety_settings)
    except Exception as e:
        print(f"Erro ao criar modelo {model_name}: {e}")
        return None

def perform_search(query: str, max_results: int = 3):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
            if not results: return "Nenhum resultado encontrado na web."
            
            formatted = "Resultados da pesquisa na web:\n"
            for i, res in enumerate(results):
                formatted += f"[{i+1}] Título: {res.get('title', 'N/A')}\n   Conteúdo: {res.get('body', 'N/A')}\n\n"
            return formatted
    except Exception as e:
        print(f"Erro na busca DDGS: {e}")
        return "Ocorreu um erro ao pesquisar na web."

def get_interaction_response(model, user_query: str, author: str, system_prompt: str, lorebook_context: str, memory_context: str = ""):
    try:
        decision_prompt = f"O usuário '{author}' perguntou: '{user_query}'. Preciso de informações atuais da internet para responder? Responda apenas 'SIM' ou 'NÃO'."
        decision_response = model.generate_content(decision_prompt)
        decision = decision_response.text.strip().upper()
        search_results = ""
        if "SIM" in decision:
            print("IA decidiu pesquisar na web.")
            search_results = perform_search(user_query)
        else:
            print("IA decidiu não pesquisar na web.")

        # PROMPT RESTAURADO PARA A VERSÃO MAIS EXPLÍCITA
        final_prompt = f"""
        {system_prompt}

        Contexto da memória de longo prazo (eventos passados):
        {memory_context if memory_context else "Nenhuma memória de longo prazo disponível."}

        Fatos importantes do Lorebook que você deve sempre lembrar:
        {lorebook_context if lorebook_context else "Nenhum fato no Lorebook."}
        
        {search_results if search_results else ""}

        Agora, responda à pergunta do usuário '{author}': {user_query}
        """
        
        final_response = model.generate_content(final_prompt)
        return final_response.text
    except Exception as e:
        print(f"Erro ao gerar resposta de interação: {e}")
        return "Desculpe, tive um problema para processar sua pergunta."

def get_summary_response(model, text_to_summarize: str, level: str, start_date: str, end_date: str):
    # PROMPT RESTAURADO PARA A VERSÃO MAIS EXPLÍCITA
    prompt = f"""
    Você é uma IA arquivista. Sua tarefa é ler o log de um chat da Twitch e criar um resumo conciso e factual dos eventos mais importantes.
    O resumo é para o nível de memória: '{level}', cobrindo o período de {start_date} até {end_date}.

    Log do Chat para resumir:
    ---
    {text_to_summarize}
    ---

    Crie um resumo claro em um único parágrafo.

    Resumo Gerado:
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erro ao gerar resumo: {e}")
        return f"Não foi possível gerar o resumo para o período de {start_date} a {end_date}."