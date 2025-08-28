# app.py
import os
import threading
import time
import logging

# Configuração simples do logger apenas para o console
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(threadName)s] - %(levelname)s - %(message)s')

# Importa a função principal do bot
from main_bot import main as run_bot_main
# Importa nossa nova função de log
from shared_state import log_to_panel

def start_bot_thread():
    """Função que será executada na thread do bot."""
    log_to_panel("INFO", "Iniciando a thread do bot...", "BotThread")
    try:
        run_bot_main()
    except Exception as e:
        log_to_panel("CRITICAL", f"A thread do bot encontrou um erro fatal: {e}", "BotThread")
        logging.critical(f"A thread do bot encontrou um erro fatal: {e}", exc_info=True)
    log_to_panel("INFO", "A thread do bot foi finalizada.", "BotThread")


if __name__ == "__main__":
    # 1. Iniciar o bot em uma thread de fundo
    bot_thread = threading.Thread(target=start_bot_thread, name="BotThread", daemon=True)
    bot_thread.start()

    log_to_panel("INFO", "Thread do bot iniciada. Aguardando 5 segundos...", "MainThread")
    time.sleep(5)

    # 2. Iniciar o painel Streamlit na thread principal
    log_to_panel("INFO", "Iniciando o painel de controle Streamlit...", "MainThread")
    
    port = os.environ.get("PORT", 8501)
    
    streamlit_command = f"streamlit run panel.py --server.port {port} --server.enableCORS false --server.enableXsrfProtection false"
    
    os.system(streamlit_command)