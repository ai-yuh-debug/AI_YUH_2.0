================================================================================
          DOCUMENTAÇÃO OFICIAL - AI_YUH BOT - VERSÃO 3.5.2-STABLE
================================================================================

Este documento descreve a arquitetura, funcionalidades, comandos e fluxo de
dados do AI_Yuh Bot, um assistente de IA para a Twitch com memória generativa
e sistema de controle de estado.

--------------------------------------------------------------------------------
1. VISÃO GERAL DA ARQUITETURA
--------------------------------------------------------------------------------

O projeto é dividido em múltiplos componentes que rodam simultaneamente em um
único serviço na nuvem (Render), orquestrados por um script principal.

- app.py (O Orquestrador):
  Ponto de entrada da aplicação. Inicia o Bot e o Painel em threads separadas,
  permitindo que rodem em paralelo no mesmo processo.

- main_bot.py (O Bot):
  O coração da aplicação. Conecta-se ao chat da Twitch via IRC e gerencia o
  ciclo de vida, a leitura de mensagens e o agendamento de tarefas.

- panel.py (O Painel de Controle):
  Uma aplicação web criada com Streamlit que serve como interface para monitorar
  e gerenciar o bot. Exibe logs, status e permite a edição de configurações.

- gemini_handler.py (O Cérebro de IA):
  Gerencia a interação com a API do Google Gemini. Contém a lógica para duas
  instâncias de IA distintas.

- database_handler.py (A Memória Persistente):
  Gerencia toda a comunicação com o banco de dados Supabase, onde todas as
  configurações, memórias, logs e dados de usuários são armazenados.

- requirements.txt:
  Lista todas as dependências Python necessárias para o projeto.

--------------------------------------------------------------------------------
2. SISTEMA DE IA DUPLO
--------------------------------------------------------------------------------

O bot utiliza dois modelos de IA para tarefas distintas, garantindo eficiência
e qualidade nas respostas. Os modelos são configuráveis através do painel.

- IA de Interação (Padrão: gemini-1.5-flash-latest):
  Responsável por conversar com os usuários em tempo real. É otimizada para
  velocidade e diálogo. Ela LÊ as memórias do banco de dados para obter
  contexto antes de responder.

- IA Arquivista (Padrão: gemini-1.5-flash-latest):
  Responsável por criar, organizar e gerenciar a memória hierárquica. Ela
  LÊ grandes blocos de texto (logs de chat, resumos antigos) e CRIA novos
  resumos que são salvos no banco de dados. Ela nunca fala com os usuários.

--------------------------------------------------------------------------------
3. SISTEMA DE MEMÓRIA GENERATIVA
--------------------------------------------------------------------------------

A memória do bot é dividida em múltiplos níveis para simular a capacidade de
lembrar de eventos a curto, médio e longo prazo.

- Nível 0: Memória de Curto Prazo (RAM)
  - O histórico de conversa recente com cada usuário individualmente.
  - É armazenado em memória (dicionário `short_term_memory`) e descartado
    após 5 minutos de inatividade do usuário, sendo antes sumarizado para a
    Memória de Longo Prazo.

- Nível 1: Memória de Transferência (Chat Global)
  - A cada 15 minutos ou 40 mensagens (o que vier primeiro), o chat é
    sumarizado pela IA Arquivista e salvo no banco de dados como uma memória
    de nível "transfer".

- Nível 2: Memória Diária
  - Uma vez por dia (às 00:15 UTC-3), todas as memórias "transfer" do dia
    anterior são lidas e sumarizadas em uma única memória "daily". As
    memórias "transfer" são então apagadas.

- Nível 3: Memória Semanal
  - Toda segunda-feira (às 01:00 UTC-3), se existirem 7 memórias diárias,
    elas são sumarizadas em uma memória "weekly". As memórias diárias
    são então apagadas.

- Nível 4: Memória Mensal
  - O sistema checa diariamente (às 01:30 UTC-3) se já existem 4 memórias
    semanais. Se sim, elas são sumarizadas em uma memória "monthly" e apagadas.

- Nível 5: Memória Anual
  - O sistema checa diariamente (às 02:00 UTC-3) se já existem 12 memórias
    mensais. Se sim, elas são sumarizadas em uma memória "yearly" e apagadas.

