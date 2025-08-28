# shared_state.py
from collections import deque

# Criamos uma deque (fila) com um tamanho máximo de 100 linhas.
# Isso evita que a lista de logs cresça indefinidamente e consuma toda a memória.
# Quando o limite é atingido, as mensagens mais antigas são descartadas automaticamente.
log_queue = deque(maxlen=100)