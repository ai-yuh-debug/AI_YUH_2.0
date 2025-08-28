# app.py
import os
import threading
import time
import logging

# Configuração do logger para este arquivo de inicialização
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
    # A thread é configurada como 'daemon' para que ela seja encerrada automaticamente
    # se o programa principal (Streamlit) for finalizado.
    bot_thread = threading.Thread(target=start_bot_thread, name="BotThread", daemon=True)
    bot_thread.start()

    logging.info("Thread do bot iniciada. Aguardando 5 segundos para a inicialização...")
    time.sleep(5) # Dá um tempo para o bot começar a conectar antes de iniciar o painel

    # 2. Iniciar o painel Streamlit na thread principal
    logging.info("Iniciando o painel de controle Streamlit...")
    
    # Busca a porta fornecida pela Render, ou usa 8501 como padrão localmente
    port = os.environ.get("PORT", 8501)
    
    # Comando para rodar o Streamlit
    # Os flags --server.enableCORS e --server.enableXsrfProtection são recomendados
    # para evitar problemas de conexão quando rodando em serviços como a Render.
    streamlit_command = f"streamlit run panel.py --server.port {port} --server.enableCORS false --server.enableXsrfProtection false"
    
    # Executa o comando. Este comando bloqueará a execução aqui, mantendo o painel vivo.
    os.system(streamlit_command)