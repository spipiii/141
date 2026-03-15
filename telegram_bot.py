# telegram_bot.py
import asyncio
import logging
from typing import List, Dict
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === НАСТРОЙКИ ===
# 🔑 Обязательно заключите токен в кавычки!
TELEGRAM_BOT_TOKEN = "8688404030:AAHeM7LBRolyLFQvVWBk7DWE44LKT8KA4AA"

# 🛡️ Оставьте None для теста, чтобы принимать команды от всех
# После теста замените на свой chat_id (например, 123456789)
AUTHORIZED_CHAT_ID = None
# ===================

class TelegramReporter:
    def __init__(self):
        try:
            self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            logger.info("✅ Приложение Telegram-бота инициализировано")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота: {e}")
            raise

        self.setup_handlers()
        self.signals: List[Dict] = []
        self.status: str = "Бот не запущен"
        logger.info("🟢 TelegramReporter инициализирован")

    def set_status(self, status: str):
        """Обновляет статус и логирует"""
        self.status = status
        logger.info(f"📌 Статус обновлён: {status}")

    def add_signals(self, signals: List[Dict]):
        """Добавляет сигналы и логирует количество"""
        self.signals = signals
        logger.info(f"📊 Получено {len(signals)} торговых связок для отправки")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        chat_id = update.effective_chat.id
        user = update.effective_user

        logger.info(f"📩 Пользователь запустил бота: {user.first_name} (ID: {chat_id})")

        if AUTHORIZED_CHAT_ID and chat_id != AUTHORIZED_CHAT_ID:
            await update.message.reply_text("❌ Доступ запрещён. Укажите правильный ID.")
            logger.warning(f"🚫 Доступ отклонён для ID: {chat_id}")
            return

        welcome = (
            f"✅ Добро пожаловать, {user.first_name}!\n\n"
            f"Арбитражный сканер подключён.\n\n"
            f"Доступные команды:\n"
            f"  /status — текущий статус бота\n"
            f"  /signals — последние торговые связки\n\n"
            f"📌 Ваш ID: <code>{chat_id}</code>\n"
            f"(скопируйте и вставьте в AUTHORIZED_CHAT_ID при необходимости)"
        )
        await update.message.reply_html(welcome)

    async def send_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет текущий статус"""
        chat_id = update.effective_chat.id
        logger.info(f"🔍 Пользователь запросил статус: {chat_id}")

        if AUTHORIZED_CHAT_ID and chat_id != AUTHORIZED_CHAT_ID:
            logger.warning(f"🚫 Запрос статуса от запрещённого ID: {chat_id}")
            return

        await update.message.reply_text(f"📊 Текущий статус:\n{self.status}")

    async def send_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет последние торговые связки"""
        chat_id = update.effective_chat.id
        logger.info(f"🔍 Пользователь запросил сигналы: {chat_id}")

        if AUTHORIZED_CHAT_ID and chat_id != AUTHORIZED_CHAT_ID:
            logger.warning(f"🚫 Запрос сигналов от запрещённого ID: {chat_id}")
            return

        if not self.signals:
            await update.message.reply_text("📭 Нет активных торговых связок.")
            logger.info("📤 Отправлено: нет сигналов")
            return

        message = f"🔍 Найдено {len(self.signals)} торговых связок:\n\n"
        for i, opp in enumerate(self.signals[:5], 1):
            symbol = opp.get('symbol', 'N/A')
            buy_ex = opp.get('buy_exchange', 'N/A')
            sell_ex = opp.get('sell_exchange', 'N/A')
            spread = opp.get('spread', 0)
            profit = opp.get('net_profit', 0)
            volume = opp.get('volume', 0) / 1000  # в тыс. USDT

            message += (
                f"{i}. {symbol}\n"
                f"   🛒 Покупка: {buy_ex} (${opp.get('buy_price', 0):,.2f})\n"
                f"   💵 Продажа: {sell_ex} (${opp.get('sell_price', 0):,.2f})\n"
                f"   📈 Спред: {spread:.2f}% | Прибыль: ${profit:.2f}\n"
                f"   💰 Объём: ~{volume:.1f}K USDT\n\n"
            )

        if len(self.signals) > 5:
            message += f"… и ещё {len(self.signals) - 5}"

        try:
            await update.message.reply_text(message, disable_web_page_preview=True)
            logger.info(f"📤 Отправлено {len(self.signals)} сигналов пользователю {chat_id}")
        except Exception as e:
            error_msg = f"❌ Ошибка отправки сигналов: {e}"
            await update.message.reply_text(error_msg)
            logger.error(error_msg)

    def setup_handlers(self):
        """Настраивает обработчики команд"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("status", self.send_status))
        self.app.add_handler(CommandHandler("signals", self.send_signals))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        logger.info("🔧 Обработчики команд настроены")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Логирует любые текстовые сообщения"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        text = update.message.text

        logger.info(f"📩 Личное сообщение от {user.first_name} (ID: {chat_id}): '{text}'")

    async def run(self):
        """Запускает Telegram-бота и удерживает его в работе"""
        try:
            await self.app.initialize()
            logger.info("🌐 Приложение Telegram инициализировано")

            await self.app.start()
            logger.info("🟢 Telegram-бот успешно запущен и готов к работе")

            # Удерживаем бота включённым
            await asyncio.Event().wait()  # бесконечное ожидание

        except Exception as e:
            logger.critical(f"💥 Критическая ошибка в Telegram-боте: {e}")
            raise