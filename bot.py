# bot.py

import os
import sys
import socket
import time
import threading
import schedule
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv

import database_handler
import gemini_handler

# --- Carregamento de Configurações do .env ---
load_dotenv()
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
BOT_NICK = os.getenv("BOT_NICK")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL")
HOURLY_MEMORY_LIMIT = int(os.getenv("HOURLY_MEMORY_LIMIT", 40))

# --- Configurações do Servidor IRC da Twitch ---
TWITCH_SERVER = "irc.chat.twitch.tv"
TWITCH_PORT = 6667

# --- Variáveis Globais de Memória ---
chat_buffer = []
last_buffer_processing_time = datetime.now(pytz.utc)
tz_br = pytz.timezone('America/Sao_Paulo')

# --- Funções de Sumarização (Lógica de Memória) ---
def summarize_hourly(archivist_model):
    global chat_buffer, last_buffer_processing_time
    if not chat_buffer:
        print("Buffer de chat vazio. Nenhuma sumarização horária necessária.")
        return
    print("\nIniciando sumarização horária...")
    log_content = "\n".join(chat_buffer)
    start_time = last_buffer_processing_time
    end_time = datetime.now(pytz.utc)
    summary = gemini_handler.get_summary_response(
        archivist_model, log_content, "hourly",
        start_time.strftime('%Y-%m-%d %H:%M:%S'),
        end_time.strftime('%Y-%m-%d %H:%M:%S')
    )
    database_handler.insert_memory("hourly", f"Resumo da hora ({start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}): {summary}", start_time, end_time)
    chat_buffer = []
    last_buffer_processing_time = end_time
    print("Sumarização horária concluída e buffer limpo.")

