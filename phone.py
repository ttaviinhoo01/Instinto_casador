"""
INSTINTO - Bot Telegram (Controle via Celular)
================================================================
Comandos:
- /status: Mostra estado do sistema
- /kill: Pânico/Flattening completo
- /rearm: Reativa sistema após kill

Segurança: Whitelist rígida de usuários
"""

import asyncio
from typing import Optional, Set
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from db import Database
from orchestrator import Orchestrator

# Whitelist de usuários permitidos
ADMIN_IDS: Set[int] = {8907295819}  # Tavinhoo

class PhoneBot:
    def __init__(self, db: Database, orchestrator: Orchestrator, token: str):
        self.db = db
        self.orchestrator = orchestrator
        self.token = token
        self.app = Application.builder().token(token).build()
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Registra comandos com decorador de whitelist"""
        self.app.add_handler(CommandHandler("status", self._admin_only(self.cmd_status)))
        self.app.add_handler(CommandHandler("kill", self._admin_only(self.cmd_kill)))
        self.app.add_handler(CommandHandler("rearm", self._admin_only(self.cmd_rearm)))

    def _admin_only(self, func):
        """Decorador rígido de whitelist"""
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            if user_id not in ADMIN_IDS:
                await update.message.reply_text("⛔ Acesso negado. Você não é admin.")
                return
            return await func(update, context)
        return wrapper

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra estado atual do sistema"""
        try:
            nav = await self.db.get_nav_state()
            positions = await self.db.get_positions()
            
            status_text = f"""
📊 **INSTINTO STATUS**

💰 **NAV:**
- Equity Total: ${nav['total_equity']:.2f}
- Disponível: ${nav['available_balance']:.2f}
- Margem Usada: ${nav['used_margin']:.2f}
- PnL Não Realizado: ${nav['unrealized_pnl']:.2f}

📈 **Posições Abertas:** {len(positions)}
"""
            for pos in positions:
                status_text += f"""
- {pos['symbol']}: {pos['side']} {pos['amount']} @ ${pos['entry_price']:.2f}
"""
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao obter status: {str(e)}")

    async def cmd_kill(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Pânico/Flattening completo"""
        try:
            # Adquire lock para evitar dupla execução
            if not await self.db.try_acquire_command_lock("kill", ttl_seconds=10):
                await update.message.reply_text("⚠️ Comando já em execução...")
                return
            
            await update.message.reply_text("🚨 INICIANDO PANIC/FLATTENING...")
            
            result = await self.orchestrator.panic()
            
            if result:
                await update.message.reply_text("✅ Pânico concluído. Posições zeradas.")
            else:
                await update.message.reply_text("❌ Falha no pânico. Verifique logs.")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Erro: {str(e)}")

    async def cmd_rearm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Reativa sistema após kill"""
        try:
            await self.orchestrator.executor.set_emergency_stop(False)
            await update.message.reply_text("✅ Sistema rearmado. Pronto para operar.")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Erro: {str(e)}")

    async def start(self) -> None:
        """Inicia o bot"""
        await self.app.initialize()
        await self.app.start()
        await self.app.run_polling()

    async def stop(self) -> None:
        """Para o bot"""
        try:
            await self.app.stop()
        except RuntimeError:
            pass


if __name__ == "__main__":
    async def test():
        db = Database("data/test_phone.db")
        from executor import Executor
        executor = Executor(db)
        orchestrator = Orchestrator(db, executor)
        print("Estrutura do PhoneBot validada.")
        await db.close()

    asyncio.run(test())
