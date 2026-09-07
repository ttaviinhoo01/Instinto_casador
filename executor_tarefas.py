"""
INSTINTO CAÇADOR - Executor de Tarefas Automáticas
================================================================
Executa micro-tarefas e faucets automaticamente.
Gerencia fila de prioridades e acumula ganhos.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

class TaskExecutor:
    def __init__(self):
        self.completed_tasks = []
        self.total_earned = 0.0
        self.current_balance = 0.0
        self.execution_log = []
        
        # Simulação de tarefas (será substituído por execução real)
        self.task_types = {
            'survey': {'reward': 0.25, 'time_seconds': 300, 'difficulty': 'medium'},
            'video': {'reward': 0.05, 'time_seconds': 60, 'difficulty': 'easy'},
            'app_test': {'reward': 0.50, 'time_seconds': 600, 'difficulty': 'hard'},
            'click': {'reward': 0.01, 'time_seconds': 10, 'difficulty': 'very_easy'},
            'signup': {'reward': 0.75, 'time_seconds': 180, 'difficulty': 'medium'},
            'download': {'reward': 0.15, 'time_seconds': 120, 'difficulty': 'easy'}
        }

    async def execute_task(self, task_type: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executa uma tarefa e retorna resultado"""
        if task_type not in self.task_types:
            return {'success': False, 'error': 'unknown_task_type'}
        
        task_info = self.task_types[task_type]
        
        # Simula execução
        await asyncio.sleep(min(task_info['time_seconds'] / 10, 5))  # Acelera para teste
        
        # Registra ganho
        reward = task_info['reward']
        self.total_earned += reward
        self.current_balance += reward
        
        result = {
            'success': True,
            'task_type': task_type,
            'reward': reward,
            'time_seconds': task_info['time_seconds'],
            'timestamp': time.time()
        }
        
        self.completed_tasks.append(result)
        self.execution_log.append(result)
        
        return result

    async def execute_batch(self, tasks: List[str], delay_between: int = 2) -> Dict[str, Any]:
        """Executa lote de tarefas"""
        results = []
        
        for task_type in tasks:
            result = await self.execute_task(task_type)
            results.append(result)
            await asyncio.sleep(delay_between)  # Evita detecção
        
        return {
            'total_tasks': len(results),
            'successful': sum(1 for r in results if r['success']),
            'total_earned': sum(r.get('reward', 0) for r in results if r['success']),
            'results': results
        }

    async def run_cycle(self, duration_minutes: int = 30) -> Dict[str, Any]:
        """Executa ciclo de tarefas por tempo determinado"""
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        cycle_results = []
        
        # Sequência otimizada de tarefas
        optimal_sequence = [
            'signup',      # Alto valor
            'app_test',    # Alto valor
            'survey',      # Médio valor
            'download',    # Médio valor
            'video',       # Baixo valor
            'click'        # Muito baixo
        ]
        
        while time.time() < end_time:
            for task in optimal_sequence:
                if time.time() >= end_time:
                    break
                    
                result = await self.execute_task(task)
                cycle_results.append(result)
                
                # Intervalo entre tarefas
                await asyncio.sleep(5)
        
        return {
            'duration_minutes': duration_minutes,
            'tasks_completed': len(cycle_results),
            'total_earned': sum(r.get('reward', 0) for r in cycle_results),
            'results': cycle_results
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de execução"""
        if not self.completed_tasks:
            return {
                'total_earned': 0,
                'tasks_completed': 0,
                'average_reward': 0,
                'best_task': None
            }
        
        task_rewards = {}
        for task in self.completed_tasks:
            task_type = task['task_type']
            if task_type not in task_rewards:
                task_rewards[task_type] = []
            task_rewards[task_type].append(task['reward'])
        
        best_task = max(task_rewards.items(), key=lambda x: sum(x[1]) / len(x[1]))
        
        return {
            'total_earned': self.total_earned,
            'tasks_completed': len(self.completed_tasks),
            'average_reward': self.total_earned / len(self.completed_tasks),
            'best_task': best_task[0],
            'best_task_avg': sum(best_task[1]) / len(best_task[1])
        }

    def save_progress(self, filename: str = "data/progress.json"):
        """Salva progresso em arquivo"""
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        data = {
            'total_earned': self.total_earned,
            'completed_tasks': self.completed_tasks,
            'last_updated': time.time()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def load_progress(self, filename: str = "data/progress.json"):
        """Carrega progresso de arquivo"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                self.total_earned = data.get('total_earned', 0)
                self.completed_tasks = data.get('completed_tasks', [])
                return True
        except FileNotFoundError:
            return False


if __name__ == "__main__":
    async def test():
        executor = TaskExecutor()
        
        print("🚀 INICIANDO EXECUÇÃO DE TESTE...")
        
        # Executa ciclo curto de 1 minuto
        results = await executor.run_cycle(duration_minutes=1)
        
        print(f"\n📊 RESULTADOS DO CICLO:")
        print(f"✅ Tarefas completadas: {results['tasks_completed']}")
        print(f"💰 Total ganho: ${results['total_earned']:.2f}")
        
        stats = executor.get_statistics()
        print(f"\n📈 ESTATÍSTICAS:")
        print(f"  - Total acumulado: ${stats['total_earned']:.2f}")
        print(f"  - Média por tarefa: ${stats['average_reward']:.3f}")
        print(f"  - Melhor tarefa: {stats['best_task']}")
        
        # Salva progresso
        executor.save_progress()
        print(f"\n💾 Progresso salvo em data/progress.json")

    asyncio.run(test())
