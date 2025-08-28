# -*- coding: utf-8 -*-
import os
import socket
import time
from datetime import datetime, timedelta
import threading
import schedule
import pytz
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(threadName)s] - %(levelname)s - %(message)s')
load_dotenv()
import gemini_handler
import database_handler

# --- Configurações & Variáveis Globais ---
TTV_TOKEN = os.getenv('TTV_TOKEN')
BOT_NICK = os.getenv('BOT_NICK', 'ai_yuh').lower()
TTV_CHANNEL = os.getenv('TTV_CHANNEL').lower()
HOST = "irc.chat.twitch.tv"
PORT = 6667
BOT_SETTINGS = {}
LOREBOOK = []
short_term_memory = {}
global_chat_buffer = []
GLOBAL_BUFFER_MAX_MESSAGES = 40
GLOBAL_BUFFER_MAX_MINUTES = 15
MEMORY_EXPIRATION_MINUTES = 5
MAX_HISTORY_LENGTH = 10
TIMEZONE = pytz.timezone('America/Sao_Paulo')

# =========================================================================================
#                 NOVAS FUNÇÕES PARA MEMÓRIA HIERÁRQUICA
# =========================================================================================
def consolidate_weekly_memories():
    database_handler.add_log("INFO", "AGENDADOR: Verificando memórias 'daily' para consolidação semanal.", "SchedulerThread")
    daily_memories = database_handler.get_memories_for_consolidation("daily", None, None) # Pega todas as memórias diárias
    
    if len(daily_memories) < 7:
        database_handler.add_log("INFO", f"AGENDADOR: Apenas {len(daily_memories)}/7 memórias diárias. Aguardando para sumarização semanal.", "SchedulerThread")
        return

    memories_to_summarize = daily_memories[:7]
    database_handler.add_log("INFO", "AGENDADOR: 7 memórias diárias encontradas. Sumarizando para memória semanal...", "SchedulerThread")
    
    full_text = "\n\n".join([f"Eventos de {datetime.fromisoformat(mem['metadata']['date']).strftime('%A, %d/%m/%Y')}:\n{mem['summary']}" for mem in memories_to_summarize])
    weekly_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos mais importantes da semana a seguir:\n{full_text}")
    
    start_date = memories_to_summarize[0]['metadata']['date']
    end_date = memories_to_summarize[-1]['metadata']['date']
    metadata = {"start_date": start_date, "end_date": end_date}
    
    database_handler.save_hierarchical_memory("weekly", weekly_summary, metadata)
    
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_log("INFO", "AGENDADOR: Memória semanal consolidada e memórias diárias limpas.", "SchedulerThread")

def consolidate_monthly_memories():
    database_handler.add_log("INFO", "AGENDADOR: Verificando memórias 'weekly' para consolidação mensal.", "SchedulerThread")
    weekly_memories = database_handler.get_memories_for_consolidation("weekly", None, None)
    
    # Usamos 4 semanas para formar um mês
    if len(weekly_memories) < 4:
        database_handler.add_log("INFO", f"AGENDADOR: Apenas {len(weekly_memories)}/4 memórias semanais. Aguardando.", "SchedulerThread")
        return

    memories_to_summarize = weekly_memories[:4]
    database_handler.add_log("INFO", "AGENDADOR: 4 memórias semanais encontradas. Sumarizando para memória mensal...", "SchedulerThread")
    
    full_text = "\n\n".join([f"Resumo da semana de {mem['metadata']['start_date']} a {mem['metadata']['end_date']}:\n{mem['summary']}" for mem in memories_to_summarize])
    monthly_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos mais importantes do mês a seguir:\n{full_text}")
    
    month_name = datetime.fromisoformat(memories_to_summarize[0]['metadata']['start_date']).strftime('%B de %Y')
    metadata = {"month": month_name}
    
    database_handler.save_hierarchical_memory("monthly", monthly_summary, metadata)
    
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_log("INFO", "AGENDADOR: Memória mensal consolidada e memórias semanais limpas.", "SchedulerThread")

def consolidate_yearly_memories():
    database_handler.add_log("INFO", "AGENDADOR: Verificando memórias 'monthly' para consolidação anual.", "SchedulerThread")
    monthly_memories = database_handler.get_memories_for_consolidation("monthly", None, None)
    
    if len(monthly_memories) < 12:
        database_handler.add_log("INFO", f"AGENDADOR: Apenas {len(monthly_memories)}/12 memórias mensais. Aguardando.", "SchedulerThread")
        return

    memories_to_summarize = monthly_memories[:12]
    database_handler.add_log("INFO", "AGENDADOR: 12 memórias mensais encontradas. Sumarizando para memória anual...", "SchedulerThread")
    
    full_text = "\n\n".join([f"Resumo de {mem['metadata']['month']}:\n{mem['summary']}" for mem in memories_to_summarize])
    year_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos mais importantes do ano a seguir:\n{full_text}")
    
    year_number = datetime.now(TIMEZONE).year - 1 # Assumindo que roda no início do ano seguinte
    metadata = {"year": year_number}
    
    database_handler.save_hierarchical_memory("yearly", year_summary, metadata)
    
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_log("INFO", "AGENDADOR: Memória anual consolidada e memórias mensais limpas.", "SchedulerThread")

