# bot.py

import os
import time
import threading
import schedule
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from twitchio.ext import commands
import sys

# Importa os nossos handlers
import database_handler
import gemini_handler

# --- Carregamento de Configurações ---
load_dotenv()
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL")
BOT_NICK = os.getenv("BOT_NICK")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!ask")
HOURLY_MEMORY_LIMIT = int(os.getenv("HOURLY_MEMORY_LIMIT", 40))
tz_br = pytz.timezone('America/Sao_Paulo')

# --- Gerenciamento de Memória em RAM ---
chat_buffer = []
last_buffer_processing_time = datetime.now(pytz.utc)

# --- Funções de Sumarização (Lógica de Memória) ---

def summarize_hourly(archivist_model):
    global chat_buffer, last_buffer_processing_time
    if not chat_buffer:
        print("Buffer de chat vazio. Nenhuma sumarização horária necessária.")
        return

    print("Iniciando sumarização horária...")
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

class Bot(commands.Bot):
    def __init__(self):
        self.load_configs() # Carrega configs antes de inicializar o bot
        super().__init__(token=TWITCH_TOKEN, prefix=self.bot_prefix, initial_channels=[TWITCH_CHANNEL])
        self.interaction_model = gemini_handler.get_generative_model(self.interaction_model_name)
        self.archivist_model = gemini_handler.get_generative_model(self.archivist_model_name)
        
        if not all([self.interaction_model, self.archivist_model]):
            print("Erro crítico: Não foi possível inicializar os modelos de IA. Verifique a API Key e os nomes dos modelos.")
            sys.exit(1) # Encerra o programa se os modelos não puderem ser carregados

    def load_configs(self):
        """Carrega configurações do banco de dados."""
        print("Buscando configurações dinâmicas do Supabase...")
        settings = database_handler.get_bot_settings()
        masters, blacklisted = database_handler.get_user_roles()

        self.interaction_model_name = settings.get("interaction_model", "gemini-1.5-pro-latest")
        self.archivist_model_name = settings.get("archivist_model", "gemini-1.5-flash-latest")
        self.system_prompt = settings.get("system_prompt", "Você é a AI_YUH, uma IA amigável na Twitch.")
        self.master_users = masters
        self.blacklisted_users = blacklisted
        self.bot_prefix = settings.get("bot_prefix", BOT_PREFIX)

        print("Configurações carregadas.")

    def run_scheduler(self):
        """Loop que roda as tarefas agendadas."""
        schedule.every().day.at("00:05", "America/Sao_Paulo").do(lambda: summarize_daily(self.archivist_model))
        schedule.every().monday.at("00:10", "America/Sao_Paulo").do(lambda: summarize_weekly(self.archivist_model))
        print("Agendador de memória configurado.")
        while True:
            schedule.run_pending()
            time.sleep(1)

    async def event_ready(self):
        print(f'Bot conectado como | {self.nick}')
        scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        scheduler_thread.start()
        print("Thread do sistema de memória iniciada.")

    async def event_message(self, message):
        if message.echo: return
        if message.author.name.lower() in self.blacklisted_users: return

        timestamp = datetime.now(pytz.utc).strftime('%H:%M:%S')
        chat_buffer.append(f"[{timestamp}] {message.author.name}: {message.content}")
        print(f"Buffer: {len(chat_buffer)}/{HOURLY_MEMORY_LIMIT}", end='\r')

        if len(chat_buffer) >= HOURLY_MEMORY_LIMIT:
            # Roda a sumarização em uma thread separada para não bloquear o bot
            threading.Thread(target=summarize_hourly, args=(self.archivist_model,), daemon=True).start()
        
        await self.handle_commands(message)

    @commands.command(name="ask")
    async def ask_command(self, ctx: commands.Context, *, question: str):
        if ctx.author.name.lower() in self.blacklisted_users: return
        print(f"\nComando !ask de {ctx.author.name}: {question}")

        # Busca contextos em tempo real
        lore_context = database_handler.get_lorebook_entries()
        memory_items = database_handler.get_all_memories_for_context()
        memory_context = "\n".join([mem['content'] for mem in memory_items])
        
        response = gemini_handler.get_interaction_response(
            self.interaction_model, question, ctx.author.name, 
            self.system_prompt, lore_context, memory_context
        )
        await ctx.send(f"@{ctx.author.name}, {response}")

    @commands.command(name="reload")
    async def reload_command(self, ctx: commands.Context):
        """Comando para recarregar as configurações do DB."""
        if ctx.author.name.lower() in self.master_users:
            self.load_configs()
            # Recria os modelos com os novos nomes, se necessário
            self.interaction_model = gemini_handler.get_generative_model(self.interaction_model_name)
            self.archivist_model = gemini_handler.get_generative_model(self.archivist_model_name)
            # Atualiza o prefixo do bot
            self.prefix = self.bot_prefix
            
            await ctx.send(f"@{ctx.author.name}, configurações e modelos de IA recarregados com sucesso!")
        else:
            await ctx.send(f"@{ctx.author.name}, você não tem permissão para usar este comando.")

if __name__ == "__main__":
    bot = Bot()
    bot.run()