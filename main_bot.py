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
import re

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
MEMORY_EXPIRATION_MINUTES = 10
MAX_HISTORY_LENGTH = 10
TIMEZONE = pytz.timezone('America/Sao_Paulo')
BOT_STATE = 'ASLEEP'
sock_global = None # Socket global para ser usado por funções agendadas

def go_to_sleep():
    global BOT_STATE
    if BOT_STATE == 'AWAKE':
        BOT_STATE = 'ASLEEP'
        database_handler.add_live_log("STATUS", "Bot DESATIVADO automaticamente pelo agendador.")
        logging.info("Bot entrando em modo ASLEEP por agendamento.")

def force_consolidate_daily():
    if BOT_STATE == 'ASLEEP':
        database_handler.add_live_log("ERRO", "O bot precisa estar AWAKE para forçar sumarização.")
        return
    database_handler.add_live_log("STATUS", "Iniciando sumarização diária forçada...")
    consolidate_daily_memories(force=True)

def force_consolidate_weekly():
    if BOT_STATE == 'ASLEEP':
        database_handler.add_live_log("ERRO", "O bot precisa estar AWAKE para forçar sumarização.")
        return
    database_handler.add_live_log("STATUS", "Iniciando sumarização semanal forçada...")
    consolidate_weekly_memories(force=True)

def force_consolidate_monthly():
    if BOT_STATE == 'ASLEEP':
        database_handler.add_live_log("ERRO", "O bot precisa estar AWAKE para forçar sumarização.")
        return
    database_handler.add_live_log("STATUS", "Iniciando sumarização mensal forçada...")
    consolidate_monthly_memories(force=True)

def force_consolidate_yearly():
    if BOT_STATE == 'ASLEEP':
        database_handler.add_live_log("ERRO", "O bot precisa estar AWAKE para forçar sumarização.")
        return
    database_handler.add_live_log("STATUS", "Iniciando sumarização anual forçada...")
    consolidate_yearly_memories(force=True)
    
def force_consolidate_secular():
    if BOT_STATE == 'ASLEEP':
        database_handler.add_live_log("ERRO", "O bot precisa estar AWAKE para forçar sumarização.")
        return
    database_handler.add_live_log("STATUS", "Iniciando sumarização secular forçada...")
    consolidate_secular_memories(force=True)

def check_control_signals():
    signals = database_handler.get_and_clear_signals()
    if not signals: return
    for s in signals:
        signal = s.get('signal')
        database_handler.add_live_log("STATUS", f"Recebido sinal de controle: '{signal}'")
        if signal == 'FORCE_DAILY_SUMMARY': force_consolidate_daily()
        elif signal == 'FORCE_WEEKLY_SUMMARY': force_consolidate_weekly()
        elif signal == 'FORCE_MONTHLY_SUMMARY': force_consolidate_monthly()
        elif signal == 'FORCE_YEARLY_SUMMARY': force_consolidate_yearly()
        elif signal == 'FORCE_SECULAR_SUMMARY': force_consolidate_secular()
        else: database_handler.add_live_log("ERRO", f"Sinal de controle desconhecido: '{signal}'")

def check_reminders():
    if BOT_STATE != 'AWAKE' or sock_global is None: return
    
    reminders = database_handler.get_active_reminders(TTV_CHANNEL)
    now_utc = datetime.now(pytz.utc)

    for r in reminders:
        should_execute = False
        trigger_type = r.get('trigger_type')
        last_executed_str = r.get('last_executed_at')
        
        if trigger_type == 'live_on' and last_executed_str is None:
            should_execute = True
        
        elif trigger_type == 'interval':
            trigger_value_str = r.get('trigger_value', '0m')
            try:
                value = int(re.findall(r'\d+', trigger_value_str)[0])
                unit = re.findall(r'[a-zA-Z]+', trigger_value_str)[0].lower()
                
                if unit == 'm': delta = timedelta(minutes=value)
                elif unit == 'h': delta = timedelta(hours=value)
                else: continue
                
                if last_executed_str is None:
                    should_execute = True
                else:
                    last_executed_dt = datetime.fromisoformat(last_executed_str)
                    if now_utc >= last_executed_dt + delta:
                        should_execute = True
            except (IndexError, ValueError):
                continue
        
        if should_execute:
            content = r.get('content')
            target = r.get('target_user')
            message = f"@{target} Lembrete: {content}" if target else f"Lembrete para o chat: {content}"
            
            send_chat_message(sock_global, message)
            database_handler.update_reminder_execution_time(r['id'])
            if trigger_type == 'live_on':
                database_handler.supabase_client.table('reminders').update({"is_active": False}).eq("id", r['id']).execute()