def summarize_daily(archivist_model):
    print("Verificando sumarização diária...")
    yesterday = datetime.now(tz_br) - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
    end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(pytz.utc)
    hourly_memories = database_handler.get_memories_between("hourly", start, end)
    if not hourly_memories:
        print(f"Nenhuma memória horária encontrada para {start.strftime('%Y-%m-%d')}.")
        return
    print(f"Iniciando sumarização diária para {start.strftime('%Y-%m-%d')}...")
    content = "\n".join([mem['content'] for mem in hourly_memories])
    summary = gemini_handler.get_summary_response(archivist_model, content, "daily", start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    database_handler.insert_memory("daily", f"Resumo do dia {start.strftime('%d/%m/%Y')}: {summary}", start, end)
    database_handler.delete_memories_between("hourly", start, end)
    print("Sumarização diária concluída.")

def summarize_weekly(archivist_model):
    print("Verificando sumarização semanal...")
    today = datetime.now(tz_br)
    if today.weekday() != 0: return # Roda apenas na Segunda-feira
    end = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
    start = end - timedelta(days=6)
    start_utc, end_utc = start.astimezone(pytz.utc), end.astimezone(pytz.utc)
    daily_memories = database_handler.get_memories_between("daily", start_utc, end_utc)
    if not daily_memories:
        print("Nenhuma memória diária na última semana para sumarizar.")
        return
    print("Iniciando sumarização semanal...")
    content = "\n".join([mem['content'] for mem in daily_memories])
    summary = gemini_handler.get_summary_response(archivist_model, content, "weekly", start_utc.strftime('%Y-%m-%d'), end_utc.strftime('%Y-%m-%d'))
    database_handler.insert_memory("weekly", f"Resumo da semana ({start_utc.strftime('%d/%m')} a {end_utc.strftime('%d/%m')}): {summary}", start_utc, end_utc)
    database_handler.delete_memories_between("daily", start_utc, end_utc)
    print("Sumarização semanal concluída.")

# --- Classe Principal do Bot ---

class Bot:
    def __init__(self):
        self.sock = None
        self.load_configs()
        self.interaction_model = gemini_handler.get_generative_model(self.interaction_model_name)
        self.archivist_model = gemini_handler.get_generative_model(self.archivist_model_name)
        if not all([self.interaction_model, self.archivist_model]):
            print("Erro crítico: Não foi possível inicializar os modelos de IA. Verifique API Key e nomes dos modelos.")
            sys.exit(1)

    def load_configs(self):
        print("Buscando configurações dinâmicas do Supabase...")
        settings = database_handler.get_bot_settings()
        masters, blacklisted = database_handler.get_user_roles()
        self.interaction_model_name = settings.get("interaction_model", "gemini-2.5-flash")
        self.archivist_model_name = settings.get("archivist_model", "gemini-1.5-flash-latest") # Conforme solicitado
        self.system_prompt = settings.get("system_prompt", "Você é a AI_YUH, uma IA amigável na Twitch.")
        self.master_users = masters
        self.blacklisted_users = blacklisted
        self.bot_prefix = settings.get("bot_prefix", "!ask")
        print("Configurações carregadas.")
        print(f"  - Modelo Interação: {self.interaction_model_name}")
        print(f"  - Modelo Arquivista: {self.archivist_model_name}")

    def run_scheduler(self):
        schedule.every().day.at("00:05", "America/Sao_Paulo").do(lambda: summarize_daily(self.archivist_model))
        schedule.every().monday.at("00:10", "America/Sao_Paulo").do(lambda: summarize_weekly(self.archivist_model))
        print("Agendador de memória configurado.")
        while True:
            schedule.run_pending()
            time.sleep(1)

    def send_message(self, message):
        try:
            message_to_send = f"PRIVMSG #{TWITCH_CHANNEL} :{message}\r\n"
            self.sock.send(message_to_send.encode("utf-8"))
            print(f"ENVIADO: {message}")
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")

    def run(self):
        while True: # Loop principal para reconexão automática
            try:
                self.sock = socket.socket()
                self.sock.connect((TWITCH_SERVER, TWITCH_PORT))
                self.sock.send(f"PASS {TWITCH_TOKEN}\r\n".encode("utf-8"))
                self.sock.send(f"NICK {BOT_NICK}\r\n".encode("utf-8"))
                self.sock.send(f"JOIN #{TWITCH_CHANNEL}\r\n".encode("utf-8"))
                print(f"Bot conectado como '{BOT_NICK}' ao canal '{TWITCH_CHANNEL}'")

                scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
                scheduler_thread.start()
                print("Thread do sistema de memória iniciada.")

                while True: # Loop de recebimento de mensagens
                    resp = self.sock.recv(4096).decode("utf-8")

                    if not resp:
                        # Conexão fechada pelo servidor
                        print("Conexão fechada pelo servidor. Reconectando...")
                        break # Sai do loop interno para reconectar

                    if resp.startswith("PING"):
                        self.sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                        print("PONG enviado.")
                        continue

                    # Processamento de cada linha recebida, pois podem vir várias
                    for line in resp.splitlines():
                        if "PRIVMSG" not in line:
                            continue

                        parts = line.split(":", 2)
                        if len(parts) < 3: continue
                        
                        user_info = parts[1].split("!", 1)
                        author = user_info[0].strip()
                        message = parts[2].strip()

                        print(f"[{author}]: {message}")

                        if author.lower() in self.blacklisted_users:
                            continue

                        timestamp = datetime.now(pytz.utc).strftime('%H:%M:%S')
                        chat_buffer.append(f"[{timestamp}] {author}: {message}")
                        print(f"Buffer: {len(chat_buffer)}/{HOURLY_MEMORY_LIMIT}", end='\r')
                        if len(chat_buffer) >= HOURLY_MEMORY_LIMIT:
                            threading.Thread(target=summarize_hourly, args=(self.archivist_model,), daemon=True).start()

                        # --- Lógica de Comandos ---
                        if message.lower().startswith(self.bot_prefix):
                            command_body = message[len(self.bot_prefix):].strip()
                            if command_body:
                                print(f"\nComando !ask de {author}: {command_body}")
                                lore_context = database_handler.get_lorebook_entries()
                                memory_items = database_handler.get_all_memories_for_context()
                                memory_context = "\n".join([mem['content'] for mem in memory_items])
                                response = gemini_handler.get_interaction_response(self.interaction_model, command_body, author, self.system_prompt, lore_context, memory_context)
                                self.send_message(f"@{author}, {response}")

                        elif message.lower().startswith("!reload"):
                            if author.lower() in self.master_users:
                                self.load_configs()
                                self.interaction_model = gemini_handler.get_generative_model(self.interaction_model_name)
                                self.archivist_model = gemini_handler.get_generative_model(self.archivist_model_name)
                                self.send_message(f"@{author}, configurações e modelos de IA recarregados com sucesso!")

            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                print("Conexão perdida. Reconectando em 10 segundos...")
                time.sleep(10)
            except socket.gaierror:
                print("Erro de DNS ou rede. Verifique a conexão com a internet. Tentando novamente em 30 segundos...")
                time.sleep(30)
            except Exception as e:
                print(f"Ocorreu um erro inesperado no loop principal: {e}")
                time.sleep(15)

if __name__ == "__main__":
    bot = Bot()
    bot.run()