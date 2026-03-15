from typing import List, Dict, Any
from config import MIN_PROFIT_USD
import logging
import numpy as np

logger = logging.getLogger(__name__)

def ai_filter(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Улучшенный ИИ-фильтр для арбитражных возможностей
    
    Args:
        opportunities: Список арбитражных возможностей
        
    Returns:
        Отфильтрованный список возможностей
    """
    if not opportunities:
        return []
        
    # Преобразуем данные в numpy массив для анализа
    profits = np.array([opp['net_profit'] for opp in opportunities])
    spreads = np.array([opp['spread'] for opp in opportunities])
    volumes = np.array([opp['volume'] for opp in opportunities])
    confidence_scores = np.array([opp['confidence_score'] for opp in opportunities])
    
    # Рассчитываем статистики
    profit_mean = np.mean(profits)
    profit_std = np.std(profits)
    spread_mean = np.mean(spreads)
    volume_mean = np.mean(volumes)
    
    filtered = []
    for opp in opportunities:
        try:
            # Основные фильтры
            if opp['net_profit'] < MIN_PROFIT_USD:
                continue
                
            if opp['spread'] < 0.5:  # Минимальный спред
                continue
                
            # Фильтр по статистической значимости
            profit_z_score = (opp['net_profit'] - profit_mean) / (profit_std + 1e-8)
            if profit_z_score < -1.0:  # Исключаем убыточные относительно среднего
                continue
                
            # Приоритет возможностям с высоким рейтингом доверия
            if opp['confidence_score'] < 50:  # Минимальный рейтинг доверия 50/100
                continue
                
            # Проверка на аномалии
            if opp['volume'] > volume_mean * 10:  # Подозрительно высокий объем
                logger.warning(f"Обнаружен аномально высокий объем для {opp['symbol']}: {opp['volume']}")
                continue
                
            # Добавляем в результат
            opp_copy = opp.copy()
            opp_copy['profit_z_score'] = round(profit_z_score, 2)
            filtered.append(opp_copy)
            
        except Exception as e:
            logger.error(f"Ошибка при ИИ-фильтрации для {opp.get('symbol', 'unknown')}: {e}")
            continue
    
    # Сортируем по рейтингу доверия и чистой прибыли
    filtered.sort(key=lambda x: (x['confidence_score'], x['net_profit']), reverse=True)
    
    logger.info(f"После ИИ-фильтрации осталось {len(filtered)} возможностей из {len(opportunities)}")
    return filtered


def calculate_dynamic_thresholds(opportunities: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Рассчитывает динамические пороги для фильтрации на основе текущих данных
    
    Args:
        opportunities: Список арбитражных возможностей
        
    Returns:
        Словарь с динамическими порогами
    """
    if not opportunities:
        return {
            'min_profit': MIN_PROFIT_USD,
            'min_spread': 0.5,
            'min_confidence': 50
        }
        
    profits = [opp['net_profit'] for opp in opportunities]
    spreads = [opp['spread'] for opp in opportunities]
    confidence = [opp['confidence_score'] for opp in opportunities]
    
    return {
        'min_profit': max(MIN_PROFIT_USD, np.percentile(profits, 25)),  # 25-й перцентиль
        'min_spread': max(0.5, np.percentile(spreads, 30)),  # 30-й перцентиль
        'min_confidence': max(50, np.percentile(confidence, 40))  # 40-й перцентиль
    }