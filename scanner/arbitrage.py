from typing import List, Dict, Any
from collections import defaultdict
import logging

from config import MIN_SPREAD, TRADE_SIZE_USD, TAKER_FEE, SLIPPAGE_TOLERANCE, STOP_LOSS_PCT, TAKE_PROFIT_PCT

logger = logging.getLogger(__name__)

def find_arbitrage(universe: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Поиск арбитражных возможностей между биржами
    
    Args:
        universe: Словарь с данными о рынках по символам
        
    Returns:
        Список арбитражных возможностей, отсортированный по спреду
    """
    opportunities = []
    
    for symbol, markets in universe.items():
        if len(markets) < 2:
            continue  # Нужно как минимум 2 биржи для арбитража
            
        # Сортируем рынки по цене покупки (ask) и продажи (bid)
        buy_markets = sorted(markets, key=lambda x: x['ask'])
        sell_markets = sorted(markets, key=lambda x: x['bid'], reverse=True)
        
        # Берем лучшие цены
        best_buy = buy_markets[0]
        best_sell = sell_markets[0]
        
        # Проверяем, что это разные биржи
        if best_buy['exchange'] == best_sell['exchange']:
            if len(markets) < 2:
                continue
            # Берем вторую лучшую биржу для продажи
            best_sell = sell_markets[1] if sell_markets[1]['exchange'] != best_buy['exchange'] else None
            if not best_sell:
                continue
        
        buy_price = float(best_buy['ask'])
        sell_price = float(best_sell['bid'])
        
        # Проверяем качество спреда
        if buy_price >= sell_price:
            continue
            
        spread = (sell_price - buy_price) / buy_price * 100
        
        # Фильтрация по минимальному спреду
        if spread < MIN_SPREAD:
            continue
        
        # Расчет прибыли с учетом комиссий и проскальзывания
        gross = TRADE_SIZE_USD * (spread / 100)
        fees = TRADE_SIZE_USD * TAKER_FEE * 2
        slippage_cost = TRADE_SIZE_USD * SLIPPAGE_TOLERANCE * 2
        profit = gross - fees - slippage_cost
        
        # Фильтрация по минимальной прибыли
        if profit <= 0:
            continue
        
        # Расчет рисков
        stop_loss_price = buy_price * (1 - STOP_LOSS_PCT / 100)
        take_profit_price = sell_price * (1 + TAKE_PROFIT_PCT / 100)
        risk_reward_ratio = profit / (TRADE_SIZE_USD * STOP_LOSS_PCT / 100) if profit > 0 else 0
        
        opportunity = {
            "symbol": symbol,
            "buy_exchange": best_buy['exchange'],
            "sell_exchange": best_sell['exchange'],
            "buy_price": buy_price,
            "sell_price": sell_price,
            "spread": round(spread, 3),
            "gross_profit": round(gross, 2),
            "fees": round(fees, 2),
            "slippage": round(slippage_cost, 2),
            "net_profit": round(profit, 2),
            "volume": float(best_buy['volume']),
            "timestamp": best_buy.get('timestamp'),
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "confidence_score": calculate_confidence_score(spread, profit, best_buy['volume'], risk_reward_ratio)
        }
        
        opportunities.append(opportunity)
        logger.debug(f"Найдена возможность арбитража: {opportunity}")
    
    # Сортируем по чистой прибыли и коэффициенту риска/прибыли
    opportunities.sort(key=lambda x: (x["net_profit"], x["risk_reward_ratio"]), reverse=True)
    
    logger.info(f"Найдено {len(opportunities)} арбитражных возможностей")
    return opportunities

def calculate_confidence_score(spread: float, profit: float, volume: float, risk_reward_ratio: float) -> float:
    """
    Рассчитывает рейтинг доверия для арбитражной возможности
    
    Args:
        spread: Спред в процентах
        profit: Прибыль в USD
        volume: Объем торгов
        risk_reward_ratio: Коэффициент риск/прибыль
        
    Returns:
        Рейтинг доверия от 0 до 100
    """
    # Нормализация параметров (предполагаем максимальные значения)
    max_spread = 10.0      # Максимальный спред 10%
    max_profit = 100.0     # Максимальная прибыль 100 USD
    max_volume = 1000000.0 # Максимальный объем 1M USD
    max_rr = 10.0         # Максимальный коэффициент риск/прибыль
    
    spread_score = min(spread / max_spread, 1.0)
    profit_score = min(profit / max_profit, 1.0)
    volume_score = min(volume / max_volume, 1.0)
    rr_score = min(risk_reward_ratio / max_rr, 1.0)
    
    # Взвешенное среднее (объем и коэффициент риск/прибыль имеют больший вес)
    confidence = (
        spread_score * 0.1 +
        profit_score * 0.2 +
        volume_score * 0.4 +
        rr_score * 0.3
    ) * 100
    
    return round(confidence, 2)