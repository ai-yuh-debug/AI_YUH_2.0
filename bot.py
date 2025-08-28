# -*- coding: utf-8 -*-
import os
import socket
import time
import re
from datetime import datetime, timedelta
import threading
import schedule
import pytz
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
GLOBAL_BUFFER_MAX_MESSAGES = 40
GLOBAL_BUFFER_MAX_MINUTES = 15
MEMORY_EXPIRATION_MINUTES = 1
MAX_HISTORY_LENGTH = 10
UNCERTAINTY_KEYWORDS = ["não sei", "nao sei", "não tenho acesso", "desconheço", "não consigo encontrar"]
TIMEZONE = pytz.timezone('America/Sao_Paulo')

def run_scheduler():
    print(f"[{datetime.now(TIMEZONE).strftime('%H:%M:%S')}] Agendador iniciado.")
    while True:
        schedule.run_pending()
        time.sleep(1)

def consolidate_daily_memories():
    # ... (código inalterado)

def send_heartbeat():
    database_handler.update_bot_status("Online")

def send_chat_message(sock, message):
    try:
        sock.send(f"PRIVMSG #{TTV_CHANNEL} :{message}\n".encode('utf-8'))
        database_handler.add_live_chat_message(BOT_NICK, message)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def summarize_and_clear_global_buffer():
    # ... (código inalterado)
    
def cleanup_inactive_memory():
    # ... (código inalterado)

def find_relevant_lore(question: str, full_lorebook: list) -> list[str]:
    # ... (código inalterado)

def process_message(sock, raw_message):
    if "PRIVMSG" not in raw_message: return
    try:
        source, _, message_body = raw_message.partition('PRIVMSG')
        user_info = source.split('!')[0][1:]
        message_content = message_body.split(':', 1)[1].strip()
        
        database_handler.add_live_chat_message(user_info, message_content)
        if user_info.lower() == BOT_NICK: return
        
        global_chat_buffer.append({"user": user_info, "content": message_content})
        user_permission = database_handler.get_user_permission(user_info)
        if user_permission == 'blacklist': return

        msg_lower = message_content.lower()
        
        learn_command = "!learn "
        if msg_lower.startswith(learn_command):
            # ... (lógica !learn inalterada)
            return

        activation_ask = "!ask "; activation_mention = f"@{BOT_NICK} "
        question = ""; is_activated = False
        if msg_lower.startswith(activation_ask): is_activated=True; question=message_content[len(activation_ask):].strip()
        elif msg_lower.startswith(activation_mention): is_activated=True; question=message_content[len(activation_mention):].strip()

        if is_activated and question:
            database_handler.add_live_log("IA PENSANDO", f"'{user_info}' perguntou: '{question}'")
            current_lorebook = database_handler.get_current_lorebook()
            relevant_lore = find_relevant_lore(question, current_lorebook)
            long_term_memories = database_handler.search_long_term_memory(user_info)
            hierarchical_memories = database_handler.search_hierarchical_memory()
            user_memory = short_term_memory.get(user_info, {"history": []})
            
            thought = f"Usuário: '{user_info}' | Pergunta: '{question}' | Contextos: Lorebook ({len(relevant_lore)}), Mem. Pessoal ({len(long_term_memories)}), Mem. Global ({len(hierarchical_memories)})"
            database_handler.update_bot_thought(thought)
            
            print("Tentando responder sem busca na web...") # LOG RESTAURADO
            initial_response = gemini_handler.generate_response_without_search(question, user_memory['history'], BOT_SETTINGS, relevant_lore, long_term_memories, hierarchical_memories)
            
            final_response = initial_response
            if any(keyword in initial_response.lower() for keyword in UNCERTAINTY_KEYWORDS):
                print("Resposta inicial indica incerteza. Realizando busca na web.") # LOG RESTAURADO
                database_handler.add_live_log("IA BUSCANDO", "Incerteza detectada. Buscando no DDGS.")
                web_context = gemini_handler.web_search(question)
                if web_context:
                    final_response = gemini_handler.generate_response_with_search(question, user_memory['history'], BOT_SETTINGS, relevant_lore, long_term_memories, hierarchical_memories, web_context)
            else:
                print("Resposta inicial foi confiante. Não é necessário buscar na web.") # LOG RESTAURADO

            send_chat_message(sock, f"@{user_info} {final_response}")
            
            user_memory['history'].append({'role': 'user', 'parts': [question]})
            user_memory['history'].append({'role': 'model', 'parts': [final_response]})
            user_memory['last_interaction'] = datetime.now()
            short_term_memory[user_info] = user_memory
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def listen_for_messages(sock):
    # ... (código inalterado)

def main():
    # ... (código inalterado)

if __name__ == "__main__":
    main()