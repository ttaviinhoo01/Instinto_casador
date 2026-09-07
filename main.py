"""
INSTINTO - Ponto de Entrada Principal
================================================================
Inicializa todos os módulos e gerencia Graceful Shutdown.
"""

import asyncio
import signal
import sys
import time
from db import Database
from executor import Executor
from orchestrator import Orchestrator
from phone import PhoneBot

# Configurações
TELEGRAM_TOKEN = ""  # Desativado no Termux - será ativado no VPS
EXCHANGE_API_KEY = ""  # ← COLOQUE SUA API KEY AQUI
EXCHANGE_API_SECRET = ""  # ← COLOQUE SEU API SECRET AQUI

class InstintoApp:
    def __init__(self):
        self.db = Database()
        self.executor = Executor(
            self.db,
            exchange_id="binance",
            api_key=EXCHANGE_API_KEY,
            api_secret=EXCHANGE_API_SECRET
        )
        self.orchestrator = Orchestrator(self.db, self.executor)
        self.phone_bot = None
        if TELEGRAM_TOKEN:
            self.phone_bot = PhoneBot(self.db, self.orchestrator, TELEGRAM_TOKEN)
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Inicia todos os componentes"""
        print("🚀 INSTINTO INICIANDO...")
        
        # Inicializa DB
        await self.db.initialize()
        print("✅ Banco de dados inicializado")
        
        # Inicia bot do Telegram (se token configurado)
        if self.phone_bot:
            asyncio.create_task(self.phone_bot.start())
            print("✅ Bot Telegram iniciado")
        else:
            print("⚠️ Bot Telegram desativado (sem token)")
        
        # Inicia orquestrador
        await self.orchestrator.start()
        
        # Aguarda sinal de shutdown
        await self._shutdown_event.wait()

    async def shutdown(self, signal_name: str) -> None:
        """Graceful Shutdown"""
        print(f"\n⚠️ Recebido {signal_name}. Iniciando shutdown limpo...")
        
        # Para bot
        if self.phone_bot:
            try:
                await self.phone_bot.stop()
                print("✅ Bot Telegram parado")
            except Exception as e:
                print(f"⚠️ Erro ao parar bot: {e}")
        
        # Para orquestrador
        await self.orchestrator.stop()
        print("✅ Orquestrador parado")
        
        # Fecha DB
        await self.db.close()
        print("✅ Banco de dados fechado")
        
        self._shutdown_event.set()
        print("🏁 Shutdown completo. Até logo!")

    def setup_signal_handlers(self) -> None:
        """Configura handlers para SIGINT e SIGTERM"""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self.shutdown(s.name))
                )
            except NotImplementedError:
                pass

async def main():
    app = InstintoApp()
    app.setup_signal_handlers()
    
    try:
        await app.start()
    except KeyboardInterrupt:
        await app.shutdown("SIGINT")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        await app.shutdown("ERROR")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