def run_scheduler():
    logging.info("Agendador de memória e tarefas iniciado.")
    database_handler.add_live_log("STATUS", "Agendador iniciado.")
    
    schedule.every().minute.do(check_control_signals)
    schedule.every().minute.do(check_reminders)
    schedule.every(2).minutes.do(send_heartbeat)
    schedule.every().day.at("00:15", str(TIMEZONE)).do(consolidate_daily_memories)
    schedule.every().monday.at("01:00", str(TIMEZONE)).do(consolidate_weekly_memories)
    schedule.every().day.at("01:30", str(TIMEZONE)).do(consolidate_monthly_memories)
    schedule.every().day.at("02:00", str(TIMEZONE)).do(consolidate_yearly_memories)
    schedule.every().day.at("02:30", str(TIMEZONE)).do(consolidate_secular_memories)
    schedule.every().day.at("03:00", str(TIMEZONE)).do(database_handler.delete_old_logs)
    
    auto_sleep_enabled = BOT_SETTINGS.get('auto_sleep_enabled', False)
    auto_sleep_time = BOT_SETTINGS.get('auto_sleep_time')
    if auto_sleep_enabled and auto_sleep_time and isinstance(auto_sleep_time, str) and len(auto_sleep_time) == 5:
        try:
            schedule.every().day.at(auto_sleep_time, str(TIMEZONE)).do(go_to_sleep)
            database_handler.add_live_log("STATUS", f"Auto-Sleep agendado para as {auto_sleep_time} (UTC-3).")
        except Exception as e:
            database_handler.add_live_log("ERRO", f"Horário de Auto-Sleep inválido: {auto_sleep_time}. Erro: {e}")

    while True:
        schedule.run_pending()
        time.sleep(1)

