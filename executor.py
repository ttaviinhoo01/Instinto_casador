"""
INSTINTO - Executor Blindado (CCXT Async + 5 Travas Críticas)
================================================================
Travas:
1. Reconciliation Loop: Exchange é a verdade no boot
2. Ordens IOC/Limit apenas (Market só no pânico)
3. Asyncio Lock no emergency_stop (checagem ms antes do HTTP)
4. Dead Man's Switch: bloqueia novas entradas se feed > 5s
5. NAV Sync horário + Panic/Flattening completo
"""

import asyncio
import ccxt.async_support as ccxt
import time
from typing import Dict, Any, Optional, List
from db import Database

class Executor:
    def __init__(self, db: Database, exchange_id: str = "binance", api_key: str = "", api_secret: str = ""):
        self.db = db
        self.exchange = getattr(ccxt, exchange_id)({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        self.emergency_stop = False
        self._emergency_lock = asyncio.Lock()
        self._dead_man_switch = False
        self._last_feed_ts = time.time()
        self._nav_sync_interval = 3600  # 1 hora
        self._last_nav_sync = 0

    async def check_emergency_stop(self) -> bool:
        """Trava 3: Checagem atômica do emergency_stop"""
        async with self._emergency_lock:
            return self.emergency_stop

    async def set_emergency_stop(self, value: bool) -> None:
        """Ativa/desativa emergency_stop de forma segura"""
        async with self._emergency_lock:
            self.emergency_stop = value
            await self.db.append_event(
                source="executor",
                event_type="EMERGENCY_STOP" if value else "EMERGENCY_REARM",
                payload={"state": value, "ts": time.time()}
            )

    async def reconciliation_loop(self) -> Dict[str, Any]:
        """Trava 1: Sincroniza posições com a Exchange no boot"""
        try:
            positions = await self.exchange.fetch_positions()
            for pos in positions:
                if float(pos['contracts']) != 0:
                    await self.db.upsert_position(
                        symbol=pos['symbol'],
                        side=pos['side'],
                        amount=float(pos['contracts']),
                        entry_price=float(pos['entryPrice']),
                        current_price=float(pos['markPrice']),
                        exchange_ts=time.time()
                    )
                else:
                    await self.db.remove_position(pos['symbol'])
            
            await self.db.append_event(
                source="executor",
                event_type="RECONCILIATION_COMPLETE",
                payload={"positions_synced": len(positions)}
            )
            return {"success": True, "positions": len(positions)}
        except Exception as e:
            await self.db.append_event(
                source="executor",
                event_type="RECONCILIATION_FAILED",
                payload={"error": str(e)}
            )
            return {"success": False, "error": str(e)}

    async def place_order_ioc(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        tolerance: float = 0.001  # 0.1% de tolerância
    ) -> Dict[str, Any]:
        """
        Trava 2: Ordem IOC/Limit com tolerância rígida de preço.
        Market é PROIBIDO aqui.
        """
        if await self.check_emergency_stop():
            return {"success": False, "error": "EMERGENCY_STOP_ACTIVE"}

        if self._dead_man_switch:
            return {"success": False, "error": "DEAD_MAN_SWITCH_TRIGGERED"}

        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = float(ticker['last'])
            
            # Valida tolerância de preço
            price_diff = abs(current_price - price) / current_price
            if price_diff > tolerance:
                await self.db.append_event(
                    source="executor",
                    event_type="ORDER_REJECTED_PRICE_TOLERANCE",
                    payload={
                        "symbol": symbol,
                        "current_price": current_price,
                        "order_price": price,
                        "diff": price_diff,
                        "tolerance": tolerance
                    }
                )
                return {"success": False, "error": "PRICE_TOLERANCE_EXCEEDED"}

            order = await self.exchange.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=amount,
                price=price,
                params={'timeInForce': 'IOC'}
            )

            await self.db.append_event(
                source="executor",
                event_type="ORDER_PLACED",
                payload={
                    "order_id": order['id'],
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "type": "IOC_LIMIT"
                }
            )
            return {"success": True, "order": order}

        except Exception as e:
            await self.db.append_event(
                source="executor",
                event_type="ORDER_FAILED",
                payload={"symbol": symbol, "error": str(e)}
            )
            return {"success": False, "error": str(e)}

    async def update_price_feed(self, symbol: str) -> None:
        """Atualiza timestamp do feed (Dead Man's Switch)"""
        self._last_feed_ts = time.time()
        self._dead_man_switch = False
        await self.db.update_last_price_feed_ts()

    async def check_dead_man_switch(self) -> bool:
        """Trava 4: Verifica se feed está atrasado > 5s"""
        now = time.time()
        if now - self._last_feed_ts > 5.0:
            self._dead_man_switch = True
            await self.db.append_event(
                source="executor",
                event_type="DEAD_MAN_SWITCH_TRIGGERED",
                payload={"last_feed_ts": self._last_feed_ts, "delay": now - self._last_feed_ts}
            )
            return True
        return False

    async def nav_sync(self) -> Dict[str, Any]:
        """Trava 5: Sincroniza NAV com a Exchange"""
        try:
            balance = await self.exchange.fetch_balance()
            total_equity = float(balance['total'].get('USDT', 0))
            available = float(balance['free'].get('USDT', 0))
            used = float(balance['used'].get('USDT', 0))
            
            # Calcula PnL não realizado
            positions = await self.db.get_positions()
            unrealized_pnl = 0
            for pos in positions:
                ticker = await self.exchange.fetch_ticker(pos['symbol'])
                current_price = float(ticker['last'])
                if pos['side'] == 'long':
                    pnl = (current_price - pos['entry_price']) * pos['amount']
                else:
                    pnl = (pos['entry_price'] - current_price) * pos['amount']
                unrealized_pnl += pnl

            await self.db.update_nav_state(
                total_equity=total_equity,
                available_balance=available,
                used_margin=used,
                unrealized_pnl=unrealized_pnl
            )
            
            await self.db.append_event(
                source="executor",
                event_type="ADJUST_NAV",
                payload={
                    "total_equity": total_equity,
                    "available": available,
                    "used": used,
                    "unrealized_pnl": unrealized_pnl
                }
            )
            
            self._last_nav_sync = time.time()
            return {"success": True, "total_equity": total_equity}

        except Exception as e:
            await self.db.append_event(
                source="executor",
                event_type="NAV_SYNC_FAILED",
                payload={"error": str(e)}
            )
            return {"success": False, "error": str(e)}

    async def panic_flatten(self) -> Dict[str, Any]:
        """Pânico: Cancela ordens abertas e zera posições via market"""
        try:
            await self.set_emergency_stop(True)
            
            # Cancela todas as ordens abertas
            open_orders = await self.exchange.fetch_open_orders()
            for order in open_orders:
                await self.exchange.cancel_order(order['id'], order['symbol'])
            
            # Zera posições via market reduceOnly
            positions = await self.db.get_positions()
            for pos in positions:
                if pos['amount'] > 0:
                    side = 'sell' if pos['side'] == 'long' else 'buy'
                    await self.exchange.create_order(
                        symbol=pos['symbol'],
                        type='market',
                        side=side,
                        amount=pos['amount'],
                        params={'reduceOnly': True}
                    )
                    await self.db.remove_position(pos['symbol'])
            
            await self.db.append_event(
                source="executor",
                event_type="PANIC_FLATTEN_COMPLETE",
                payload={"positions_closed": len(positions)}
            )
            return {"success": True, "positions_closed": len(positions)}

        except Exception as e:
            await self.db.append_event(
                source="executor",
                event_type="PANIC_FLATTEN_FAILED",
                payload={"error": str(e)}
            )
            return {"success": False, "error": str(e)}

    async def close(self) -> None:
        """Fecha conexão com a Exchange"""
        await self.exchange.close()


if __name__ == "__main__":
    async def test():
        db = Database("data/test_executor.db")
        await db.initialize()
        
        # Testa sem credenciais reais (apenas estrutura)
        executor = Executor(db)
        
        # Testa emergency_stop
        await executor.set_emergency_stop(True)
        assert await executor.check_emergency_stop() == True
        
        # Testa dead man switch
        executor._last_feed_ts = time.time() - 10
        assert await executor.check_dead_man_switch() == True
        
        print("Teste do Executor concluído (estrutura validada).")
        await db.close()

    asyncio.run(test())
