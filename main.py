"""
INSTINTO CAÇADOR - Ponto de Entrada Principal
"""
import asyncio
from main_cacador import InstintoCacador

async def main():
    cacador = InstintoCacador()
    await cacador.start()

if __name__ == "__main__":
    asyncio.run(main())