def consolidate_weekly_memories(force=False):
    log_prefix = "SUMARIZAÇÃO FORÇADA" if force else "SUMARIZAÇÃO GLOBAL"
    database_handler.add_live_log(log_prefix, "Verificando memórias 'daily' para consolidação semanal.")
    daily_memories = database_handler.get_memories_for_consolidation("daily")
    if len(daily_memories) < 7 and not force:
        database_handler.add_live_log("STATUS", f"Apenas {len(daily_memories)}/7 memórias diárias. Aguardando.")
        return
    if not daily_memories:
        database_handler.add_live_log("STATUS", "Nenhuma memória diária para sumarizar.")
        return
    memories_to_summarize = daily_memories if force else daily_memories[:7]
    database_handler.add_live_log(log_prefix, f"Sumarizando {len(memories_to_summarize)} memórias diárias...")
    full_text = "\n\n".join([f"Eventos de {datetime.fromisoformat(mem['metadata']['date']).strftime('%A, %d/%m/%Y')}:\n{mem['summary']}" for mem in memories_to_summarize if mem.get('metadata') and mem['metadata'].get('date')])
    weekly_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos da semana:\n{full_text}", "semanal")
    start_date = memories_to_summarize[0]['metadata']['date']
    end_date = memories_to_summarize[-1]['metadata']['date']
    metadata = {"start_date": start_date, "end_date": end_date, "forced": force}
    database_handler.save_hierarchical_memory("weekly", weekly_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_live_log("MEMÓRIA GLOBAL", "Memória semanal consolidada.")

def consolidate_monthly_memories(force=False):
    log_prefix = "SUMARIZAÇÃO FORÇADA" if force else "SUMARIZAÇÃO GLOBAL"
    database_handler.add_live_log(log_prefix, "Verificando memórias 'weekly' para consolidação mensal.")
    weekly_memories = database_handler.get_memories_for_consolidation("weekly")
    if len(weekly_memories) < 4 and not force:
        database_handler.add_live_log("STATUS", f"Apenas {len(weekly_memories)}/4 memórias semanais. Aguardando.")
        return
    if not weekly_memories:
        database_handler.add_live_log("STATUS", "Nenhuma memória semanal para sumarizar.")
        return
    memories_to_summarize = weekly_memories if force else weekly_memories[:4]
    database_handler.add_live_log(log_prefix, f"Sumarizando {len(memories_to_summarize)} memórias semanais...")
    full_text = "\n\n".join([f"Resumo da semana de {mem['metadata']['start_date']} a {mem['metadata']['end_date']}:\n{mem['summary']}" for mem in memories_to_summarize if mem.get('metadata') and mem['metadata'].get('start_date')])
    monthly_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos mais importantes do mês a seguir:\n{full_text}", "mensal")
    month_name = datetime.fromisoformat(memories_to_summarize[0]['metadata']['start_date']).strftime('%B de %Y')
    metadata = {"month": month_name, "forced": force}
    database_handler.save_hierarchical_memory("monthly", monthly_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_live_log("MEMÓRIA GLOBAL", "Memória mensal consolidada e memórias semanais limpas.")

def consolidate_yearly_memories(force=False):
    log_prefix = "SUMARIZAÇÃO FORÇADA" if force else "SUMARIZAÇÃO GLOBAL"
    database_handler.add_live_log(log_prefix, "Verificando memórias 'monthly' para consolidação anual.")
    monthly_memories = database_handler.get_memories_for_consolidation("monthly")
    if len(monthly_memories) < 12 and not force:
        database_handler.add_live_log("STATUS", f"Apenas {len(monthly_memories)}/12 memórias mensais. Aguardando.")
        return
    if not monthly_memories:
        database_handler.add_live_log("STATUS", "Nenhuma memória mensal para sumarizar.")
        return
    memories_to_summarize = monthly_memories if force else monthly_memories[:12]
    database_handler.add_live_log(log_prefix, f"Sumarizando {len(memories_to_summarize)} memórias mensais...")
    full_text = "\n\n".join([f"Resumo de {mem['metadata']['month']}:\n{mem['summary']}" for mem in memories_to_summarize if mem.get('metadata') and mem['metadata'].get('month')])
    year_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos mais importantes do ano a seguir:\n{full_text}", "anual")
    year_number = datetime.now(TIMEZONE).year - 1
    metadata = {"year": year_number, "forced": force}
    database_handler.save_hierarchical_memory("yearly", year_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_live_log("MEMÓRIA GLOBAL", "Memória anual consolidada e memórias mensais limpas.")

def consolidate_secular_memories(force=False):
    log_prefix = "SUMARIZAÇÃO FORÇADA" if force else "SUMARIZAÇÃO GLOBAL"
    database_handler.add_live_log(log_prefix, "Verificando memórias 'yearly' para consolidação secular.")
    yearly_memories = database_handler.get_memories_for_consolidation("yearly")
    if len(yearly_memories) < 100 and not force:
        database_handler.add_live_log("STATUS", f"Apenas {len(yearly_memories)}/100 memórias anuais. Aguardando.")
        return
    if not yearly_memories:
        database_handler.add_live_log("STATUS", "Nenhuma memória anual para sumarizar.")
        return
    memories_to_summarize = yearly_memories if force else yearly_memories[:100]
    database_handler.add_live_log(log_prefix, f"Sumarizando {len(memories_to_summarize)} memórias anuais...")
    full_text = "\n\n".join([f"Resumo do ano {mem['metadata']['year']}:\n{mem['summary']}" for mem in memories_to_summarize if mem.get('metadata') and mem['metadata'].get('year')])
    century_summary = gemini_handler.summarize_global_chat(f"Resuma os eventos mais importantes do século a seguir:\n{full_text}", "secular")
    start_year = memories_to_summarize[0]['metadata']['year']
    end_year = memories_to_summarize[-1]['metadata']['year']
    metadata = {"start_year": start_year, "end_year": end_year, "forced": force}
    database_handler.save_hierarchical_memory("century", century_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_summarize]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_live_log("MEMÓRIA GLOBAL", "Memória secular consolidada e memórias anuais limpas.")

def consolidate_daily_memories(force=False):
    if BOT_STATE == 'ASLEEP' and not force: return
    
    log_prefix = "SUMARIZAÇÃO FORÇADA" if force else "SUMARIZAÇÃO GLOBAL"
    database_handler.add_live_log(log_prefix, "Verificando memórias 'transfer' para consolidação diária.")
    
    memories_to_consolidate = []
    if force:
        memories_to_consolidate = database_handler.get_memories_for_consolidation("transfer")
    else:
        today = datetime.now(TIMEZONE).date()
        yesterday = today - timedelta(days=1)
        start_of_yesterday = TIMEZONE.localize(datetime.combine(yesterday, datetime.min.time()))
        end_of_yesterday = TIMEZONE.localize(datetime.combine(yesterday, datetime.max.time()))
        memories_to_consolidate = database_handler.get_memories_for_consolidation("transfer", start_of_yesterday, end_of_yesterday)
        
    if not memories_to_consolidate:
        database_handler.add_live_log("STATUS", "Nenhuma memória 'transfer' para consolidar.")
        return
        
    database_handler.add_live_log(log_prefix, f"{len(memories_to_consolidate)} memórias 'transfer' encontradas. Sumarizando...")
    full_text = "\n\n".join([mem['summary'] for mem in memories_to_consolidate if mem.get('summary')])
    daily_summary = gemini_handler.summarize_global_chat(f"Resuma os seguintes eventos:\n{full_text}", "diário")
    
    metadata_date = datetime.now(TIMEZONE).isoformat() if force else (datetime.now(TIMEZONE).date() - timedelta(days=1)).isoformat()
    metadata = {"date": metadata_date, "forced": force}
    
    database_handler.save_hierarchical_memory("daily", daily_summary, metadata)
    ids_to_delete = [mem['id'] for mem in memories_to_consolidate]
    database_handler.delete_memories_by_ids(ids_to_delete)
    database_handler.add_live_log("MEMÓRIA GLOBAL", "Memória diária consolidada.")

def send_heartbeat():
    database_handler.update_bot_status(f"Online ({BOT_STATE})")

def send_chat_message(sock, message):
    try:
        if '\n' in message: messages_to_send = message.split('\n')
        else: messages_to_send = [message]
        for line in messages_to_send:
            clean_line = line.strip()
            if not clean_line: continue
            sock.send(f"PRIVMSG #{TTV_CHANNEL} :{clean_line}\n".encode('utf-8'))
            database_handler.add_live_log("CHAT", f"BOT > {clean_line}")
            time.sleep(1.2)
    except Exception as e:
        database_handler.add_live_log("ERRO", f"Erro ao enviar msg: {e}")

def summarize_and_clear_global_buffer():
    global global_chat_buffer
    MIN_MESSAGES_FOR_SUMMARY = 5
    if len(global_chat_buffer) < MIN_MESSAGES_FOR_SUMMARY:
        if global_chat_buffer:
            database_handler.add_live_log("STATUS", f"Buffer com apenas {len(global_chat_buffer)} msgs. Descartando sem sumarizar.")
            global_chat_buffer = []
        return
    database_handler.add_live_log("SUMARIZAÇÃO GLOBAL", f"Sumarizando buffer global com {len(global_chat_buffer)} mensagens.")
    transcript = "\n".join(f"[{msg['timestamp'].strftime('%H:%M')}] {msg['user']}: {msg['content']}" for msg in global_chat_buffer)
    summary = gemini_handler.summarize_global_chat(transcript, "transferência")
    if "erro" not in summary.lower() and len(summary) > 10:
        start_time = global_chat_buffer[0]['timestamp']
        end_time = global_chat_buffer[-1]['timestamp']
        metadata = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "message_count": len(global_chat_buffer)
        }
        database_handler.save_hierarchical_memory("transfer", summary, metadata)
    else:
        database_handler.add_live_log("ERRO", f"Sumarização falhou ou retornou conteúdo inválido: '{summary}'")
    global_chat_buffer = []
    database_handler.add_live_log("STATUS", "Buffer global sumarizado e limpo.")

def cleanup_inactive_memory():
    if BOT_STATE == 'ASLEEP': return
    now = datetime.now()
    inactive_users = [user for user, data in list(short_term_memory.items()) if now - data['last_interaction'] > timedelta(minutes=MEMORY_EXPIRATION_MINUTES)]
    for user in inactive_users:
        user_permission = database_handler.get_user_permission(user)
        if user_permission == 'master':
            database_handler.add_live_log("MEMÓRIA PESSOAL", f"Usuário master '{user}' inativo. Sumarizando e salvando memória.")
            user_memory_data = short_term_memory[user]
            summary = gemini_handler.summarize_conversation(user_memory_data['history'])
            database_handler.save_long_term_memory(user, summary)
        else:
            database_handler.add_live_log("MEMÓRIA PESSOAL", f"Usuário normal '{user}' inativo. Limpando memória de curto prazo.")
        del short_term_memory[user]

def process_message(sock, raw_message):
    global BOT_STATE, LOREBOOK
    try:
        if "PRIVMSG" not in raw_message: return
        source, _, message_body = raw_message.partition('PRIVMSG')
        user_info = source.split('!')[0][1:]
        message_content = message_body.split(':', 1)[1].strip()
        if user_info.lower() == BOT_NICK: return
        
        user_permission = database_handler.get_user_permission(user_info)
        msg_lower = message_content.lower()
        
        if BOT_STATE == 'ASLEEP':
            if user_info.lower() == 'streamelements' and 'a mãe ta oooooooooon!' in msg_lower:
                BOT_STATE = 'AWAKE'
                database_handler.add_live_log("STATUS", "Bot ATIVADO pelo anúncio de live.")
                send_chat_message(sock, "Alerta de live detectado. AI_Yuh ativada e pronta para interagir!")
                check_reminders()
                return
            if msg_lower == '!awake' and user_permission == 'master':
                BOT_STATE = 'AWAKE'
                database_handler.add_live_log("STATUS", f"Bot ATIVADO manualmente por {user_info}.")
                send_chat_message(sock, f"Entendido, {user_info}. Ativando sistemas. AI_Yuh está online.")
                check_reminders()
                return
            return

        elif BOT_STATE == 'AWAKE':
            if msg_lower == '!sleep' and user_permission == 'master':
                BOT_STATE = 'ASLEEP'
                database_handler.add_live_log("STATUS", f"Bot DESATIVADO manualmente por {user_info}.")
                send_chat_message(sock, "Entendido. Desativando sistemas e entrando em modo de baixo consumo.")
                return

            if user_permission in ['blacklist', 'bot']:
                return 
            
            database_handler.add_live_log("CHAT", f"{user_info}: {message_content}")
            
            if message_content.startswith('!learn '):
                if user_permission == 'master':
                    fact = message_content[len('!learn '):].strip()
                    if fact and database_handler.add_lorebook_entry(fact, user_info):
                        LOREBOOK = database_handler.get_current_lorebook()
                        send_chat_message(sock, f"@{user_info} Lorebook atualizado! Anotado.")
                    else:
                        send_chat_message(sock, f"@{user_info} Tive um problema para aprender isso.")
                else:
                    send_chat_message(sock, f"Desculpe @{user_info}, apenas mestres podem me ensinar.")
                return

            question = ""
            is_activated = False
            mention_str = f"@{BOT_NICK}"
            
            if message_content.startswith('!ask '):
                is_activated = True
                question = message_content[len('!ask '):].strip()
            elif mention_str in msg_lower:
                is_activated = True
                question = re.sub(mention_str, '', message_content, flags=re.IGNORECASE).strip()
                if not question:
                    is_activated = False

            if is_activated and question:
                long_term_memories = database_handler.search_long_term_memory(user_info)
                current_lorebook = database_handler.get_current_lorebook()
                hierarchical_memories = database_handler.search_hierarchical_memory()
                user_memory = short_term_memory.get(user_info, {"history": []})
                
                timezone_str = BOT_SETTINGS.get('timezone', 'America/Sao_Paulo')
                try: user_timezone = pytz.timezone(timezone_str)
                except pytz.UnknownTimeZoneError: user_timezone = pytz.timezone('America/Sao_Paulo')
                current_time_str = datetime.now(user_timezone).strftime('%d de %B de %Y, %H:%M:%S (%Z)')

                debug_string = (
                    f"Usuário: '{user_info}' | Pergunta: '{question[:50]}...'\n"
                    f"Contextos: Lorebook ({len(current_lorebook)}), Mem. Pessoal ({len(long_term_memories)}), Mem. Global ({len(hierarchical_memories)})"
                )
                database_handler.update_bot_debug_status(debug_string)
                
                final_response = gemini_handler.generate_interactive_response(
                    question, user_memory['history'], BOT_SETTINGS, current_lorebook, long_term_memories, hierarchical_memories, user_info, user_permission, current_time=current_time_str
                )
                
                send_chat_message(sock, f"@{user_info} {final_response}")
                
                user_memory['history'].append({'role': 'user', 'parts': [question]})
                user_memory['history'].append({'role': 'model', 'parts': [final_response]})
                user_memory['last_interaction'] = datetime.now()
                if len(user_memory['history']) > MAX_HISTORY_LENGTH * 2:
                    user_memory['history'] = user_memory['history'][-MAX_HISTORY_LENGTH*2:]
                short_term_memory[user_info] = user_memory
            else:
                global_chat_buffer.append({"user": user_info, "content": message_content, "timestamp": datetime.now(TIMEZONE)})

    except Exception as e:
        database_handler.add_live_log("ERRO", f"Erro em process_message: {e}")
        logging.error(f"Erro em process_message: {e}", exc_info=True)

def listen_for_messages(sock):
    buffer = ""; last_cleanup = time.time(); last_global_summary = time.time()
    while True:
        try:
            now = time.time()
            if BOT_STATE == 'AWAKE' and now - last_cleanup > 60:
                cleanup_inactive_memory(); last_cleanup = now
            if BOT_STATE == 'AWAKE' and (len(global_chat_buffer) >= GLOBAL_BUFFER_MAX_MESSAGES or now - last_global_summary > (GLOBAL_BUFFER_MAX_MINUTES * 60)):
                summarize_and_clear_global_buffer(); last_global_summary = now
            
            buffer += sock.recv(4096).decode('utf-8', errors='ignore')
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
    global BOT_SETTINGS, LOREBOOK, BOT_STATE, sock_global
    BOT_SETTINGS, LOREBOOK = database_handler.load_initial_data()
    if not BOT_SETTINGS:
        logging.critical("Não foi possível carregar as configs do bot."); return
    gemini_handler.load_models_from_settings(BOT_SETTINGS)
    if not gemini_handler.GEMINI_ENABLED or not database_handler.DB_ENABLED:
        logging.critical("Módulos essenciais falharam."); return
    
    scheduler_thread = threading.Thread(target=run_scheduler, name="SchedulerThread", daemon=True)
    scheduler_thread.start()
    
    sock = socket.socket()
    sock_global = sock
    sock.settimeout(60.0)
    try:
        database_handler.add_live_log("STATUS", "Conectando ao IRC da Twitch...")
        sock.connect((HOST, PORT))
        sock.send(f"PASS {TTV_TOKEN}\n".encode('utf-8'))
        sock.send(f"NICK {BOT_NICK}\n".encode('utf-8'))
        sock.send(f"JOIN #{TTV_CHANNEL}\n".encode('utf-8'))
        database_handler.add_live_log("STATUS", "Conectado. Entrando em modo de baixo consumo.")
        time.sleep(2)
        BOT_STATE = 'ASLEEP'
        database_handler.update_bot_status(f"Online ({BOT_STATE})")
        send_chat_message(sock, f"AI_Yuh (v4.1.1-final) em modo de espera.")
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