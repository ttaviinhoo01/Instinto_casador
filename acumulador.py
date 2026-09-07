"""
INSTINTO CAÇADOR - Acumulador de Capital
================================================================
Gerencia capital acumulado e decide quando ativar trading.
Reinveste automaticamente e distribui recursos.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

class CapitalAccumulator:
    def __init__(self):
        self.balance = 0.0
        self.total_earned = 0.0
        self.total_withdrawn = 0.0
        self.threshold_trading = 10.0  # Ativa trading com $10
        self.threshold_withdrawal = 50.0  # Saque com $50
        
        # Distribuição de capital
        self.allocation = {
            'reinvest': 0.60,      # 60% reinveste em tarefas
            'save': 0.25,          # 25% reserva
            'trading': 0.10,       # 10% para trading
            'withdraw': 0.05       # 5% para saque
        }
        
        self.history = []

    async def add_earnings(self, amount: float, source: str) -> Dict[str, Any]:
        """Adiciona ganhos ao acumulador"""
        self.balance += amount
        self.total_earned += amount
        
        transaction = {
            'type': 'earning',
            'amount': amount,
            'source': source,
            'timestamp': time.time()
        }
        
        self.history.append(transaction)
        
        # Verifica se atingiu threshold de trading
        trading_ready = self.balance >= self.threshold_trading
        
        return {
            'balance': self.balance,
            'trading_ready': trading_ready,
            'transaction': transaction
        }

    def calculate_distribution(self) -> Dict[str, float]:
        """Calcula distribuição do capital"""
        distribution = {}
        
        for category, percentage in self.allocation.items():
            distribution[category] = self.balance * percentage
        
        return distribution

    async def auto_distribute(self) -> Dict[str, Any]:
        """Distribui capital automaticamente"""
        distribution = self.calculate_distribution()
        
        # Simula distribuição
        result = {
            'total_balance': self.balance,
            'distribution': distribution,
            'timestamp': time.time()
        }
        
        self.history.append({
            'type': 'distribution',
            'data': result
        })
        
        return result

    def get_trading_capital(self) -> float:
        """Retorna capital disponível para trading"""
        distribution = self.calculate_distribution()
        return distribution.get('trading', 0)

    def get_reinvest_capital(self) -> float:
        """Retorna capital para reinvestimento"""
        distribution = self.calculate_distribution()
        return distribution.get('reinvest', 0)

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do acumulador"""
        return {
            'balance': self.balance,
            'total_earned': self.total_earned,
            'total_withdrawn': self.total_withdrawn,
            'trading_capital': self.get_trading_capital(),
            'reinvest_capital': self.get_reinvest_capital(),
            'trading_threshold': self.threshold_trading,
            'trading_ready': self.balance >= self.threshold_trading,
            'progress_to_trading': min(self.balance / self.threshold_trading * 100, 100)
        }

    def save_state(self, filename: str = "data/accumulator.json"):
        """Salva estado do acumulador"""
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        data = {
            'balance': self.balance,
            'total_earned': self.total_earned,
            'total_withdrawn': self.total_withdrawn,
            'history': self.history[-100:],  # Últimos 100 eventos
            'last_updated': time.time()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def load_state(self, filename: str = "data/accumulator.json") -> bool:
        """Carrega estado do acumulador"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                self.balance = data.get('balance', 0)
                self.total_earned = data.get('total_earned', 0)
                self.total_withdrawn = data.get('total_withdrawn', 0)
                self.history = data.get('history', [])
                return True
        except FileNotFoundError:
            return False


if __name__ == "__main__":
    async def test():
        accumulator = CapitalAccumulator()
        
        print("💰 TESTANDO ACUMULADOR DE CAPITAL...")
        
        # Simula ganhos
        earnings = [
            (2.46, 'microtasks'),
            (1.50, 'faucets'),
            (3.75, 'surveys'),
            (0.89, 'airdrops')
        ]
        
        for amount, source in earnings:
            result = await accumulator.add_earnings(amount, source)
            print(f"  + ${amount:.2f} de {source} → Saldo: ${result['balance']:.2f}")
        
        # Distribui capital
        distribution = await accumulator.auto_distribute()
        
        print(f"\n📊 DISTRIBUIÇÃO:")
        for category, amount in distribution['distribution'].items():
            print(f"  - {category}: ${amount:.2f}")
        
        # Estatísticas
        stats = accumulator.get_statistics()
        
        print(f"\n📈 ESTATÍSTICAS:")
        print(f"  - Saldo total: ${stats['balance']:.2f}")
        print(f"  - Capital para trading: ${stats['trading_capital']:.2f}")
        print(f"  - Trading pronto: {'SIM' if stats['trading_ready'] else 'NÃO'}")
        print(f"  - Progresso: {stats['progress_to_trading']:.1f}%")
        
        # Salva estado
        accumulator.save_state()
        print(f"\n💾 Estado salvo em data/accumulator.json")

    asyncio.run(test())