def run_scheduler():
    logging.info("Agendador de memória e tarefas iniciado.")
    database_handler.add_log("INFO", "Agendador iniciado.", "SchedulerThread")
    
    # Tarefas de alta frequência
    schedule.every(2).minutes.do(send_heartbeat)
    
    # Tarefas de baixa frequência (madrugada)
    schedule.every().day.at("00:15", str(TIMEZONE)).do(consolidate_daily_memories)
    schedule.every().monday.at("01:00", str(TIMEZONE)).do(consolidate_weekly_memories)
    schedule.every().day.at("01:30", str(TIMEZONE)).do(consolidate_monthly_memories) # Roda todo dia para checar se já tem 4 semanas
    schedule.every().day.at("02:00", str(TIMEZONE)).do(consolidate_yearly_memories) # Roda todo dia para checar se já tem 12 meses
    schedule.every().day.at("03:00", str(TIMEZONE)).do(database_handler.delete_old_logs)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def consolidate_daily_memories():
    # ... (código existente da função)
    database_handler.add_log("INFO", "AGENDADOR: Verificando memórias 'transfer'...", "SchedulerThread")
    today = datetime.now(TIMEZONE).date()
    yesterday = today - timedelta(days=1)
    start_of_yesterday = TIMEZONE.localize(datetime.combine(yesterday, datetime.min.time()))
    end_of_yesterday = TIMEZONE.localize(datetime.combine(yesterday, datetime.max.time()))
    memories_to_consolidate = database_handler.get_memories_for_consolidation("transfer", start_of_yesterday, end_of_yesterday)
    if not memories_to_consolidate:
        database_handler.add_log("INFO", "AGENDADOR: Nenhuma memória para consolidar.", "SchedulerThread")
        return
    database_handler.add_log("INFO", f"AGENDADOR: {len(memories_to_consolidate)} memórias encontradas. Sumarizando...", "SchedulerThread")
    full_text = "\n\n".join([mem['summary'] for mem in memories_to_consolidate])
    daily_summary = gemini_handler.summarize_global_chat(f"Resuma os seguintes eventos do dia {yesterday.strftime('%d/%m/%Y')}:\n{full_text}")
    metadata = {"date": yesterday.isoformat()}
    database_handler.save_hierarchical_memory("daily", daily_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_consolidate]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_log("INFO", "AGENDADOR: Memória diária consolidada.", "SchedulerThread")

# ... (o resto de main_bot.py, como send_heartbeat, send_chat_message, process_message, etc., continua igual)
def send_heartbeat():
    database_handler.update_bot_status("Online")

def send_chat_message(sock, message):
    try:
        if '\n' in message: messages_to_send = message.split('\n')
        else: messages_to_send = [message]
        for line in messages_to_send:
            clean_line = line.strip()
            if not clean_line: continue
            sock.send(f"PRIVMSG #{TTV_CHANNEL} :{clean_line}\n".encode('utf-8'))
            database_handler.add_log("INFO", f"BOT > {clean_line}", "BotThread")
            time.sleep(0.8)
    except Exception as e:
        database_handler.add_log("ERROR", f"Erro ao enviar msg: {e}", "BotThread")

def summarize_and_clear_global_buffer():
    global global_chat_buffer
    if not global_chat_buffer: return
    database_handler.add_log("INFO", f"Sumarizando buffer global com {len(global_chat_buffer)} mensagens.", "BotThread")
    transcript = "\n".join(f"[{msg['timestamp'].strftime('%H:%M')}] {msg['user']}: {msg['content']}" for msg in global_chat_buffer)
    summary = gemini_handler.summarize_global_chat(transcript)
    database_handler.save_hierarchical_memory("transfer", summary)
    global_chat_buffer = []
    database_handler.add_log("INFO", "Buffer global sumarizado e limpo.", "BotThread")

def cleanup_inactive_memory():
    now = datetime.now()
    inactive_users = [user for user, data in list(short_term_memory.items()) if now - data['last_interaction'] > timedelta(minutes=MEMORY_EXPIRATION_MINUTES)]
    for user in inactive_users:
        database_handler.add_log("INFO", f"Usuário {user} inativo. Sumarizando e limpando memória.", "BotThread")
        user_memory = short_term_memory.pop(user)
        summary = gemini_handler.summarize_conversation(user_memory['history'])
        database_handler.save_long_term_memory(user, summary)

