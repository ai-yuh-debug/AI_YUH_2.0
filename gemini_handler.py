# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento da IA
# =========================================================================================
# FASE 6: O Ciclo Completo da Memória e Busca na Web (MIGRADO)
#
# Autor: Seu Nome/Apelido
# Versão: 2.0.0 (Migrado para google-cloud-aiplatform)
# Data: 26/08/2025
#
# Descrição: O módulo foi completamente refatorado para usar a biblioteca
#            oficial e moderna 'google-cloud-aiplatform', resolvendo os
#            problemas de dependência e nos alinhando com as melhores práticas
#            atuais do Google.
#
# =========================================================================================

import os
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, Part
import vertexai.preview.generative_models as generative_models
from ddgs import DDGS

GEMINI_ENABLED = False
interaction_model = None
summarizer_model = None

try:
    # A nova biblioteca exige que você configure o projeto e a localização do GCP
    # Eles podem ser definidos como variáveis de ambiente ou aqui.
    # Para o AI Studio, isso geralmente não é necessário, pois a autenticação é gerenciada.
    # Mas é uma boa prática estar ciente disso.
    # vertexai.init(project="SEU_GCP_PROJECT_ID", location="us-central1")

    # Modelo principal para interação com o usuário (configurável via DB)
    interaction_model_name = "gemini-2.5-flash" # Placeholder, será sobreposto pelo DB

    # Modelo secundário, otimizado para tarefas de sumarização (fixo)
    summarizer_model = GenerativeModel("gemini-1.5-flash")

    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }

    print("Módulo Vertex AI (Gemini) inicializado.")
    GEMINI_ENABLED = True

except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível inicializar o módulo Vertex AI. Erro: {e}")
    print("Isso pode exigir autenticação via gcloud: 'gcloud auth application-default login'")

def load_interaction_model(model_name: str, use_native_search: bool):
    """Carrega o modelo de IA, ativando a busca nativa com a sintaxe correta."""
    global interaction_model
    try:
        tools = None
        if use_native_search:
            # A sintaxe é a mesma, mas agora usa a classe da biblioteca correta
            google_search_tool = Tool.from_google_search_retrieval({})
            tools = [google_search_tool]
        
        interaction_model = GenerativeModel(model_name, tools=tools)
        
        search_status = "com" if use_native_search else "sem"
        print(f"Modelo de interação '{model_name}' carregado {search_status} a ferramenta 'google_search'.")

    except Exception as e:
        print(f"ERRO ao carregar o modelo de interação '{model_name}': {e}")
        global GEMINI_ENABLED
        GEMINI_ENABLED = False

def web_search_fallback(query: str, num_results: int = 3) -> str:
    """Realiza uma busca na web usando DDGS como fallback."""
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

        # A nova biblioteca constrói o histórico de forma um pouco diferente
        # O histórico agora é uma lista de objetos 'Content'
        system_instructions = []
        system_instructions.append(Part.from_text(settings.get('personality_prompt', '')))
        
        if lorebook:
            lorebook_text = "\n".join(f"- {fact}" for fact in lorebook)
            system_instructions.append(Part.from_text(f"{settings.get('lorebook_prompt', '')}\n{lorebook_text}"))
        
        if long_term_memories:
            memories_text = "\n".join(f"- {mem}" for mem in long_term_memories)
            system_instructions.append(Part.from_text(f"Resumos de conversas passadas:\n{memories_text}"))
        
        if web_context:
            system_instructions.append(Part.from_text(f"Contexto da web:\n{web_context}"))
        
        # A biblioteca vertexai usa um parâmetro `system_instruction`
        chat = interaction_model.start_chat(history=[])
        
        response = chat.send_message(
            [f"**Instruções do Sistema (Aja como se eu não estivesse vendo isso):**\n{' '.join(p.text for p in system_instructions)}\n\n**Histórico da Conversa:**\n{' '.join(h.text for h in history)}\n\n**Nova Pergunta do Usuário:**\n{question}"],
            generation_config={"max_output_tokens": 256, "temperature": 0.9},
            safety_settings=safety_settings,
        )

        response_text = response.text.replace('*', '').replace('`', '').strip()
        return response_text[:480]

    except Exception as e:
        print(f"Erro ao gerar resposta da IA: {e}"); return "Ocorreu um erro enquanto eu pensava."

def summarize_conversation(conversation_history: list) -> str:
    if not GEMINI_ENABLED or not summarizer_model: return "Erro: Sumarização indisponível."
    try:
        transcript = "\n".join(f"{msg.role}: {msg.parts[0].text}" for msg in conversation_history)
        prompt = f"Resuma os pontos principais da conversa a seguir em uma frase impessoal:\n\n{transcript}\n\nResumo:"
        response = summarizer_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erro ao sumarizar conversa: {e}"); return "Erro de sumarização."