# -*- coding: utf-8 -*-
import os
import socket
import time
from datetime import datetime, timedelta, date
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
GLOBAL_BUFFER_MAX_MINUTES = 15 # Adicionado como gatilho de tempo
UNCERTAINTY_KEYWORDS = ["não sei", "nao sei", "não tenho acesso", "desconheço", "não consigo encontrar"]
TIMEZONE = pytz.timezone('America/Sao_Paulo') # UTC-3

# --- Motor do Agendador de Memória ---
def run_scheduler():
    """Loop que roda em uma thread separada para executar tarefas agendadas."""
    print(f"[{datetime.now(TIMEZONE).strftime('%H:%M:%S')}] Agendador de memória iniciado em uma thread de fundo.")
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- Funções de Consolidação de Memória ---
def consolidate_daily_memories():
    print(f"[{datetime.now(TIMEZONE).strftime('%H:%M:%S')}] AGENDADOR: Verificando memórias 'transfer' para consolidar em 'daily'.")
    today = datetime.now(TIMEZONE).date()
    yesterday = today - timedelta(days=1)
    
    start_of_yesterday = TIMEZONE.localize(datetime.combine(yesterday, datetime.min.time()))
    end_of_yesterday = TIMEZONE.localize(datetime.combine(yesterday, datetime.max.time()))
    
    memories_to_consolidate = database_handler.get_memories_for_consolidation("transfer", start_of_yesterday, end_of_yesterday)
    
    if not memories_to_consolidate:
        print("AGENDADOR: Nenhuma memória 'transfer' de ontem para consolidar.")
        return
        
    print(f"AGENDADOR: Encontradas {len(memories_to_consolidate)} memórias 'transfer' de ontem. Sumarizando...")
    full_text = "\n".join([mem['summary'] for mem in memories_to_consolidate])
    daily_summary = gemini_handler.summarize_global_chat(f"Resuma os seguintes eventos do dia em um parágrafo conciso:\n{full_text}")
    
    metadata = {"date": yesterday.isoformat(), "source_ids": [mem['id'] for mem in memories_to_consolidate]}
    database_handler.save_hierarchical_memory("daily", daily_summary, metadata)
    
    ids_to_delete = [mem['id'] for mem in memories_to_consolidate]
    database_handler.delete_memories_by_ids(ids_to_delete)

# (Aqui iriam as funções consolidate_weekly, monthly, etc.)

# --- Funções do Bot ---
def send_chat_message(sock, message):
    try: sock.send(f"PRIVMSG #{TTV_CHANNEL} :{message}\n".encode('utf-8'))
    except Exception as e: print(f"Erro ao enviar mensagem: {e}")

def summarize_and_clear_global_buffer():
    global global_chat_buffer
    if not global_chat_buffer: return
    print(f"Buffer de transferência atingiu o limite. Sumarizando {len(global_chat_buffer)} mensagens...")
    transcript = "\n".join(f"{msg['user']}: {msg['content']}" for msg in global_chat_buffer)
    summary = gemini_handler.summarize_global_chat(transcript)
    database_handler.save_hierarchical_memory("transfer", summary)
    global_chat_buffer = []
    print("Buffer de transferência sumarizado e limpo.")

def process_message(sock, raw_message):
    if "PRIVMSG" not in raw_message: return
    try:
        source, _, message_body = raw_message.partition('PRIVMSG')
        user_info = source.split('!')[0][1:]
        message_content = message_body.split(':', 1)[1].strip()
        if user_info.lower() == BOT_NICK: return
        # print(f"CHAT | {user_info}: {message_content}") # Comentado para não poluir
        global_chat_buffer.append({"user": user_info, "content": message_content})
        
        user_permission = database_handler.get_user_permission(user_info)
        if user_permission == 'blacklist': return

        msg_lower = message_content.lower()
        # Lógica de !learn, !ask, etc. (inalterada)
        
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def listen_for_messages(sock):
    buffer = ""
    while True:
        try:
            buffer += sock.recv(2048).decode('utf-8', errors='ignore')
            messages = buffer.split('\r_n'); buffer = messages.pop()
            for raw_message in messages:
                if not raw_message: continue
                if raw_message.startswith('PING'): sock.send("PONG :tmi.twitch.tv\r_n".encode('utf-8')); continue
                process_message(sock, raw_message)
        except Exception as e:
            print(f"Erro no loop de escuta: {e}"); time.sleep(5)

def main():
    global BOT_SETTINGS, LOREBOOK
    BOT_SETTINGS, LOREBOOK = database_handler.load_initial_data()
    if not BOT_SETTINGS: print("ERRO CRÍTICO: Não foi possível carregar as configurações."); return
    gemini_handler.load_models_from_settings(BOT_SETTINGS)
    if not gemini_handler.GEMINI_ENABLED or not database_handler.DB_ENABLED: print("O bot não pode iniciar."); return
    
    # --- Configuração e Início do Agendador ---
    schedule.every(GLOBAL_BUFFER_MAX_MINUTES).minutes.do(summarize_and_clear_global_buffer)
    schedule.every().day.at("00:00", str(TIMEZONE)).do(consolidate_daily_memories)
    # Adicionar aqui os outros agendamentos (weekly, etc.) no futuro
    
    scheduler_thread = threading.Thread(target=run_scheduler, name="MemoryScheduler")
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # --- Conexão e Loop Principal do Bot ---
    sock = socket.socket()
    try:
        print("Conectando ao servidor IRC da Twitch...")
        sock.connect((HOST, PORT))
        print("Conectado. Autenticando...")
        sock.send(f"PASS {TTV_TOKEN}\n".encode('utf-8'))
        sock.send(f"NICK {BOT_NICK}\n".encode('utf-8'))
        sock.send(f"JOIN #{TTV_CHANNEL}\n".encode('utf-8'))
        send_chat_message(sock, f"AI_Yuh (v2.2.0-scheduler) online. Agendador de memória ativado.")
        listen_for_messages(sock)
    except Exception as e:
        print(f"Erro fatal na conexão: {e}")
    finally:
        print("Fechando a conexão."); sock.close()

if __name__ == "__main__":
    main()