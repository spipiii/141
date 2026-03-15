# main.py
import asyncio
import logging
import time
from typing import List, Dict, Any

from config import EXCHANGES, SYMBOL_LIMIT, DRY_RUN, LOG_LEVEL, MAX_RETRIES
from exchanges.manager import ExchangeManager
from scanner.universe import build_universe
from scanner.arbitrage import find_arbitrage
from filters.liquidity import liquidity_filter
from ai.simple_ai import ai_filter
from telegram_bot import TelegramReporter  # ← Импорт Telegram

# Настройка логирования
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArbitrageBot:
    def __init__(self):
        self.manager = ExchangeManager(EXCHANGES)
        self.retry_count = 0
        self.telegram = TelegramReporter()  # ← Telegram интеграция

    async def initialize(self) -> bool:
        try:
            await self.manager.init()
            if not self.manager.exchanges:
                logger.error("Не удалось инициализировать ни одной биржи")
                return False
            logger.info(f"Инициализировано {len(self.manager.exchanges)} бирж")
            return True
        except Exception as e:
            logger.error(f"Ошибка при инициализации бота: {e}")
            return False

    async def run_once(self) -> None:
        try:
            books = await self.manager.fetch_orderbooks(limit=SYMBOL_LIMIT)
            if not books:
                self.telegram.set_status("⚠️ Не удалось получить стаканы")
                logger.warning("Не удалось получить стаканы котировок")
                return

            universe = build_universe(books)
            if not universe:
                self.telegram.set_status("⚠️ Не удалось построить вселенную")
                logger.warning("Не удалось построить вселенную рынков")
                return

            opps = find_arbitrage(universe)
            logger.info(f"Найдено {len(opps)} арбитражных возможностей")
            self.telegram.set_status(f"✅ Найдено {len(opps)} возможностей")

            opps = liquidity_filter(opps)
            logger.info(f"После фильтрации по ликвидности: {len(opps)}")
            self.telegram.set_status(f"Ликвидность: {len(opps)} осталось")

            opps = ai_filter(opps)
            logger.info(f"После ИИ фильтрации: {len(opps)}")
            self.telegram.set_status(f"ИИ: {len(opps)} сигналов")

            self.telegram.add_signals(opps)  # Сохраняем сигналы
            await self.process_signals(opps)
            self.retry_count = 0

        except Exception as e:
            self.retry_count += 1
            error_msg = f"❌ Ошибка (попытка {self.retry_count}/{MAX_RETRIES}): {e}"
            self.telegram.set_status(error_msg)
            logger.error(error_msg)

    async def process_signals(self, opportunities: List[Dict[str, Any]]) -> None:
        for opp in opportunities:
            try:
                logger.info(f"SIGNAL: {opp}")
                if not DRY_RUN:
                    await self.execute_trade(opp)
                else:
                    logger.info(f"Режим сухого прогона: сделка не исполнена для {opp['symbol']}")
            except Exception as e:
                logger.error(f"Ошибка при обработке сигнала {opp}: {e}")

    async def execute_trade(self, opportunity: Dict[str, Any]) -> None:
        buy_exchange_id = opportunity['buy_exchange']
        sell_exchange_id = opportunity['sell_exchange']

        buy_exchange = next((e for e in self.manager.exchanges if e.id == buy_exchange_id), None)
        sell_exchange = next((e for e in self.manager.exchanges if e.id == sell_exchange_id), None)

        if not buy_exchange or not sell_exchange:
            logger.error(f"Не найдены биржи: {buy_exchange_id}, {sell_exchange_id}")
            return

        symbol = opportunity['symbol']
        buy_price = opportunity['buy_price']
        amount = TRADE_SIZE_USD / buy_price  # Корректный объём

        try:
            buy_order = await buy_exchange.create_market_buy_order(symbol, amount)
            logger.info(f"Создан ордер на покупку: {buy_order}")

            sell_order = await sell_exchange.create_market_sell_order(symbol, amount)
            logger.info(f"Создан ордер на продажу: {sell_order}")

            logger.info(f"✅ Сделка исполнена: {opportunity}")
        except Exception as e:
            logger.error(f"Ошибка при исполнении сделки: {e}")


async def main():
    bot = ArbitrageBot()

    if not await bot.initialize():
        logger.error("Не удалось инициализировать бота")
        return

    # Запуск Telegram-бота в фоне
    telegram_task = asyncio.create_task(bot.telegram.run())

    logger.info("🚀 Арбитражный бот запущен")
    try:
        while True:
            await bot.run_once()
            await asyncio.sleep(3)
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    finally:
        await bot.manager.close()
        logger.info("🔌 Биржи отключены")


if __name__ == "__main__":
    asyncio.run(main())