# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Twitch Bot com Memória Generativa
# =========================================================================================
# FASE 1 (Revisada): Conexão Direta com IRC (Apenas OAuth)
#
# Autor: Seu Nome/Apelido
# Versão: 1.1.0
# Data: 26/08/2025
#
# Descrição: Esta versão do bot atende ao requisito de usar APENAS o token OAuth
#            para autenticação, sem a necessidade de um Client ID. Para isso,
#            abandonamos a biblioteca twitchio e usamos a biblioteca nativa 'socket'
#            para nos comunicarmos diretamente com o servidor IRC da Twitch.
#
# =========================================================================================

import os
import socket
import time
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações Carregadas do .env ---
TTV_TOKEN = os.getenv('TTV_TOKEN')
BOT_NICK = os.getenv('BOT_NICK')
TTV_CHANNEL = os.getenv('TTV_CHANNEL')
BOT_PREFIX = os.getenv('BOT_PREFIX')

# --- Constantes do Servidor IRC da Twitch ---
HOST = "irc.chat.twitch.tv"
PORT = 6667

# --- Função Principal de Execução ---

def main():
    """Função principal que conecta e executa o bot."""
    # Validação das variáveis de ambiente essenciais
    required_vars = ['TTV_TOKEN', 'BOT_NICK', 'TTV_CHANNEL']
    if any(not var for var in [TTV_TOKEN, BOT_NICK, TTV_CHANNEL]):
        print("Erro: Verifique se TTV_TOKEN, BOT_NICK, e TTV_CHANNEL estão definidos no arquivo .env")
        return

    # Criação e configuração do socket
    sock = socket.socket()
    try:
        print("Conectando ao servidor IRC da Twitch...")
        sock.connect((HOST, PORT))
        print("Conectado. Autenticando...")

        # Envio de dados de autenticação (APENAS Nick e OAuth)
        sock.send(f"PASS {TTV_TOKEN}\n".encode('utf-8'))
        sock.send(f"NICK {BOT_NICK}\n".encode('utf-8'))
        sock.send(f"JOIN #{TTV_CHANNEL}\n".encode('utf-8'))
        
        print(f"Autenticação enviada. Entrando no canal #{TTV_CHANNEL}")
        
        # Envia uma mensagem de "Olá" para o chat
        send_chat_message(sock, f"Olá! AI_Yuh (v1.1.0) está online.")
        
        # Loop principal para escutar o chat
        listen_for_messages(sock)

    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        print("Fechando a conexão.")
        sock.close()

def send_chat_message(sock, message):
    """Envia uma mensagem formatada para o chat da Twitch."""
    try:
        print(f"ENVIANDO: {message}")
        sock.send(f"PRIVMSG #{TTV_CHANNEL} :{message}\n".encode('utf-8'))
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def listen_for_messages(sock):
    """Loop principal que lê e processa as mensagens do servidor IRC."""
    while True:
        try:
            # Lê dados do buffer do socket
            resp = sock.recv(2048).decode('utf-8')

            # Se a resposta estiver vazia, a conexão pode ter caído
            if not resp:
                print("Conexão perdida. Tentando reconectar...")
                # Lógica de reconexão pode ser adicionada aqui
                break

            # A Twitch exige que respondamos a PINGs para manter a conexão ativa
            if resp.startswith('PING'):
                print("PING recebido, enviando PONG...")
                sock.send("PONG\n".encode('utf-8'))
                continue
            
            # Se não for um PING, processa como uma mensagem normal
            process_message(sock, resp)

        except ConnectionResetError:
            print("Conexão foi resetada pelo servidor. Reconectando...")
            # Lógica de reconexão
            break
        except Exception as e:
            print(f"Erro no loop de escuta: {e}")
            time.sleep(5) # Espera um pouco antes de continuar

def process_message(sock, raw_message):
    """Decodifica uma mensagem bruta do IRC e aciona comandos."""
    # Imprime a mensagem bruta para depuração
    print(f"RECEBIDO: {raw_message.strip()}")

    # Estrutura de uma mensagem de chat no IRC da Twitch:
    # :<user>!<user>@<user>.tmi.twitch.tv PRIVMSG #<channel> :<message>
    if "PRIVMSG" in raw_message:
        parts = raw_message.split("PRIVMSG")
        
        # Extrai o nome de usuário
        user_info = parts[0].split('!')[0][1:]
        
        # Extrai o conteúdo da mensagem
        message_content = parts[1].split(':', 1)[1].strip()

        print(f"CHAT | {user_info}: {message_content}")

        # --- Lógica de Comandos ---
        if message_content.startswith(BOT_PREFIX):
            command_parts = message_content[len(BOT_PREFIX):].split()
            command_name = command_parts[0].lower()

            if command_name == "ping":
                send_chat_message(sock, f"Pong, @{user_info}!")

# =========================================================================================
#                               PONTO DE ENTRADA DO SCRIPT
# =========================================================================================
if __name__ == "__main__":
    main()