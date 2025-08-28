# app.py
import os
import threading
import time
import logging
from logging import Handler

# Importamos nosso estado compartilhado
import shared_state

# ==============================================================================
#                      NOVA CLASSE PARA CAPTURAR LOGS
# ==============================================================================
class QueueLogHandler(Handler):
    """
    Um manipulador de log personalizado que envia os logs para a nossa deque compartilhada.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def emit(self, record):
        """
        Esta função é chamada para cada mensagem de log gerada.
        """
        # Formata a mensagem de log e a adiciona à nossa fila.
        log_entry = self.format(record)
        shared_state.log_queue.append(log_entry)
# ==============================================================================

# Configuração do logger para este arquivo de inicialização
# Formatamos para incluir o nome da thread, que é útil para depuração.
log_format = '%(asctime)s [%(threadName)s] - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)

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
    # ==============================================================================
    #             CONFIGURAÇÃO DO NOVO MANIPULADOR DE LOG
    # ==============================================================================
    # 1. Cria uma instância do nosso manipulador personalizado.
    queue_handler = QueueLogHandler()
    
    # 2. Define o formato da mensagem para este manipulador.
    formatter = logging.Formatter(log_format)
    queue_handler.setFormatter(formatter)
    
    # 3. Adiciona nosso manipulador ao logger raiz.
    # Agora, TODOS os logs gerados em qualquer lugar do nosso código
    # serão enviados para a nossa fila, além de irem para o console.
    logging.getLogger().addHandler(queue_handler)
    # ==============================================================================

    # 1. Iniciar o bot em uma thread de fundo
    bot_thread = threading.Thread(target=start_bot_thread, name="BotThread", daemon=True)
    bot_thread.start()

    logging.info("Thread do bot iniciada. Aguardando 5 segundos para a inicialização...")
    time.sleep(5) # Dá um tempo para o bot começar a conectar antes de iniciar o painel

    # 2. Iniciar o painel Streamlit na thread principal
    logging.info("Iniciando o painel de controle Streamlit...")
    
    port = os.environ.get("PORT", 8501)
    
    streamlit_command = f"streamlit run panel.py --server.port {port} --server.enableCORS false --server.enableXsrfProtection false"
    
    os.system(streamlit_command)