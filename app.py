# app.py
import os
import threading
import time
import logging

# Configuração simples do logger apenas para o console da Render
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(threadName)s] - %(levelname)s - %(message)s')

# Importa a função principal do bot
from main_bot import main as run_bot_main

def start_bot_thread():
    """Função que será executada na thread do bot."""
    logging.info("Iniciando a thread do bot...")
    try:
        run_bot_main()
    except Exception as e:
        logging.critical(f"A thread do bot encontrou um erro fatal e foi encerrada: {e}", exc_info=True)
    logging.info("A thread do bot foi finalizada.")

if __name__ == "__main__":
    # 1. Iniciar o bot em uma thread de fundo
    bot_thread = threading.Thread(target=start_bot_thread, name="BotThread", daemon=True)
    bot_thread.start()

    logging.info("Thread do bot iniciada. Aguardando 5 segundos para a inicialização...")
    time.sleep(5)

    # 2. Iniciar o painel Streamlit na thread principal
    logging.info("Iniciando o painel de controle Streamlit...")
    
    port = int(os.environ.get("PORT", 8501))
    
    streamlit_command = f"streamlit run panel.py --server.port {port} --server.enableCORS false --server.enableXsrfProtection false"
    
    os.system(streamlit_command)