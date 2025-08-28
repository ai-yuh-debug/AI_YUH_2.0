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

# Configuração do logger para ser consistente em todo o projeto
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
UNCERTAINTY_KEYWORDS = ["não sei", "nao sei", "não tenho certeza", "não tenho acesso", "desconheço", "não consigo encontrar"]
TIMEZONE = pytz.timezone('America/Sao_Paulo')

def run_scheduler():
    """Executa o loop do agendador de tarefas em uma thread dedicada."""
    logging.info("Agendador de memória iniciado.")
    while True:
        schedule.run_pending()
        time.sleep(1)

def consolidate_daily_memories():
    """Tarefa agendada para consolidar as memórias 'transfer' do dia anterior em uma memória 'daily'."""
    logging.info("AGENDADOR: Verificando memórias 'transfer' para consolidação diária.")
    today = datetime.now(TIMEZONE).date()
    yesterday = today - timedelta(days=1)
    start_of_yesterday = TIMEZONE.localize(datetime.combine(yesterday, datetime.min.time()))
    end_of_yesterday = TIMEZONE.localize(datetime.combine(yesterday, datetime.max.time()))
    
    memories_to_consolidate = database_handler.get_memories_for_consolidation("transfer", start_of_yesterday, end_of_yesterday)
    
    if not memories_to_consolidate:
        logging.info("AGENDADOR: Nenhuma memória 'transfer' de ontem para consolidar."); return
    
    logging.info(f"AGENDADOR: Encontradas {len(memories_to_consolidate)} memórias. Sumarizando...")
    full_text = "\n\n".join([mem['summary'] for mem in memories_to_consolidate])
    daily_summary = gemini_handler.summarize_global_chat(f"Resuma os seguintes eventos do dia {yesterday.strftime('%d/%m/%Y')}:\n{full_text}")
    metadata = {"date": yesterday.isoformat()}
    database_handler.save_hierarchical_memory("daily", daily_summary, metadata)
    
    ids_to_delete = [mem['id'] for mem in memories_to_consolidate]
    database_handler.delete_memories_by_ids(ids_to_delete)
    logging.info("AGENDADOR: Memória diária consolidada e memórias 'transfer' limpas.")

def send_heartbeat():
    """Tarefa agendada para atualizar o status do bot no painel, confirmando que está online."""
    database_handler.update_bot_status("Online")

# =========================================================================================
#                      ESTA É A FUNÇÃO CORRIGIDA
# =========================================================================================
def send_chat_message(sock, message):
    """
    Envia uma mensagem para o chat da Twitch.
    Se a mensagem for muito longa ou tiver múltiplas linhas, ela será dividida.
    """
    try:
        # Se a mensagem contém quebras de linha, trate-a como uma lista de mensagens.
        if '\n' in message:
            messages_to_send = message.split('\n')
        else:
            # Se não, coloque a única mensagem em uma lista para usar o mesmo loop.
            messages_to_send = [message]

        for line in messages_to_send:
            # Ignora linhas vazias que podem ser resultado de .split('\n')
            clean_line = line.strip()
            if not clean_line:
                continue

            # Garante que a linha não exceda o limite de caracteres da Twitch
            # (Um valor seguro é ~450 para dar margem para o prefixo PRIVMSG etc.)
            if len(clean_line) > 450:
                # Se uma única linha for muito longa, a quebramos também.
                parts = [clean_line[i:i+450] for i in range(0, len(clean_line), 450)]
                for part in parts:
                    sock.send(f"PRIVMSG #{TTV_CHANNEL} :{part}\n".encode('utf-8'))
                    logging.info(f"BOT (parte) > {part}")
                    time.sleep(0.8) # Pausa um pouco maior para evitar spam
            else:
                sock.send(f"PRIVMSG #{TTV_CHANNEL} :{clean_line}\n".encode('utf-8'))
                logging.info(f"BOT > {clean_line}")
                time.sleep(0.8) # Pausa entre cada linha para evitar ser mutado (rate limiting)

    except Exception as e:
        logging.error(f"Erro ao enviar mensagem: {e}", exc_info=True)
# =========================================================================================

def summarize_and_clear_global_buffer():
    """Sumariza o buffer global de chat e o limpa."""
    global global_chat_buffer
    if not global_chat_buffer: return
    
    logging.info(f"Buffer de transferência atingiu o limite: {len(global_chat_buffer)} mensagens.")
    transcript = "\n".join(f"[{msg['timestamp'].strftime('%H:%M')}] {msg['user']}: {msg['content']}" for msg in global_chat_buffer)
    summary = gemini_handler.summarize_global_chat(transcript)
    database_handler.save_hierarchical_memory("transfer", summary)
    global_chat_buffer = []
    logging.info("Buffer de transferência sumarizado e limpo.")
    
