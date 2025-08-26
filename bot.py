# -*- coding: utf-8 -*-

# =========================================================================================
#                   AI_YUH - Twitch Bot com Memória Generativa
# =========================================================================================
# FASE 1: O Esqueleto do Bot - Conexão e Comunicação Básica
#
# Autor: Seu Nome/Apelido
# Versão: 1.0.0
# Data: 26/08/2025
#
# Descrição: Este é o script principal para o bot da Twitch, AI_Yuh.
#            Nesta primeira fase, o foco é estabelecer a conexão com a Twitch,
#            carregar configurações de forma segura e responder a um comando básico
#            para verificar a funcionalidade. Este código é a base para a
#            implantação futura no Render.
#
# =========================================================================================

import os
from twitchio.ext import commands
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
# Isso mantém suas credenciais seguras e fora do código-fonte.
# O Render usará suas próprias variáveis de ambiente, mas este método é perfeito para desenvolvimento local.
load_dotenv()

class Bot(commands.Bot):

    def __init__(self):
        # Inicializa a classe do Bot com as credenciais e informações do canal
        # Essas informações são carregadas do arquivo .env
        super().__init__(
            token=os.getenv('TTV_TOKEN'),
            client_id=os.getenv('TTV_CLIENT_ID'),
            nick=os.getenv('BOT_NICK'),
            prefix=os.getenv('BOT_PREFIX'),
            initial_channels=[os.getenv('TTV_CHANNEL')]
        )
        print("Inicializando o bot...")

    async def event_ready(self):
        """
        Esta função é chamada quando o bot se conecta com sucesso à Twitch.
        É um ótimo lugar para imprimir mensagens de status ou enviar uma
        mensagem de "olá" para o canal.
        """
        # Acessa o canal a partir da lista de canais conectados
        channel_name = os.getenv('TTV_CHANNEL')
        print(f'Bot conectado como {self.nick}')
        print(f'Entrando no canal: {channel_name}')
        
        # Obtém o objeto do canal para enviar mensagens
        channel = self.get_channel(channel_name)
        if channel:
            await channel.send(f"/me Olá! AI_Yuh está online e pronta para interagir.")
        else:
            print(f"Erro: Não foi possível encontrar o canal {channel_name}.")

    async def event_message(self, message):
        """
        Esta função é chamada para cada mensagem enviada no chat.
        É aqui que o bot "escuta" tudo.
        """
        # Ignora mensagens enviadas pelo próprio bot para evitar loops infinitos
        if message.echo:
            return

        # Imprime a mensagem no console para fins de depuração
        print(f"({message.timestamp.strftime('%H:%M:%S')}) {message.author.name}: {message.content}")

        # Processa os comandos definidos com @commands.command()
        await self.handle_commands(message)

    # =========================================================================================
    #                                 COMANDOS BÁSICOS
    # =========================================================================================

    @commands.command(name='ping')
    async def ping_command(self, ctx: commands.Context):
        """
        Comando de teste simples.
        Quando um usuário digita !ping, o bot responde com "Pong!".
        Isso serve para verificar se o bot está online e respondendo a comandos.
        """
        await ctx.send(f'Pong, @{ctx.author.name}!')

# =========================================================================================
#                               PONTO DE ENTRADA DO SCRIPT
# =========================================================================================

def main():
    """Função principal para rodar o bot."""
    # Validação das variáveis de ambiente essenciais
    required_vars = ['TTV_TOKEN', 'TTV_CLIENT_ID', 'BOT_NICK', 'TTV_CHANNEL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Erro: As seguintes variáveis de ambiente estão faltando no seu arquivo .env: {', '.join(missing_vars)}")
        return

    # Cria uma instância da nossa classe Bot
    bot = Bot()
    # Inicia a execução do bot (este método bloqueia a execução até o bot parar)
    bot.run()

if __name__ == "__main__":
    main()