def process_message(sock, raw_message):
    try:
        if "PRIVMSG" not in raw_message: return
        source, _, message_body = raw_message.partition('PRIVMSG')
        user_info = source.split('!')[0][1:]
        message_content = message_body.split(':', 1)[1].strip()
        if user_info.lower() == BOT_NICK: return
        
        database_handler.add_log("INFO", f"{user_info}: {message_content}", "BotThread")
        
        global_chat_buffer.append({"user": user_info, "content": message_content, "timestamp": datetime.now(TIMEZONE)})
        user_permission = database_handler.get_user_permission(user_info)
        if user_permission == 'blacklist': return
        msg_lower = message_content.lower()
        
        learn_command = "!learn "
        if msg_lower.startswith(learn_command):
            if user_permission == 'master':
                fact = message_content[len(learn_command):].strip()
                if fact and database_handler.add_lorebook_entry(fact, user_info):
                    global LOREBOOK
                    LOREBOOK = database_handler.get_current_lorebook()
                    send_chat_message(sock, f"@{user_info} Entendido. Adicionei o fato à minha base de conhecimento.")
                else: send_chat_message(sock, f"@{user_info} Tive um problema para aprender isso.")
            else: send_chat_message(sock, f"Desculpe @{user_info}, apenas mestres podem me ensinar.")
            return

        activation_ask = "!ask "; activation_mention = f"@{BOT_NICK} "
        question = ""; is_activated = False
        if msg_lower.startswith(activation_ask): is_activated=True; question=message_content[len(activation_ask):].strip()
        elif msg_lower.startswith(activation_mention): is_activated=True; question=message_content[len(activation_mention):].strip()

        if is_activated and question:
            current_lorebook = database_handler.get_current_lorebook()
            long_term_memories = database_handler.search_long_term_memory(user_info)
            hierarchical_memories = database_handler.search_hierarchical_memory()
            user_memory = short_term_memory.get(user_info, {"history": []})
            
            database_handler.add_log("INFO", f"Gerando resposta para {user_info}...", "BotThread")
            
            final_response = gemini_handler.generate_interactive_response(
                question, user_memory['history'], BOT_SETTINGS, current_lorebook, long_term_memories, hierarchical_memories
            )
            
            send_chat_message(sock, f"@{user_info} {final_response}")
            
            user_memory['history'].append({'role': 'user', 'parts': [question]})
            user_memory['history'].append({'role': 'model', 'parts': [final_response]})
            user_memory['last_interaction'] = datetime.now()
            if len(user_memory['history']) > MAX_HISTORY_LENGTH * 2:
                user_memory['history'] = user_memory['history'][-MAX_HISTORY_LENGTH*2:]
            short_term_memory[user_info] = user_memory
            
    except Exception as e:
        database_handler.add_log("ERROR", f"Erro em process_message: {e}", "BotThread")
        logging.error(f"Erro em process_message: {e}", exc_info=True)

def listen_for_messages(sock):
    buffer = ""; last_cleanup = time.time(); last_global_summary = time.time()
    while True:
        try:
            now = time.time()
            if now - last_cleanup > 60:
                cleanup_inactive_memory(); last_cleanup = now
            if len(global_chat_buffer) >= GLOBAL_BUFFER_MAX_MESSAGES or now - last_global_summary > (GLOBAL_BUFFER_MAX_MINUTES * 60):
                summarize_and_clear_global_buffer(); last_global_summary = now
            buffer += sock.recv(2048).decode('utf-8', errors='ignore')
            messages = buffer.split('\r\n'); buffer = messages.pop()
            for raw_message in messages:
                if not raw_message: continue
                if raw_message.startswith('PING'):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
                    continue
                process_message(sock, raw_message)
        except socket.timeout: continue
        except Exception as e:
            database_handler.add_log("ERROR", f"Erro no loop de escuta: {e}", "BotThread")
            logging.error(f"Erro no loop de escuta: {e}")
            time.sleep(15)

def main():
    global BOT_SETTINGS, LOREBOOK
    BOT_SETTINGS, LOREBOOK = database_handler.load_initial_data()
    if not BOT_SETTINGS:
        logging.critical("Não foi possível carregar as configs do bot."); return
    gemini_handler.load_models_from_settings(BOT_SETTINGS)
    if not gemini_handler.GEMINI_ENABLED or not database_handler.DB_ENABLED:
        logging.critical("Módulos essenciais falharam."); return
    
    scheduler_thread = threading.Thread(target=run_scheduler, name="SchedulerThread", daemon=True)
    scheduler_thread.start()
    
    sock = socket.socket()
    sock.settimeout(60.0)
    try:
        database_handler.add_log("INFO", "Conectando ao IRC da Twitch...", "BotThread")
        sock.connect((HOST, PORT))
        sock.send(f"PASS {TTV_TOKEN}\n".encode('utf-8'))
        sock.send(f"NICK {BOT_NICK}\n".encode('utf-8'))
        sock.send(f"JOIN #{TTV_CHANNEL}\n".encode('utf-8'))
        database_handler.add_log("INFO", "Conectado e autenticado.", "BotThread")
        time.sleep(2)
        database_handler.update_bot_status("Online")
        send_chat_message(sock, f"AI_Yuh (v2.9.0-full-memory) online.")
        listen_for_messages(sock)
    except Exception as e:
        database_handler.add_log("CRITICAL", f"Erro fatal na conexão: {e}", "BotThread")
        logging.critical(f"Erro fatal na conexão: {e}", exc_info=True)
    finally:
        database_handler.add_log("INFO", "Desligando...", "BotThread")
        database_handler.update_bot_status("Offline")
        sock.close()

if __name__ == "__main__":
    main()