- Nível 6: Memória Secular
  - O sistema checa diariamente (às 02:30 UTC-3) se já existem 100 memórias
    anuais. Se sim, elas são sumarizadas em uma memória "century" e apagadas.

- Memória de Longo Prazo (Pessoal):
  - Resumos de conversas individuais com usuários, criados a partir da
    memória de curto prazo.

- Lorebook:
  - Uma base de conhecimento de fatos importantes, ensinados manualmente
    através do comando `!learn`. É usado como fonte primária de contexto.

--------------------------------------------------------------------------------
4. SISTEMA "AWAKER" (ESTADOS DO BOT)
--------------------------------------------------------------------------------

Para otimizar o uso de recursos, o bot opera em dois estados distintos.

- Estado 'ASLEEP' (Adormecido):
  - O bot está conectado ao chat, mas em modo de baixo consumo.
  - Ele não processa memórias, não loga o chat e não responde a comandos,
    exceto os de ativação.

- Estado 'AWAKE' (Acordado):
  - O bot está em plena funcionalidade. Ele processa todas as mensagens,
    gera memórias, responde à IA e executa todas as suas tarefas.

--------------------------------------------------------------------------------
5. COMANDOS DO BOT
--------------------------------------------------------------------------------

Os comandos são a principal forma de interagir com as funcionalidades do bot.

--- COMANDOS PÚBLICOS ---

!ask <pergunta>
  - Ativa a IA de Interação para responder à pergunta.
  - Exemplo: `!ask qual a capital do Brasil?`

@ai_yuh <pergunta>
  - Alternativa ao !ask, funciona mencionando o nome do bot.
  - Exemplo: `@ai_yuh me conte uma piada`

--- COMANDOS DE MESTRE (MASTER) ---
(Apenas usuários com permissão 'master' podem usar)

!learn <fato>
  - Adiciona uma nova entrada ao Lorebook. O fato deve ser claro e conciso.
  - Exemplo: `!learn A mascote do canal é uma capivara chamada Cleiton.`

!awake
  - Força o bot a sair do estado 'ASLEEP' e entrar no estado 'AWAKE'.
  - Útil caso o gatilho automático de início de live falhe.

!sleep
  - Força o bot a sair do estado 'AWAKE' e entrar no estado 'ASLEEP'.
  - Útil para encerrar a atividade do bot ao final da live.

--------------------------------------------------------------------------------
6. GATILHOS AUTOMÁTICOS
--------------------------------------------------------------------------------

- Despertar Automático (Live On):
  - O bot sairá do estado 'ASLEEP' para 'AWAKE' automaticamente quando o
    bot StreamElements postar a mensagem de início de live configurada
    (contendo "a mãe ta oooooooooon!").

- Filtragem de Bots:
  - Quando no estado 'AWAKE', o bot irá ignorar automaticamente mensagens
    de usuários marcados com a permissão 'bot' no painel, evitando que
    outros bots poluam a memória generativa.

--------------------------------------------------------------------------------
7. PAINEL DE CONTROLE
--------------------------------------------------------------------------------

Acessível pela URL da aplicação na Render, o painel permite:

- Monitorar o status do bot (Online/Offline, AWAKE/ASLEEP).
- Ver a "Última Ação da IA", um log de depuração mostrando a última pergunta
  e os contextos usados.
- Visualizar em tempo real (com refresh automático) três colunas de logs:
  1. Logs do Sistema: Conexões, erros, status do agendador.
  2. Pensamento da IA: O que a IA recebeu, o que ela respondeu, e se ela
     solicitou uma busca na web.
  3. Chat Processado: Um espelho das mensagens do chat que o bot está lendo.
- Gerenciar Configurações: Editar o prompt de personalidade, os modelos de IA
  e os parâmetros de geração.
- Gerenciar Usuários: Adicionar, editar e remover usuários, definindo suas
  permissões ('master', 'normal', 'blacklist', 'bot').
- Gerenciar Lorebook: Adicionar e remover fatos do Lorebook.
- Visualizar Memórias: Ver o conteúdo das tabelas de memória pessoal e global.

============================= FIM DA DOCUMENTAÇÃO =============================