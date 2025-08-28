# shared_state.py
from collections import deque
from datetime import datetime
import pytz

TIMEZONE = pytz.timezone('America/Sao_Paulo')
log_queue = deque(maxlen=100)

def log_to_panel(level: str, message: str, thread_name: str = "Thread"):
    """
    Função centralizada para adicionar logs à fila do painel.
    Isso evita o uso de manipuladores de log complexos e nos dá controle direto.
    """
    timestamp = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
    formatted_log = f"{timestamp} [{thread_name}] - {level.upper()} - {message}"
    log_queue.append(formatted_log)