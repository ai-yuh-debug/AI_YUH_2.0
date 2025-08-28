# api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import database_handler

# Cria a instância da aplicação FastAPI
app = FastAPI()

# Configura o CORS (Cross-Origin Resource Sharing)
# Isso é importante para permitir que o JavaScript do painel
# se comunique com a API, mesmo que eles rodem em portas diferentes localmente.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas as origens
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos os cabeçalhos
)

@app.get("/api/live_data")
async def get_live_data():
    """
    Este é o endpoint da API. Ele busca todos os dados necessários para o painel
    e os retorna em um único objeto JSON.
    """
    # Busca os logs mais recentes do banco de dados
    log_entries = database_handler.get_live_logs(limit=150)
    
    # Busca os status
    status = database_handler.get_bot_status()
    debug_status = database_handler.get_bot_debug_status()
    
    # Retorna um dicionário. O FastAPI o converterá automaticamente para JSON.
    return {
        "status": status,
        "debug_status": debug_status,
        "logs": log_entries
    }