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

def consolidate_weekly_memories():
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", "Verificando memórias 'daily' para consolidação semanal.")
    daily_memories = database_handler.get_memories_for_consolidation("daily")
    if len(daily_memories) < 7:
        database_handler.add_live_log("STATUS", f"Apenas {len(daily_memories)}/7 memórias diárias. Aguardando.")
        return
    memories_to_summarize = daily_memories[:7]
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", "7 memórias diárias encontradas. Sumarizando para memória semanal...")
    full_text = "\n\n".join([f"Eventos de {datetime.fromisoformat(mem['metadata']['date']).strftime('%A, %d/%m/%Y')}:\n{mem['summary']}" for mem in memories_to_summarize if mem.get('metadata') and mem['metadata'].get('date')])
    weekly_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos mais importantes da semana a seguir:\n{full_text}")
    start_date = memories_to_summarize[0]['metadata']['date']
    end_date = memories_to_summarize[-1]['metadata']['date']
    metadata = {"start_date": start_date, "end_date": end_date}
    database_handler.save_hierarchical_memory("weekly", weekly_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_live_log("MEMÓRIA GLOBAL", "Memória semanal consolidada e memórias diárias limpas.")

def consolidate_monthly_memories():
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", "Verificando memórias 'weekly' para consolidação mensal.")
    weekly_memories = database_handler.get_memories_for_consolidation("weekly")
    if len(weekly_memories) < 4:
        database_handler.add_live_log("STATUS", f"Apenas {len(weekly_memories)}/4 memórias semanais. Aguardando.")
        return
    memories_to_summarize = weekly_memories[:4]
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", "4 memórias semanais encontradas. Sumarizando...")
    full_text = "\n\n".join([f"Resumo da semana de {mem['metadata']['start_date']} a {mem['metadata']['end_date']}:\n{mem['summary']}" for mem in memories_to_summarize if mem.get('metadata') and mem['metadata'].get('start_date')])
    monthly_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos mais importantes do mês a seguir:\n{full_text}")
    month_name = datetime.fromisoformat(memories_to_summarize[0]['metadata']['start_date']).strftime('%B de %Y')
    metadata = {"month": month_name}
    database_handler.save_hierarchical_memory("monthly", monthly_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_live_log("MEMÓRIA GLOBAL", "Memória mensal consolidada e memórias semanais limpas.")

def consolidate_yearly_memories():
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", "Verificando memórias 'monthly' para consolidação anual.")
    monthly_memories = database_handler.get_memories_for_consolidation("monthly")
    if len(monthly_memories) < 12:
        database_handler.add_live_log("STATUS", f"Apenas {len(monthly_memories)}/12 memórias mensais. Aguardando.")
        return
    memories_to_summarize = monthly_memories[:12]
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", "12 memórias mensais encontradas. Sumarizando...")
    full_text = "\n\n".join([f"Resumo de {mem['metadata']['month']}:\n{mem['summary']}" for mem in memories_to_summarize if mem.get('metadata') and mem['metadata'].get('month')])
    year_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos mais importantes do ano a seguir:\n{full_text}")
    year_number = datetime.now(TIMEZONE).year - 1
    metadata = {"year": year_number}
    database_handler.save_hierarchical_memory("yearly", year_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_live_log("MEMÓRIA GLOBAL", "Memória anual consolidada e memórias mensais limpas.")

def consolidate_secular_memories():
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", "Verificando memórias 'yearly' para consolidação secular.")
    yearly_memories = database_handler.get_memories_for_consolidation("yearly")
    if len(yearly_memories) < 100:
        database_handler.add_live_log("STATUS", f"Apenas {len(yearly_memories)}/100 memórias anuais. Aguardando.")
        return
    memories_to_summarize = yearly_memories[:100]
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", "100 memórias anuais encontradas. Sumarizando para memória secular...")
    full_text = "\n\n".join([f"Resumo do ano {mem['metadata']['year']}:\n{mem['summary']}" for mem in memories_to_summarize if mem.get('metadata') and mem['metadata'].get('year')])
    century_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos mais importantes do século a seguir:\n{full_text}")
    start_year = memories_to_summarize[0]['metadata']['year']
    end_year = memories_to_summarize[-1]['metadata']['year']
    metadata = {"start_year": start_year, "end_year": end_year}
    database_handler.save_hierarchical_memory("century", century_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_live_log("MEMÓRIA GLOBAL", "Memória secular consolidada e memórias anuais limpas.")

def run_scheduler():
    logging.info("Agendador de memória e tarefas iniciado.")
    database_handler.add_live_log("STATUS", "Agendador iniciado.")
    schedule.every(2).minutes.do(send_heartbeat)
    schedule.every().day.at("00:15", str(TIMEZONE)).do(consolidate_daily_memories)
    schedule.every().monday.at("01:00", str(TIMEZONE)).do(consolidate_weekly_memories)
    schedule.every().day.at("01:30", str(TIMEZONE)).do(consolidate_monthly_memories)
    schedule.every().day.at("02:00", str(TIMEZONE)).do(consolidate_yearly_memories)
    schedule.every().day.at("02:30", str(TIMEZONE)).do(consolidate_secular_memories)
    schedule.every().day.at("03:00", str(TIMEZONE)).do(database_handler.delete_old_logs)
    while True:
        schedule.run_pending()
        time.sleep(1)

def consolidate_daily_memories():
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", "Verificando memórias 'transfer' para consolidação diária.")
    today = datetime.now(TIMEZONE).date()
    yesterday = today - timedelta(days=1)
    start_of_yesterday = TIMEZONE.localize(datetime.combine(yesterday, datetime.min.time()))
    end_of_yesterday = TIMEZONE.localize(datetime.combine(yesterday, datetime.max.time()))
    memories_to_consolidate = database_handler.get_memories_for_consolidation("transfer", start_of_yesterday, end_of_yesterday)
    if not memories_to_consolidate:
        database_handler.add_live_log("STATUS", "Nenhuma memória 'transfer' para consolidar hoje.")
        return
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", f"{len(memories_to_consolidate)} memórias 'transfer' encontradas. Sumarizando...")
    full_text = "\n\n".join([mem['summary'] for mem in memories_to_consolidate])
    daily_summary = gemini_handler.summarize_global_chat(f"Resuma os seguintes eventos do dia {yesterday.strftime('%d/%m/%Y')}:\n{full_text}")
    metadata = {"date": yesterday.isoformat()}
    database_handler.save_hierarchical_memory("daily", daily_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_consolidate]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_live_log("MEMÓRIA GLOBAL", "Memória diária consolidada.")

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
            database_handler.add_live_log("CHAT", f"BOT > {clean_line}")
            time.sleep(0.8)
    except Exception as e:
        database_handler.add_live_log("ERRO", f"Erro ao enviar msg: {e}")

def summarize_and_clear_global_buffer():
    global global_chat_buffer
    if not global_chat_buffer: return
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", f"Sumarizando buffer global com {len(global_chat_buffer)} mensagens.")
    transcript = "\n".join(f"[{msg['timestamp'].strftime('%H:%M')}] {msg['user']}: {msg['content']}" for msg in global_chat_buffer)
    summary = gemini_handler.summarize_global_chat(transcript)
    database_handler.save_hierarchical_memory("transfer", summary)
    global_chat_buffer = []
    database_handler.add_live_log("STATUS", "Buffer global sumarizado e limpo.")

def cleanup_inactive_memory():
    now = datetime.now()
    inactive_users = [user for user, data in list(short_term_memory.items()) if now - data['last_interaction'] > timedelta(minutes=MEMORY_EXPIRATION_MINUTES)]
    for user in inactive_users:
        database_handler.add_live_log("MEMÓRIA PESSOAL", f"Usuário {user} inativo. Sumarizando memória.")
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
        
        database_handler.add_live_log("CHAT", f"{user_info}: {message_content}")
        
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
            
            debug_string = (
                f"Usuário: '{user_info}' | Pergunta: '{question[:50]}...'\n"
                f"Contextos: Lorebook ({len(current_lorebook)}), Mem. Pessoal ({len(long_term_memories)}), Mem. Global ({len(hierarchical_memories)})"
            )
            database_handler.update_bot_debug_status(debug_string)
            
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
        database_handler.add_live_log("ERRO", f"Erro em process_message: {e}")
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
            database_handler.add_live_log("ERRO", f"Erro no loop de escuta: {e}")
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
        database_handler.add_live_log("STATUS", "Conectando ao IRC da Twitch...")
        sock.connect((HOST, PORT))
        sock.send(f"PASS {TTV_TOKEN}\n".encode('utf-8'))
        sock.send(f"NICK {BOT_NICK}\n".encode('utf-8'))
        sock.send(f"JOIN #{TTV_CHANNEL}\n".encode('utf-8'))
        database_handler.add_live_log("STATUS", "Conectado e autenticado.")
        time.sleep(2)
        database_handler.update_bot_status("Online")
        send_chat_message(sock, f"AI_Yuh (v3.1.0-mission-control) online.")
        listen_for_messages(sock)
    except Exception as e:
        database_handler.add_live_log("ERRO", f"Erro fatal na conexão: {e}")
        logging.critical(f"Erro fatal na conexão: {e}", exc_info=True)
    finally:
        database_handler.add_live_log("STATUS", "Desligando...")
        database_handler.update_bot_status("Offline")
        sock.close()

if __name__ == "__main__":
    main()