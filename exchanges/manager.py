import asyncio
import logging

import ccxt.async_support as ccxt

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExchangeManager:
    """
    Менеджер для работы с несколькими биржами.
    Инициализирует биржи, получает стаканы котировок.
    """

    def __init__(self, exchanges):
        """
        Инициализация менеджера
        
        Args:
            exchanges: Список ID бирж, например: ['binance', 'bybit', 'okx']
        """
        self.exchange_ids = exchanges
        self.exchanges = []

    async def init(self):
        """
        Асинхронная инициализация всех бирж
        """
        for ex_id in self.exchange_ids:
            try:
                exchange_class = getattr(ccxt, ex_id)
                e = exchange_class({
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot'  # Работаем только со спотом
                    },
                    'timeout': 10000
                })
                await e.load_markets()
                self.exchanges.append(e)
                logger.info(f"Инициализирована биржа: {ex_id}")
            except Exception as e:
                logger.error(f"Ошибка при инициализации биржи {ex_id}: {e}")

    async def fetch_orderbooks(self, limit=50):
        """
        Получает стаканы котировок для всех бирж и USDT-пар
        
        Args:
            limit: Максимальное количество символов на одну биржу
            
        Returns:
            Список данных о стаканах
        """
        tasks = []
        results = []

        for exchange in self.exchanges:
            try:
                # Получаем все спотовые пары вида XXX/USDT
                symbols = [s for s in exchange.symbols if s.endswith('/USDT')]
                
                # Ограничиваем количество пар (берём первые N)
                symbols = symbols[:limit]

                # Создаём задачи на получение стаканов
                for symbol in symbols:
                    tasks.append(self.fetch_book(exchange, symbol))

            except Exception as e:
                logger.error(f"Ошибка при получении символов для биржи {exchange.id}: {e}")

        if not tasks:
            logger.warning("Нет задач для получения стаканов")
            return results

        # Выполняем все запросы параллельно с таймаутом
        try:
            books = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=30.0
            )

            for book in books:
                if isinstance(book, dict) and book.get('bid') and book.get('ask'):
                    results.append(book)
                elif isinstance(book, Exception):
                    logger.error(f"Ошибка при получении стакана: {book}")

        except asyncio.TimeoutError:
            logger.error("Таймаут при получении стаканов котировок")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении стаканов: {e}")

        logger.info(f"Получено {len(results)} стаканов котировок")
        return results

    async def fetch_book(self, exchange, symbol):
        """
        Получает стакан котировок для одной пары и биржи
        
        Args:
            exchange: Экземпляр биржи
            symbol: Торговая пара, например 'ETH/USDT'
            
        Returns:
            Словарь с bid, ask, объёмом и т.д. или None при ошибке
        """
        try:
            logger.debug(f"Получение стакана для {exchange.id} {symbol}")

            # Запрос стакана (топ 5 уровней)
            ob = await asyncio.wait_for(
                exchange.fetch_order_book(symbol, 5),
                timeout=10.0
            )

            if not ob or not ob.get('bids') or not ob.get('asks'):
                logger.warning(f"Пустой стакан для {exchange.id} {symbol}")
                return None

            # Проверяем, что есть данные
            if len(ob['bids']) == 0 or len(ob['asks']) == 0:
                return None

            book_data = {
                "exchange": exchange.id,
                "symbol": symbol,
                "bid": float(ob['bids'][0][0]),           # Лучшая цена продажи
                "ask": float(ob['asks'][0][0]),           # Лучшая цена покупки
                "volume": float(ob.get('quoteVolume', 0)), # Объём торгов за 24ч
                "timestamp": ob.get('timestamp')
            }

            logger.debug(f"Получен стакан: {book_data}")
            return book_data

        except asyncio.TimeoutError:
            logger.error(f"Таймаут при получении стакана {exchange.id} {symbol}")
        except Exception as e:
            logger.error(f"Ошибка при получении стакана {exchange.id} {symbol}: {e}")

        return None

    async def close(self):
        """
        Закрывает соединения со всеми биржами.
        Важно вызывать при завершении работы!
        """
        for exchange in self.exchanges:
            await exchange.close()
        logger.info("Соединения с биржами закрыты")
        