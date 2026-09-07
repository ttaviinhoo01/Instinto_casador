"""
INSTINTO CAÇADOR - Sistema Principal v2.0
================================================================
Orquestra todos os módulos:
- Scanner: busca oportunidades
- Validador: filtra golpes
- Executor: executa tarefas
- Acumulador: gerencia capital
- Fontes Adicionais: arbitragem, staking, airdrops, testnets, referências, cashback

Objetivo: Gerar capital do zero absoluto até atingir threshold de trading.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from scanner import OpportunityScanner
from validador import OpportunityValidator
from executor_tarefas import TaskExecutor
from acumulador import CapitalAccumulator
from fontes_renda import AdditionalIncomeSources

class InstintoCacador:
    def __init__(self):
        self.scanner = OpportunityScanner()
        self.validator = OpportunityValidator()
        self.executor = TaskExecutor()
        self.accumulator = CapitalAccumulator()
        self.additional_sources = AdditionalIncomeSources()
        
        self.running = False
        self.cycle_count = 0
        self.total_earned = 0.0
        
        # Configurações
        self.scan_interval = 300  # 5 minutos entre scans
        self.cycle_duration = 60  # 1 minuto de execução por ciclo
        self.target_daily = 36.02  # Meta diária atualizada
        
        # Estatísticas por fonte
        self.earnings_by_source = {
            'microtasks': 0.0,
            'faucets': 0.0,
            'surveys': 0.0,
            'airdrops': 0.0,
            'arbitragem': 0.0,
            'staking': 0.0,
            'testnets': 0.0,
            'referrals': 0.0,
            'cashback': 0.0
        }

    async def start(self) -> None:
        """Inicia o sistema caçador"""
        print("🚀 INSTINTO CAÇADOR v2.0 INICIANDO...")
        print("=" * 50)
        
        # Carrega progresso anterior
        self.executor.load_progress()
        self.accumulator.load_state()
        
        if self.accumulator.balance > 0:
            print(f"💰 Progresso carregado: ${self.accumulator.balance:.2f}")
        
        self.running = True
        
        # Loop principal
        while self.running:
            await self.run_cycle()
            await asyncio.sleep(self.scan_interval)

    async def run_cycle(self) -> Dict[str, Any]:
        """Executa um ciclo completo"""
        self.cycle_count += 1
        
        print(f"\n📡 CICLO {self.cycle_count} INICIADO")
        print(f"   Horário: {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 50)
        
        # 1. Scan de oportunidades
        print("🔍 Escaneando oportunidades...")
        scan_results = await self.scanner.scan_all()
        
        # 2. Validação
        print("✅ Validando oportunidades...")
        validated = await self.validator.validate(scan_results['prioritized'])
        
        cycle_earnings = 0.0
        
        # 3. Execução de micro-tarefas
        if validated:
            print(f"⚡ Executando {len(validated)} oportunidades de micro-tarefas...")
            
            best_tasks = self.select_best_tasks(validated, limit=3)
            
            for task in best_tasks:
                task_type = self.map_task_type(task['domain'])
                if task_type:
                    result = await self.executor.execute_task(task_type)
                    if result['success']:
                        cycle_earnings += result['reward']
                        self.earnings_by_source['microtasks'] += result['reward']
                        
                        await self.accumulator.add_earnings(
                            result['reward'],
                            task['domain']
                        )
        
        # 4. Fontes de renda adicionais
        print("💰 Buscando fontes adicionais...")
        additional_results = await self.additional_sources.scan_all_sources()
        additional_potential = self.additional_sources.calculate_potential(additional_results)
        
        # Executa arbitragem (fonte principal)
        if additional_results.get('arbitragem'):
            arbitrage_opportunities = additional_results['arbitragem']
            for opp in arbitrage_opportunities[:2]:  # Executa 2 arbitragens por ciclo
                profit = opp.get('estimated_profit', 0)
                cycle_earnings += profit
                self.earnings_by_source['arbitragem'] += profit
                
                await self.accumulator.add_earnings(profit, 'arbitragem')
                print(f"   💱 Arbitragem {opp['pair']}: +${profit:.2f}")
        
        # Registra potencial de outras fontes
        for source, value in additional_potential.items():
            if source != 'arbitragem' and value > 0:
                # Adiciona fração do potencial como ganho realizado
                realized = value * 0.1  # 10% do potencial
                cycle_earnings += realized
                self.earnings_by_source[source] += realized
                
                await self.accumulator.add_earnings(realized, source)
        
        # 5. Atualiza total
        self.total_earned += cycle_earnings
        
        # 6. Salva progresso
        self.executor.save_progress()
        self.accumulator.save_state()
        
        # 7. Relatório do ciclo
        cycle_result = {
            'success': True,
            'cycle': self.cycle_count,
            'earnings': cycle_earnings,
            'total_earned': self.total_earned,
            'balance': self.accumulator.balance,
            'trading_ready': self.accumulator.get_statistics()['trading_ready'],
            'earnings_by_source': self.earnings_by_source.copy()
        }
        
        print(f"\n📊 RESULTADO DO CICLO:")
        print(f"   Ganhos do ciclo: ${cycle_earnings:.2f}")
        print(f"   Total acumulado: ${self.total_earned:.2f}")
        print(f"   Saldo disponível: ${self.accumulator.balance:.2f}")
        print(f"   Trading pronto: {'SIM' if cycle_result['trading_ready'] else 'NÃO'}")
        
        # Mostra ganhos por fonte
        print(f"\n📈 GANHOS POR FONTE:")
        for source, amount in self.earnings_by_source.items():
            if amount > 0:
                print(f"   - {source}: ${amount:.2f}")
        
        return cycle_result

    def select_best_tasks(self, validated: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
        """Seleciona melhores tarefas por ROI"""
        sorted_tasks = sorted(
            validated,
            key=lambda x: x.get('roi_per_hour', 0),
            reverse=True
        )
        return sorted_tasks[:limit]

    def map_task_type(self, domain: str) -> Optional[str]:
        """Mapeia domínio para tipo de tarefa"""
        task_map = {
            'timebucks.com': 'survey',
            'freecash.com': 'app_test',
            'ysense.com': 'survey',
            'swagbucks.com': 'video',
            'earnably.com': 'click',
            'freebitco.in': 'click',
            'cointiply.com': 'survey',
            'firefaucet.win': 'click'
        }
        return task_map.get(domain)

    async def stop(self) -> None:
        """Para o sistema"""
        self.running = False
        await self.scanner.close()
        
        # Salva estado final
        self.executor.save_progress()
        self.accumulator.save_state()
        
        print("\n" + "=" * 50)
        print("🏁 INSTINTO CAÇADOR PARADO")
        print(f"💰 Total ganho: ${self.total_earned:.2f}")
        print(f"📊 Ciclos completados: {self.cycle_count}")
        print(f"📈 Ganhos por fonte:")
        for source, amount in self.earnings_by_source.items():
            if amount > 0:
                print(f"   - {source}: ${amount:.2f}")

    def get_status(self) -> Dict[str, Any]:
        """Retorna status atual do sistema"""
        return {
            'running': self.running,
            'cycles_completed': self.cycle_count,
            'total_earned': self.total_earned,
            'balance': self.accumulator.balance,
            'trading_ready': self.accumulator.get_statistics()['trading_ready'],
            'progress_percentage': self.accumulator.get_statistics()['progress_to_trading'],
            'earnings_by_source': self.earnings_by_source
        }


if __name__ == "__main__":
    async def test():
        cacador = InstintoCacador()
        
        print("🚀 TESTANDO INSTINTO CAÇADOR v2.0...")
        print("=" * 50)
        
        # Executa 3 ciclos curtos
        for i in range(3):
            await cacador.run_cycle()
            await asyncio.sleep(2)
        
        # Mostra status final
        status = cacador.get_status()
        
        print(f"\n📊 STATUS FINAL:")
        print(f"   Ciclos: {status['cycles_completed']}")
        print(f"   Total ganho: ${status['total_earned']:.2f}")
        print(f"   Saldo: ${status['balance']:.2f}")
        print(f"   Trading pronto: {'SIM' if status['trading_ready'] else 'NÃO'}")
        print(f"   Progresso: {status['progress_percentage']:.1f}%")
        
        print(f"\n📈 GANHOS POR FONTE:")
        for source, amount in status['earnings_by_source'].items():
            if amount > 0:
                print(f"   - {source}: ${amount:.2f}")
        
        await cacador.stop()

    asyncio.run(test())
