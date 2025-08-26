# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Módulo de Gerenciamento da IA
# =========================================================================================
# FASE 5: A IA de Gerenciamento de Memória e o Ciclo de Vida
#
# Autor: Seu Nome/Apelido
# Versão: 1.2.0
# Data: 26/08/2025
#
# Descrição: O handler da IA agora constrói prompts complexos injetando
#            personalidade e lorebook. Também introduz um segundo modelo de IA,
#            mais simples, dedicado à tarefa de sumarizar conversas.
#
# =========================================================================================

import os
import google.generativeai as genai

# --- Configuração das IAs ---
GEMINI_ENABLED = False
interaction_model = None
summarizer_model = None

try:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Modelo principal para interação com o usuário (configurável via DB)
    interaction_model_config = {
        "temperature": 0.9, "top_p": 1, "top_k": 1, "max_output_tokens": 256,
    }

    # Modelo secundário, otimizado para tarefas de sumarização (fixo)
    summarizer_model = genai.GenerativeModel(model_name="gemini-1.5-flash") # Usando um modelo rápido

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        # ... (outras configurações de segurança)
    ]
    
    print("Módulo Gemini inicializado. O modelo de interação será carregado do DB.")
    GEMINI_ENABLED = True

except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível inicializar o módulo Gemini. Erro: {e}")

def load_interaction_model(model_name: str):
    """Carrega o modelo de IA de interação especificado."""
    global interaction_model
    try:
        interaction_model = genai.GenerativeModel(
            model_name=model_name,
            # generation_config=interaction_model_config, # Configs serão aplicadas na chamada
            safety_settings=safety_settings
        )
        print(f"Modelo de interação '{model_name}' carregado com sucesso.")
    except Exception as e:
        print(f"ERRO ao carregar o modelo de interação '{model_name}': {e}")
        global GEMINI_ENABLED
        GEMINI_ENABLED = False

def generate_response(question: str, history: list, settings: dict, lorebook: list) -> str:
    """Gera uma resposta da IA usando todo o contexto disponível."""
    if not GEMINI_ENABLED or not interaction_model:
        return "Desculpe, meu cérebro de interação está offline no momento."

    try:
        # --- Construção do Prompt Final ---
        full_prompt = []
        # 1. Adiciona a personalidade
        full_prompt.append({'role': 'user', 'parts': [settings.get('personality_prompt', '')]})
        full_prompt.append({'role': 'model', 'parts': ["Entendido. Assumirei essa personalidade."]})
        
        # 2. Adiciona o lorebook
        if lorebook:
            lorebook_text = "\n".join(f"- {fact}" for fact in lorebook)
            full_prompt.append({'role': 'user', 'parts': [f"{settings.get('lorebook_prompt', '')}\n{lorebook_text}"]})
            full_prompt.append({'role': 'model', 'parts': ["Compreendido. Considerarei estes fatos como verdades absolutas."]})

        # 3. Adiciona o histórico da conversa
        full_prompt.extend(history)
        
        # Inicia o chat com todo o contexto construído
        convo = interaction_model.start_chat(history=full_prompt)
        convo.send_message(question)
        
        response_text = convo.last.text.replace('*', '').replace('`', '').strip()
        return response_text[:480]

    except Exception as e:
        print(f"Erro ao gerar resposta da IA: {e}")
        return "Ocorreu um erro enquanto eu pensava na sua pergunta."

def summarize_conversation(conversation_history: list) -> str:
    """Usa a IA secundária para sumarizar uma conversa."""
    if not GEMINI_ENABLED or not summarizer_model:
        return "Erro: Módulo de sumarização indisponível."

    try:
        # Converte o histórico para um formato de texto simples
        transcript = "\n".join(f"{msg['role']}: {msg['parts'][0]}" for msg in conversation_history)
        
        prompt = f"""
        A seguir está a transcrição de uma curta conversa com um usuário em um chat da Twitch.
        Sua tarefa é criar um resumo conciso e impessoal dos pontos principais da conversa em uma única frase.
        Este resumo será usado como memória de longo prazo. Ignore saudações e foque nos fatos.

        Transcrição:
        {transcript}

        Resumo conciso:
        """
        
        response = summarizer_model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print(f"Erro ao sumarizar conversa: {e}")
        return f"Erro de sumarização: {e}"