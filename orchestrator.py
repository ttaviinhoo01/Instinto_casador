"""
INSTINTO - Orquestrador Central
================================================================
Responsabilidades:
1. Boot seguro (inicializa DB, reconcilia com Exchange)
2. Loop principal de verificação
3. NAV Sync horário
4. Comando de Pânico/Flatten
"""

import asyncio
import time
from typing import Optional
from db import Database
from executor import Executor

class Orchestrator:
    def __init__(self, db: Database, executor: Executor):
        self.db = db
        self.executor = executor
        self._running = False
        self._nav_sync_interval = 3600  # 1 hora
        self._last_nav_sync = 0
        self._check_interval = 1.0  # verifica a cada 1 segundo

    async def boot_secure(self) -> bool:
        """
        Boot seguro: inicializa DB, reconcilia com Exchange.
        Retorna True se boot OK.
        """
        try:
            await self.db.initialize()
            await self.db.append_event(
                source="orchestrator",
                event_type="BOOT_START",
                payload={"ts": time.time()}
            )
            
            # Reconciliação com Exchange (fonte da verdade)
            result = await self.executor.reconciliation_loop()
            
            if result.get("success"):
                await self.db.append_event(
                    source="orchestrator",
                    event_type="BOOT_COMPLETE",
                    payload={"reconciliation": result}
                )
                return True
            else:
                await self.db.append_event(
                    source="orchestrator",
                    event_type="BOOT_FAILED",
                    payload={"error": result.get("error")}
                )
                return False
                
        except Exception as e:
            await self.db.append_event(
                source="orchestrator",
                event_type="BOOT_ERROR",
                payload={"error": str(e)}
            )
            return False

    async def nav_sync_loop(self) -> None:
        """Loop de sincronização de NAV (a cada 1 hora)"""
        while self._running:
            now = time.time()
            if now - self._last_nav_sync >= self._nav_sync_interval:
                await self.executor.nav_sync()
                self._last_nav_sync = now
            await asyncio.sleep(60)  # verifica a cada minuto

    async def check_loop(self) -> None:
        """Loop principal de verificação"""
        while self._running:
            # Verifica Dead Man's Switch
            await self.executor.check_dead_man_switch()
            
            # Verifica emergency stop
            if await self.executor.check_emergency_stop():
                await self.db.append_event(
                    source="orchestrator",
                    event_type="EMERGENCY_STOP_ACTIVE",
                    payload={"ts": time.time()}
                )
            
            await asyncio.sleep(self._check_interval)

    async def panic(self) -> bool:
        """Comando de Pânico: Flattening completo"""
        await self.db.append_event(
            source="orchestrator",
            event_type="PANIC_INITIATED",
            payload={"ts": time.time()}
        )
        result = await self.executor.panic_flatten()
        if result.get("success"):
            await self.db.append_event(
                source="orchestrator",
                event_type="PANIC_COMPLETE",
                payload=result
            )
            return True
        return False

    async def start(self) -> None:
        """Inicia o orquestrador"""
        if self._running:
            return
        self._running = True
        
        # Boot seguro
        if not await self.boot_secure():
            await self.db.append_event(
                source="orchestrator",
                event_type="FATAL_BOOT_FAILED",
                payload={"ts": time.time()}
            )
            self._running = False
            return
        
        # Inicia loops
        await asyncio.gather(
            self.nav_sync_loop(),
            self.check_loop()
        )

    async def stop(self) -> None:
        """Para o orquestrador"""
        self._running = False
        await self.db.close()
        await self.executor.close()


if __name__ == "__main__":
    async def test():
        db = Database("data/test_orchestrator.db")
        executor = Executor(db)
        orchestrator = Orchestrator(db, executor)
        
        # Testa boot (vai falhar sem credenciais reais, mas estrutura OK)
        result = await orchestrator.boot_secure()
        print(f"Boot result: {result}")
        
        await db.close()
        print("Teste do Orquestrador concluído (estrutura validada).")

    asyncio.run(test())