def cleanup_inactive_memory():
    """Limpa a memória de curto prazo de usuários inativos e a consolida na memória de longo prazo."""
    now = datetime.now()
    # Usar list() para criar uma cópia, permitindo a modificação do dicionário durante a iteração
    inactive_users = [user for user, data in list(short_term_memory.items()) if now - data['last_interaction'] > timedelta(minutes=MEMORY_EXPIRATION_MINUTES)]
    for user in inactive_users:
        logging.info(f"Usuário {user} inativo. Sumarizando memória pessoal...")
        user_memory = short_term_memory.pop(user)
        summary = gemini_handler.summarize_conversation(user_memory['history'])
        database_handler.save_long_term_memory(user, summary)

def process_message(sock, raw_message):
    """Processa uma única mensagem recebida do chat da Twitch."""
    try:
        if "PRIVMSG" not in raw_message: return
        
        source, _, message_body = raw_message.partition('PRIVMSG')
        user_info = source.split('!')[0][1:]
        message_content = message_body.split(':', 1)[1].strip()
        
        if user_info.lower() == BOT_NICK: return
        
        logging.info(f"{user_info}: {message_content}")
        
        global_chat_buffer.append({"user": user_info, "content": message_content, "timestamp": datetime.now(TIMEZONE)})
        
        user_permission = database_handler.get_user_permission(user_info)
        if user_permission == 'blacklist': return

        msg_lower = message_content.lower()
        
        # Lógica para o comando !learn
        learn_command = "!learn "
        if msg_lower.startswith(learn_command):
            if user_permission == 'master':
                fact = message_content[len(learn_command):].strip()
                if fact and database_handler.add_lorebook_entry(fact, user_info):
                    global LOREBOOK
                    LOREBOOK = database_handler.get_current_lorebook() # Atualiza o lorebook em memória
                    send_chat_message(sock, f"@{user_info} Entendido. Adicionei o fato à minha base de conhecimento.")
                else:
                    send_chat_message(sock, f"@{user_info} Tive um problema para aprender isso.")
            else:
                send_chat_message(sock, f"Desculpe @{user_info}, apenas mestres podem me ensinar.")
            return

        # Lógica para ativação do bot (!ask ou menção)
        activation_ask = "!ask "; activation_mention = f"@{BOT_NICK} "
        question = ""; is_activated = False
        if msg_lower.startswith(activation_ask): is_activated=True; question=message_content[len(activation_ask):].strip()
        elif msg_lower.startswith(activation_mention): is_activated=True; question=message_content[len(activation_mention):].strip()

        if is_activated and question:
            # Coleta de todos os contextos
            current_lorebook = database_handler.get_current_lorebook()
            long_term_memories = database_handler.search_long_term_memory(user_info)
            hierarchical_memories = database_handler.search_hierarchical_memory()
            user_memory = short_term_memory.get(user_info, {"history": []})
            
            logging.info(f"Gerando resposta para {user_info} sem busca na web...")
            initial_response = gemini_handler.generate_response_without_search(question, user_memory['history'], BOT_SETTINGS, current_lorebook, long_term_memories, hierarchical_memories)
            
            final_response = initial_response
            # Verifica se a IA deu uma resposta incerta para decidir se busca na web
            if any(keyword in initial_response.lower() for keyword in UNCERTAINTY_KEYWORDS):
                logging.info("Resposta inicial indica incerteza. Realizando busca na web.")
                web_context = gemini_handler.web_search(question)
                if web_context:
                    final_response = gemini_handler.generate_response_with_search(question, user_memory['history'], BOT_SETTINGS, current_lorebook, long_term_memories, hierarchical_memories, web_context)
            else:
                logging.info("Resposta inicial foi confiante. Não é necessário buscar na web.")

            send_chat_message(sock, f"@{user_info} {final_response}")
            
            # Atualiza a memória de curto prazo do usuário
            user_memory['history'].append({'role': 'user', 'parts': [question]})
            user_memory['history'].append({'role': 'model', 'parts': [final_response]})
            user_memory['last_interaction'] = datetime.now()
            # Garante que a memória não cresça indefinidamente
            if len(user_memory['history']) > MAX_HISTORY_LENGTH * 2: # Mantem pares de user/model
                user_memory['history'] = user_memory['history'][-MAX_HISTORY_LENGTH*2:]
            short_term_memory[user_info] = user_memory
            
    except Exception as e:
        logging.error(f"Erro ao processar mensagem: {raw_message} | Erro: {e}", exc_info=True)

