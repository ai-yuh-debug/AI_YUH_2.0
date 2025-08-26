# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Twitch Bot com Memória Generativa
# =========================================================================================
# FASE 2: Integração com a IA de Interação
#
# Autor: Seu Nome/Apelido
# Versão: 1.3.0
# Data: 26/08/2025
#
# Descrição: O bot agora se conecta ao módulo gemini_handler para gerar respostas
#            inteligentes. A lógica de ativação (!ask e menção) agora aciona a IA.
#
# =========================================================================================

import os
import socket
import time
from dotenv import load_dotenv

# Carrega as variáveis de ambiente PRIMEIRO
load_dotenv()

# AGORA importa o nosso módulo Gemini, que depende do .env
import gemini_handler

# --- Configurações Carregadas do .env ---
TTV_TOKEN = os.getenv('TTV_TOKEN')
BOT_NICK = os.getenv('BOT_NICK').lower()
TTV_CHANNEL = os.getenv('TTV_CHANNEL').lower()

# --- Constantes do Servidor IRC da Twitch ---
HOST = "irc.chat.twitch.tv"
PORT = 6667

# --- Função Principal de Execução ---

def main():
    """Função principal que conecta e executa o bot."""
    required_vars = ['TTV_TOKEN', 'BOT_NICK', 'TTV_CHANNEL', 'GEMINI_API_KEY']
    if any(not os.getenv(var) for var in required_vars):
        print("ERRO: Verifique se todas as variáveis estão definidas no .env: TTV_TOKEN, BOT_NICK, TTV_CHANNEL, GEMINI_API_KEY")
        return

    sock = socket.socket()
    try:
        print("Conectando ao servidor IRC da Twitch...")
        sock.connect((HOST, PORT))
        print("Conectado. Autenticando...")

        sock.send(f"PASS {TTV_TOKEN}\n".encode('utf-8'))
        sock.send(f"NICK {BOT_NICK}\n".encode('utf-8'))
        sock.send(f"JOIN #{TTV_CHANNEL}\n".encode('utf-8'))
        
        print(f"Autenticação enviada. Entrando no canal #{TTV_CHANNEL}")
        
        send_chat_message(sock, f"Olá! AI_Yuh (v1.3.0) está online e com um cérebro novo! Me chame com @{BOT_NICK} ou use !ask.")
        
        listen_for_messages(sock)

    except Exception as e:
        print(f"Ocorreu um erro fatal na conexão: {e}")
    finally:
        print("Fechando a conexão.")
        sock.close()

def send_chat_message(sock, message):
    """Envia uma mensagem formatada para o chat da Twitch."""
    try:
        sock.send(f"PRIVMSG #{TTV_CHANNEL} :{message}\n".encode('utf-8'))
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def listen_for_messages(sock):
    """Loop principal que lê e processa as mensagens do servidor IRC."""
    buffer = ""
    while True:
        try:
            buffer += sock.recv(2048).decode('utf-8', errors='ignore')
            messages = buffer.split('\r\n')
            buffer = messages.pop()

            for raw_message in messages:
                if not raw_message:
                    continue
                if raw_message.startswith('PING'):
                    sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
                    continue
                
                process_message(sock, raw_message)

        except ConnectionResetError:
            print("Conexão foi resetada pelo servidor. Lógica de reconexão necessária aqui.")
            break
        except Exception as e:
            print(f"Erro no loop de escuta: {e}")
            time.sleep(5)

def process_message(sock, raw_message):
    """Decodifica uma mensagem bruta do IRC e aciona a IA."""
    if "PRIVMSG" not in raw_message:
        return

    try:
        source, _, message_body = raw_message.partition('PRIVMSG')
        user_info = source.split('!')[0][1:]
        message_content = message_body.split(':', 1)[1].strip()

        # Ignora mensagens do próprio bot
        if user_info.lower() == BOT_NICK:
            return

        print(f"CHAT | {user_info}: {message_content}")

        msg_lower = message_content.lower()
        
        if msg_lower == "!ping":
            send_chat_message(sock, f"Pong, @{user_info}! Minha conexão com a IA está: {'ATIVA' if gemini_handler.GEMINI_ENABLED else 'INATIVA'}.")
            return

        activation_ask = "!ask "
        activation_mention = f"@{BOT_NICK} "
        
        question = ""
        is_activated = False

        if msg_lower.startswith(activation_ask):
            is_activated = True
            question = message_content[len(activation_ask):].strip()
        elif msg_lower.startswith(activation_mention):
            is_activated = True
            question = message_content[len(activation_mention):].strip()

        if is_activated:
            if question:
                # O bot foi ativado! Hora de chamar a IA.
                send_chat_message(sock, f"@{user_info}, pensando sobre '{question}'...")
                
                # Esta é a chamada para o nosso novo módulo!
                # Nota: Esta chamada é síncrona, o bot vai "pausar" enquanto espera a resposta.
                # Para um bot de chat, isso geralmente é aceitável.
                ai_response = gemini_handler.generate_response(question)
                
                # Envia a resposta da IA para o chat
                send_chat_message(sock, f"@{user_info} {ai_response}")
            else:
                response = f"Olá, @{user_info}! Você me chamou? Use !ask <sua pergunta> ou @{BOT_NICK} <sua pergunta>."
                send_chat_message(sock, response)

    except Exception:
        pass

if __name__ == "__main__":
    main()