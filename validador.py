"""
INSTINTO CAÇADOR - Validador de Oportunidades
================================================================
Filtra golpes e calcula ROI realista.
Prioriza por tempo investido vs retorno.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional

class OpportunityValidator:
    def __init__(self):
        self.blacklist = [
            'scam', 'fraud', 'fake', 'ponzi', 'pyramid',
            'hyip', 'double', 'triple', 'guaranteed'
        ]
        
        self.trusted_domains = [
            'timebucks.com',
            'swagbucks.com',
            'ysense.com',
            'freecash.com',
            'earnably.com',
            'freebitco.in',
            'cointiply.com',
            'firefaucet.win'
        ]
        
        self.realistic_earnings = {
            'timebucks.com': {'per_task': 0.05, 'tasks_per_day': 20, 'time_per_task': 5},
            'swagbucks.com': {'per_task': 0.03, 'tasks_per_day': 15, 'time_per_task': 10},
            'ysense.com': {'per_task': 0.04, 'tasks_per_day': 18, 'time_per_task': 8},
            'freecash.com': {'per_task': 0.06, 'tasks_per_day': 20, 'time_per_task': 6},
            'earnably.com': {'per_task': 0.03, 'tasks_per_day': 12, 'time_per_task': 7},
            'freebitco.in': {'per_claim': 0.00000001, 'claims_per_day': 24, 'time_per_claim': 1},
            'cointiply.com': {'per_task': 0.02, 'tasks_per_day': 30, 'time_per_task': 4},
            'firefaucet.win': {'per_claim': 0.000000005, 'claims_per_day': 48, 'time_per_claim': 2}
        }

    async def validate(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valida lista de oportunidades"""
        validated = []
        
        for opp in opportunities:
            validation = await self._validate_single(opp)
            if validation['is_valid']:
                validated.append(validation)
        
        # Ordena por ROI realista
        validated.sort(key=lambda x: x['roi_per_hour'], reverse=True)
        
        return validated

    async def _validate_single(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """Valida uma oportunidade individual"""
        url = opp.get('url', '')
        name = opp.get('name', '')
        
        # Verifica blacklist
        if any(word in url.lower() for word in self.blacklist):
            return {'is_valid': False, 'reason': 'blacklisted'}
        
        # Verifica se é domínio confiável
        domain = self._extract_domain(url)
        if domain not in self.trusted_domains:
            return {'is_valid': False, 'reason': 'untrusted_domain'}
        
        # Calcula ROI realista
        earnings = self.realistic_earnings.get(domain, {})
        
        if 'per_task' in earnings:
            daily_earnings = earnings['per_task'] * earnings['tasks_per_day']
            time_invested = earnings['tasks_per_day'] * earnings['time_per_task'] / 60  # horas
        else:
            daily_earnings = earnings.get('per_claim', 0) * earnings.get('claims_per_day', 0)
            time_invested = earnings.get('claims_per_day', 0) * earnings.get('time_per_claim', 0) / 60
        
        roi_per_hour = daily_earnings / time_invested if time_invested > 0 else 0
        
        return {
            'is_valid': True,
            'url': url,
            'name': name,
            'domain': domain,
            'daily_earnings': daily_earnings,
            'time_invested_hours': time_invested,
            'roi_per_hour': roi_per_hour,
            'estimated_monthly': daily_earnings * 30
        }

    def _extract_domain(self, url: str) -> str:
        """Extrai domínio da URL"""
        return url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]

    def get_recommendations(self, validated: List[Dict[str, Any]]) -> List[str]:
        """Gera recomendações de ação"""
        recommendations = []
        
        for opp in validated:
            if opp['roi_per_hour'] > 0.5:
                recommendations.append(f"🔥 {opp['name']}: ${opp['estimated_monthly']:.2f}/mês (ROI alto)")
            elif opp['roi_per_hour'] > 0.1:
                recommendations.append(f"✅ {opp['name']}: ${opp['estimated_monthly']:.2f}/mês (ROI médio)")
            else:
                recommendations.append(f"⚠️ {opp['name']}: ${opp['estimated_monthly']:.2f}/mês (ROI baixo)")
        
        return recommendations

    def calculate_total_potential(self, validated: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calcula potencial total de ganhos"""
        total_daily = sum(opp['daily_earnings'] for opp in validated)
        total_monthly = sum(opp['estimated_monthly'] for opp in validated)
        total_time = sum(opp['time_invested_hours'] for opp in validated)
        
        return {
            'daily': total_daily,
            'monthly': total_monthly,
            'time_hours': total_time,
            'effective_rate': total_daily / total_time if total_time > 0 else 0
        }


if __name__ == "__main__":
    async def test():
        from scanner import OpportunityScanner
        
        scanner = OpportunityScanner()
        results = await scanner.scan_all()
        
        validator = OpportunityValidator()
        validated = await validator.validate(results['prioritized'])
        
        print(f"\n📊 VALIDAÇÃO COMPLETA:")
        print(f"✅ Oportunidades válidas: {len(validated)}")
        
        print(f"\n💡 RECOMENDAÇÕES:")
        for rec in validator.get_recommendations(validated):
            print(f"  {rec}")
        
        potential = validator.calculate_total_potential(validated)
        print(f"\n💰 POTENCIAL TOTAL:")
        print(f"  - Diário: ${potential['daily']:.2f}")
        print(f"  - Mensal: ${potential['monthly']:.2f}")
        print(f"  - Tempo investido: {potential['time_hours']:.1f}h/dia")
        print(f"  - Taxa efetiva: ${potential['effective_rate']:.2f}/hora")
        
        await scanner.close()

    asyncio.run(test())