def listen_for_messages(sock):
    """Loop principal que escuta por novas mensagens no socket da Twitch."""
    buffer = ""
    last_cleanup = time.time()
    last_global_summary = time.time()
    while True:
        try:
            now = time.time()
            # Executa tarefas de limpeza e sumarização em intervalos de tempo
            if now - last_cleanup > 60: 
                cleanup_inactive_memory()
                last_cleanup = now
            if len(global_chat_buffer) >= GLOBAL_BUFFER_MAX_MESSAGES or now - last_global_summary > (GLOBAL_BUFFER_MAX_MINUTES * 60):
                summarize_and_clear_global_buffer()
                last_global_summary = now
            
            # Processa dados recebidos do servidor
            buffer += sock.recv(2048).decode('utf-8', errors='ignore')
            messages = buffer.split('\r\n')
            buffer = messages.pop() # Guarda qualquer mensagem incompleta para a próxima iteração
            for raw_message in messages:
                if not raw_message: continue
                # O servidor da Twitch envia PINGs para verificar se a conexão está ativa
                if raw_message.startswith('PING'):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
                    logging.info("PING recebido, PONG enviado.")
                    continue
                process_message(sock, raw_message)
        except socket.timeout:
            # É normal um timeout ocorrer se o chat estiver quieto. Apenas continue.
            continue
        except Exception as e:
            logging.error(f"Erro no loop de escuta: {e}")
            time.sleep(15) # Pausa antes de tentar de novo para evitar spam de erros

def main():
    """Função principal que inicializa e executa o bot."""
    global BOT_SETTINGS, LOREBOOK
    BOT_SETTINGS, LOREBOOK = database_handler.load_initial_data()
    if not BOT_SETTINGS: 
        logging.critical("Não foi possível carregar as configurações do bot. Encerrando."); return
        
    gemini_handler.load_models_from_settings(BOT_SETTINGS)
    if not gemini_handler.GEMINI_ENABLED or not database_handler.DB_ENABLED: 
        logging.critical("Módulos essenciais (Gemini ou DB) falharam ao iniciar. Encerrando."); return
    
    # Configuração do agendador de tarefas
    schedule.every(GLOBAL_BUFFER_MAX_MINUTES).minutes.do(summarize_and_clear_global_buffer)
    schedule.every().day.at("00:15", str(TIMEZONE)).do(consolidate_daily_memories) # Roda 15min depois da meia noite
    schedule.every(2).minutes.do(send_heartbeat)
    
    # Inicia o agendador em uma thread separada para não bloquear o bot
    scheduler_thread = threading.Thread(target=run_scheduler, name="SchedulerThread", daemon=True)
    scheduler_thread.start()
    
    sock = socket.socket()
    sock.settimeout(60.0) # Timeout para evitar bloqueio eterno em recv()
    try:
        send_heartbeat() # Atualiza o status para Online antes de conectar
        logging.info("Conectando ao servidor IRC da Twitch...")
        sock.connect((HOST, PORT))
        logging.info("Conectado. Autenticando...")
        sock.send(f"PASS {TTV_TOKEN}\n".encode('utf-8'))
        sock.send(f"NICK {BOT_NICK}\n".encode('utf-8'))
        sock.send(f"JOIN #{TTV_CHANNEL}\n".encode('utf-8'))
        
        # Espera um pouco pela confirmação de JOIN antes de enviar mensagem
        time.sleep(2) 
        send_chat_message(sock, f"AI_Yuh (v2.4.2-hotfix) online.") # Mudei a versão para refletir a correção
        
        listen_for_messages(sock)
        
    except KeyboardInterrupt:
        logging.info("Desligamento solicitado pelo usuário (Ctrl+C).")
    except Exception as e:
        logging.critical(f"Erro fatal na conexão: {e}", exc_info=True)
    finally:
        logging.info("Desligando... Atualizando status para Offline.")
        database_handler.update_bot_status("Offline")
        sock.close()
        logging.info("Conexão fechada. Adeus!")

# =========================================================================================
# Este bloco `if __name__ == "__main__":` é a mudança crucial.
# Ele garante que a função `main()` só será chamada quando você executa este arquivo
# diretamente (ex: `python main_bot.py`).
#
# Quando o arquivo `app.py` importa o `main_bot.py`, este bloco NÃO é executado,
# o que nos permite controlar o início do bot a partir do `app.py`.
# =========================================================================================
if __name__ == "__main__":
    main()