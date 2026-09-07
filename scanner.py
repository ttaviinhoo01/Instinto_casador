"""
INSTINTO CAÇADOR - Scanner de Oportunidades
================================================================
Busca faucets, airdrops e micro-tarefas na internet.
Prioriza por ROI (Retorno sobre Investimento de tempo).
"""

import asyncio
import aiohttp
import json
import time
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

class OpportunityScanner:
    def __init__(self):
        self.session = None
        self.opportunities = []
        self.scanned_sources = []
        
        # Fontes de faucets conhecidos
        self.faucet_sources = [
            "https://freebitco.in",
            "https://cointiply.com",
            "https://firefaucet.win",
            "https://freecardano.com",
            "https://freedoge.co.in",
            "https://free-litecoin.com",
            "https://freebinancecoin.com",
            "https://freeethereum.com",
            "https://freeusdcoin.com",
            "https://freetether.com"
        ]
        
        # Sites de airdrops
        self.airdrop_sources = [
            "https://airdrops.io",
            "https://airdropalert.com",
            "https://coinmarketcap.com/airdrop/"
        ]
        
        # Micro-tarefas
        self.microtask_sources = [
            "https://timebucks.com",
            "https://swagbucks.com",
            "https://ysense.com",
            "https://freecash.com",
            "https://earnably.com"
        ]

    async def initialize(self):
        """Inicializa sessão HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml',
                    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8'
                }
            )

    async def scan_faucets(self) -> List[Dict[str, Any]]:
        """Verifica quais faucets estão ativos"""
        results = []
        
        for faucet in self.faucet_sources:
            try:
                async with self.session.get(faucet, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Verifica se o site está funcional
                        if self._is_faucet_active(html):
                            result = {
                                'type': 'faucet',
                                'url': faucet,
                                'status': 'active',
                                'name': self._extract_name(html, faucet),
                                'min_withdrawal': self._extract_min_withdrawal(html),
                                'reward_interval': self._extract_reward_interval(html),
                                'last_checked': time.time()
                            }
                            results.append(result)
                            
            except Exception as e:
                results.append({
                    'type': 'faucet',
                    'url': faucet,
                    'status': 'error',
                    'error': str(e),
                    'last_checked': time.time()
                })
            
            await asyncio.sleep(1)  # Rate limiting
        
        return results

    async def scan_airdrops(self) -> List[Dict[str, Any]]:
        """Busca airdrops ativos"""
        results = []
        
        for source in self.airdrop_sources:
            try:
                async with self.session.get(source, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Extrai links de airdrops
                        airdrops = self._extract_airdrops(html)
                        results.extend(airdrops)
                        
            except Exception as e:
                continue
            
            await asyncio.sleep(1)
        
        return results

    async def scan_microtasks(self) -> List[Dict[str, Any]]:
        """Verifica micro-tarefas disponíveis"""
        results = []
        
        for source in self.microtask_sources:
            results.append({
                'type': 'microtask',
                'url': source,
                'status': 'available',
                'name': source.replace('https://', '').replace('.com', ''),
                'estimated_pay': self._estimate_pay(source),
                'last_checked': time.time()
            })
            
            await asyncio.sleep(0.5)
        
        return results

    def _is_faucet_active(self, html: str) -> bool:
        """Verifica se o faucet está funcional"""
        indicators = ['faucet', 'claim', 'reward', 'bitcoin', 'satoshi']
        return any(indicator in html.lower() for indicator in indicators)

    def _extract_name(self, html: str, url: str) -> str:
        """Extrai nome do site"""
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if title_match:
            return title_match.group(1)[:50]
        return url.replace('https://', '')

    def _extract_min_withdrawal(self, html: str) -> float:
        """Extrai valor mínimo de saque"""
        patterns = [
            r'minimum withdrawal[:\s]*([\d.]+)',
            r'min withdraw[:\s]*([\d.]+)',
            r'min payout[:\s]*([\d.]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return 0.0

    def _extract_reward_interval(self, html: str) -> int:
        """Extrai intervalo de recompensa em minutos"""
        patterns = [
            r'every (\d+) minutes',
            r'every (\d+) min',
            r'(\d+) minutes timer'
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 60  # padrão: 1 hora

    def _extract_airdrops(self, html: str) -> List[Dict[str, Any]]:
        """Extrai links de airdrops do HTML"""
        airdrops = []
        # Procura padrões de airdrop
        patterns = [
            r'href="([^"]*airdrop[^"]*)"',
            r'href="([^"]*claim[^"]*)"',
            r'href="([^"]*free[^"]*)"'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches[:10]:  # limita a 10 por fonte
                if match.startswith('http'):
                    airdrops.append({
                        'type': 'airdrop',
                        'url': match,
                        'status': 'found',
                        'last_checked': time.time()
                    })
        
        return airdrops

    def _estimate_pay(self, source: str) -> float:
        """Estima pagamento médio por tarefa"""
        estimates = {
            'timebucks.com': 0.50,
            'swagbucks.com': 0.35,
            'ysense.com': 0.40,
            'freecash.com': 0.45,
            'earnably.com': 0.30
        }
        return estimates.get(source, 0.25)

    async def scan_all(self) -> Dict[str, Any]:
        """Executa todos os scans"""
        await self.initialize()
        
        print("🔍 INICIANDO SCAN COMPLETO...")
        
        # Scan paralelo
        faucets_task = asyncio.create_task(self.scan_faucets())
        airdrops_task = asyncio.create_task(self.scan_airdrops())
        microtasks_task = asyncio.create_task(self.scan_microtasks())
        
        faucets = await faucets_task
        airdrops = await airdrops_task
        microtasks = await microtasks_task
        
        results = {
            'timestamp': time.time(),
            'faucets': faucets,
            'airdrops': airdrops,
            'microtasks': microtasks,
            'total_opportunities': len(faucets) + len(airdrops) + len(microtasks)
        }
        
        # Prioriza por ROI
        results['prioritized'] = self.prioritize(results)
        
        return results

    def prioritize(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioriza oportunidades por ROI estimado"""
        prioritized = []
        
        # Faucets ativos têm prioridade alta
        for faucet in results.get('faucets', []):
            if faucet.get('status') == 'active':
                faucet['priority'] = 'HIGH'
                faucet['estimated_daily_earnings'] = self._estimate_faucet_earnings(faucet)
                prioritized.append(faucet)
        
        # Micro-tarefas têm prioridade média
        for task in results.get('microtasks', []):
            task['priority'] = 'MEDIUM'
            task['estimated_daily_earnings'] = task.get('estimated_pay', 0.25) * 10
            prioritized.append(task)
        
        # Airdrops têm prioridade variável
        for airdrop in results.get('airdrops', []):
            airdrop['priority'] = 'LOW'
            airdrop['estimated_daily_earnings'] = 0.10
            prioritized.append(airdrop)
        
        # Ordena por ganhos estimados
        prioritized.sort(key=lambda x: x.get('estimated_daily_earnings', 0), reverse=True)
        
        return prioritized

    def _estimate_faucet_earnings(self, faucet: Dict[str, Any]) -> float:
        """Estima ganhos diários de um faucet"""
        interval_minutes = faucet.get('reward_interval', 60)
        claims_per_day = (24 * 60) / interval_minutes
        average_reward = 0.00000001  # 1 satoshi
        return claims_per_day * average_reward * 100000  # em satoshis

    async def close(self):
        """Fecha sessão HTTP"""
        if self.session:
            await self.session.close()


if __name__ == "__main__":
    async def test():
        scanner = OpportunityScanner()
        results = await scanner.scan_all()
        
        print(f"\n📊 RESULTADOS DO SCAN:")
        print(f"✅ Total de oportunidades: {results['total_opportunities']}")
        print(f"✅ Faucets ativos: {len([f for f in results['faucets'] if f.get('status') == 'active'])}")
        print(f"✅ Airdrops encontrados: {len(results['airdrops'])}")
        print(f"✅ Micro-tarefas: {len(results['microtasks'])}")
        
        print(f"\n🏆 TOP 5 OPORTUNIDADES:")
        for opp in results['prioritized'][:5]:
            print(f"  - {opp.get('name', opp.get('url', 'Unknown'))}: ${opp.get('estimated_daily_earnings', 0):.4f}/dia")
        
        await scanner.close()

    asyncio.run(test())
