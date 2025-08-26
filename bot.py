# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Twitch Bot com Memória Generativa
# =========================================================================================
# FASE 6: O Ciclo Completo da Memória e Busca na Web (HÍBRIDO)
#
# Autor: Seu Nome/Apelido
# Versão: 1.9.0 (Busca Híbrida e Configurável)
# Data: 26/08/2025
#
# Descrição: O bot agora carrega a configuração de busca do DB e passa
#            para o handler da IA, que decide qual método de busca usar.
#
# =========================================================================================

import os
import socket
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
import gemini_handler
import database_handler

# --- Configurações & Variáveis Globais (inalterado) ---
TTV_TOKEN = os.getenv('TTV_TOKEN')
BOT_NICK = os.getenv('BOT_NICK').lower()
TTV_CHANNEL = os.getenv('TTV_CHANNEL').lower()
HOST = "irc.chat.twitch.tv"
PORT = 6667
BOT_SETTINGS = {}
LOREBOOK = []
short_term_memory = {}
MEMORY_EXPIRATION_MINUTES = 5
MAX_HISTORY_LENGTH = 10

# --- Funções Auxiliares (inalterado) ---
def send_chat_message(sock, message):
    try: sock.send(f"PRIVMSG #{TTV_CHANNEL} :{message}\n".encode('utf-8'))
    except Exception as e: print(f"Erro ao enviar mensagem: {e}")

def cleanup_inactive_memory():
    now = datetime.now()
    inactive_users = [
        user for user, data in short_term_memory.items()
        if now - data['last_interaction'] > timedelta(minutes=MEMORY_EXPIRATION_MINUTES)
    ]
    for user in inactive_users:
        print(f"Usuário {user} inativo. Sumarizando e salvando memória...")
        user_memory = short_term_memory.pop(user)
        summary = gemini_handler.summarize_conversation(user_memory['history'])
        database_handler.save_long_term_memory(user, summary)

def process_message(sock, raw_message):
    if "PRIVMSG" not in raw_message: return
    try:
        source, _, message_body = raw_message.partition('PRIVMSG')
        user_info = source.split('!')[0][1:]
        message_content = message_body.split(':', 1)[1].strip()
        if user_info.lower() == BOT_NICK: return
        print(f"CHAT | {user_info}: {message_content}")
        user_permission = database_handler.get_user_permission(user_info)
        if user_permission == 'blacklist': return

        msg_lower = message_content.lower()
        learn_command = "!learn "
        if msg_lower.startswith(learn_command):
            # ... (lógica do !learn inalterada) ...
            if user_permission == 'master':
                fact_to_learn = message_content[len(learn_command):].strip()
                if fact_to_learn:
                    success = database_handler.add_lorebook_entry(fact_to_learn, user_info)
                    if success: LOREBOOK.append(fact_to_learn); send_chat_message(sock, f"@{user_info} Entendido.")
                    else: send_chat_message(sock, f"@{user_info} Tive um problema para aprender isso.")
            else: send_chat_message(sock, f"Desculpe @{user_info}, apenas mestres podem me ensinar.")
            return

        activation_ask = "!ask "
        activation_mention = f"@{BOT_NICK} "
        question = ""
        is_activated = False
        if msg_lower.startswith(activation_ask):
            is_activated = True; question = message_content[len(activation_ask):].strip()
        elif msg_lower.startswith(activation_mention):
            is_activated = True; question = message_content[len(activation_mention):].strip()

        if is_activated and question:
            long_term_memories = database_handler.search_long_term_memory(user_info)
            user_memory = short_term_memory.get(user_info, {"history": []})
            
            # Chamada simplificada novamente. A complexidade está no gemini_handler.
            ai_response = gemini_handler.generate_response(
                question, 
                user_memory['history'], 
                BOT_SETTINGS, 
                LOREBOOK, 
                long_term_memories
            )
            
            send_chat_message(sock, f"@{user_info} {ai_response}")
            
            # ... (lógica de atualização de memória de curto prazo inalterada) ...
            user_memory['history'].append({'role': 'user', 'parts': [question]})
            user_memory['history'].append({'role': 'model', 'parts': [ai_response]})
            user_memory['last_interaction'] = datetime.now()
            if len(user_memory['history']) > MAX_HISTORY_LENGTH:
                user_memory['history'] = user_memory['history'][2:]
            short_term_memory[user_info] = user_memory
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def listen_for_messages(sock):
    # Inalterado
    buffer = ""; last_cleanup = time.time()
    while True:
        try:
            if time.time() - last_cleanup > 60:
                cleanup_inactive_memory(); last_cleanup = time.time()
            buffer += sock.recv(2048).decode('utf-8', errors='ignore')
            messages = buffer.split('\r\n'); buffer = messages.pop()
            for raw_message in messages:
                if not raw_message: continue
                if raw_message.startswith('PING'):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8')); continue
                process_message(sock, raw_message)
        except Exception as e:
            print(f"Erro no loop de escuta: {e}"); time.sleep(5)

def main():
    # ... (validação de .env inalterada) ...
    global BOT_SETTINGS, LOREBOOK
    BOT_SETTINGS, LOREBOOK = database_handler.load_initial_data()
    if not BOT_SETTINGS:
        print("ERRO CRÍTICO: Não foi possível carregar as configurações do bot."); return
    
    # MUDANÇA: Passa a configuração de busca para o loader do modelo
    use_native_search = BOT_SETTINGS.get('use_native_google_search', True)
    gemini_handler.load_interaction_model(
        BOT_SETTINGS.get('interaction_model', 'gemini-1.5-flash'),
        use_native_search
    )

    # ... (resto do código de conexão e loop principal inalterado) ...
    if not gemini_handler.GEMINI_ENABLED or not database_handler.DB_ENABLED:
        print("O bot não pode iniciar devido a um erro na inicialização de um módulo."); return
    sock = socket.socket()
    try:
        print("Conectando ao servidor IRC da Twitch...")
        sock.connect((HOST, PORT))
        print("Conectado. Autenticando...")
        sock.send(f"PASS {TTV_TOKEN}\n".encode('utf-8'))
        sock.send(f"NICK {BOT_NICK}\n".encode('utf-8'))
        sock.send(f"JOIN #{TTV_CHANNEL}\n".encode('utf-8'))
        
        search_mode = "Nativa (Google)" if use_native_search else "Fallback (DDGS)"
        send_chat_message(sock, f"AI_Yuh (v1.9.0) online. Modo de busca: {search_mode}.")
        
        listen_for_messages(sock)
    except Exception as e:
        print(f"Erro fatal na conexão: {e}")
    finally:
        print("Fechando a conexão.")
        sock.close()

if __name__ == "__main__":
    main()