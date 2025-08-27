# -*- coding: utf-8 -*-
import os
import socket
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
import gemini_handler
import database_handler

# --- Configurações & Variáveis Globais ---
TTV_TOKEN = os.getenv('TTV_TOKEN')
BOT_NICK = os.getenv('BOT_NICK').lower()
TTV_CHANNEL = os.getenv('TTV_CHANNEL').lower()
HOST = "irc.chat.twitch.tv"
PORT = 6667
BOT_SETTINGS = {}
LOREBOOK = []
short_term_memory = {}
global_chat_buffer = []
GLOBAL_BUFFER_MAX_MESSAGES = 30
GLOBAL_BUFFER_MAX_MINUTES = 15
MEMORY_EXPIRATION_MINUTES = 5
MAX_HISTORY_LENGTH = 10
UNCERTAINTY_KEYWORDS = ["não sei", "nao sei", "não tenho acesso", "desconheço", "não consigo encontrar", "minha base de conhecimento", "não tenho informações em tempo real", "dados de treinamento", "não tenho certeza", "não posso afirmar"]

def send_chat_message(sock, message):
    try: sock.send(f"PRIVMSG #{TTV_CHANNEL} :{message}\n".encode('utf-8'))
    except Exception as e: print(f"Erro ao enviar mensagem: {e}")

def cleanup_inactive_memory():
    now = datetime.now()
    inactive_users = [user for user, data in short_term_memory.items() if now - data['last_interaction'] > timedelta(minutes=MEMORY_EXPIRATION_MINUTES)]
    for user in inactive_users:
        print(f"Usuário {user} inativo. Sumarizando memória pessoal...")
        user_memory = short_term_memory.pop(user)
        summary = gemini_handler.summarize_conversation(user_memory['history'])
        database_handler.save_long_term_memory(user, summary)

def summarize_and_clear_global_buffer():
    global global_chat_buffer
    if not global_chat_buffer: return
    print(f"Buffer global atingiu o limite. Sumarizando {len(global_chat_buffer)} mensagens...")
    transcript = "\n".join(f"{msg['user']}: {msg['content']}" for msg in global_chat_buffer)
    summary = gemini_handler.summarize_global_chat(transcript)
    database_handler.save_hierarchical_memory("transfer", summary)
    global_chat_buffer = []
    print("Buffer global sumarizado e limpo.")

def process_message(sock, raw_message):
    if "PRIVMSG" not in raw_message: return
    try:
        source, _, message_body = raw_message.partition('PRIVMSG')
        user_info = source.split('!')[0][1:]
        message_content = message_body.split(':', 1)[1].strip()
        if user_info.lower() == BOT_NICK: return
        print(f"CHAT | {user_info}: {message_content}")
        global_chat_buffer.append({"user": user_info, "content": message_content})
        
        user_permission = database_handler.get_user_permission(user_info)
        if user_permission == 'blacklist': return

        msg_lower = message_content.lower()
        learn_command = "!learn "
        if msg_lower.startswith(learn_command):
            if user_permission == 'master':
                fact = message_content[len(learn_command):].strip()
                if fact and database_handler.add_lorebook_entry(fact, user_info):
                    LOREBOOK.append(fact); send_chat_message(sock, f"@{user_info} Entendido.")
                else: send_chat_message(sock, f"@{user_info} Tive um problema para aprender.")
            else: send_chat_message(sock, f"Desculpe @{user_info}, apenas mestres podem me ensinar.")
            return

        activation_ask = "!ask "; activation_mention = f"@{BOT_NICK} "
        question = ""; is_activated = False
        if msg_lower.startswith(activation_ask): is_activated=True; question=message_content[len(activation_ask):].strip()
        elif msg_lower.startswith(activation_mention): is_activated=True; question=message_content[len(activation_mention):].strip()

        if is_activated and question:
            long_term_memories = database_handler.search_long_term_memory(user_info)
            hierarchical_memories = database_handler.search_hierarchical_memory()
            user_memory = short_term_memory.get(user_info, {"history": []})
            
            print("Tentando responder sem busca na web...")
            initial_response = gemini_handler.generate_response_without_search(question, user_memory['history'], BOT_SETTINGS, LOREBOOK, long_term_memories, hierarchical_memories)
            
            final_response = initial_response
            if any(keyword in initial_response.lower() for keyword in UNCERTAINTY_KEYWORDS):
                print(f"Resposta inicial indica incerteza. Realizando busca na web.")
                web_context = gemini_handler.web_search(question)
                if web_context:
                    final_response = gemini_handler.generate_response_with_search(question, user_memory['history'], BOT_SETTINGS, LOREBOOK, long_term_memories, hierarchical_memories, web_context)
            else:
                print("Resposta inicial foi confiante. Não é necessário buscar na web.")

            send_chat_message(sock, f"@{user_info} {final_response}")
            
            user_memory['history'].append({'role': 'user', 'parts': [question]})
            user_memory['history'].append({'role': 'model', 'parts': [final_response]})
            user_memory['last_interaction'] = datetime.now()
            if len(user_memory['history']) > MAX_HISTORY_LENGTH: user_memory['history'] = user_memory['history'][2:]
            short_term_memory[user_info] = user_memory
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def listen_for_messages(sock):
    buffer = ""; last_cleanup = time.time(); last_global_summary = time.time()
    while True:
        try:
            now = time.time()
            if now - last_cleanup > 60: cleanup_inactive_memory(); last_cleanup = now
            if len(global_chat_buffer) >= GLOBAL_BUFFER_MAX_MESSAGES or now - last_global_summary > (GLOBAL_BUFFER_MAX_MINUTES * 60):
                summarize_and_clear_global_buffer(); last_global_summary = now
            
            buffer += sock.recv(2048).decode('utf-8', errors='ignore')
            messages = buffer.split('\r\n'); buffer = messages.pop()
            for raw_message in messages:
                if not raw_message: continue
                if raw_message.startswith('PING'): sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8')); continue
                process_message(sock, raw_message)
        except Exception as e:
            print(f"Erro no loop de escuta: {e}"); time.sleep(5)

def main():
    global BOT_SETTINGS, LOREBOOK
    BOT_SETTINGS, LOREBOOK = database_handler.load_initial_data()
    if not BOT_SETTINGS: print("ERRO CRÍTICO: Não foi possível carregar as configurações do bot."); return
    gemini_handler.load_models_from_settings(BOT_SETTINGS)
    if not gemini_handler.GEMINI_ENABLED or not database_handler.DB_ENABLED: print("O bot não pode iniciar devido a um erro na inicialização de um módulo."); return
    
    sock = socket.socket()
    try:
        print("Conectando ao servidor IRC da Twitch...")
        sock.connect((HOST, PORT))
        print("Conectado. Autenticando...")
        sock.send(f"PASS {TTV_TOKEN}\n".encode('utf-8'))
        sock.send(f"NICK {BOT_NICK}\n".encode('utf-8'))
        sock.send(f"JOIN #{TTV_CHANNEL}\n".encode('utf-8'))
        send_chat_message(sock, f"AI_Yuh (v2.1.1-hier-ctx) online. Contexto hierárquico ativado.")
        listen_for_messages(sock)
    except Exception as e:
        print(f"Erro fatal na conexão: {e}")
    finally:
        print("Fechando a conexão.")
        sock.close()

if __name__ == "__main__":
    main()