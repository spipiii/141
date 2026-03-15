from typing import List, Dict, Any
from config import MIN_VOLUME_USD, MIN_PRICE_AGE_MS, MAX_PRICE_AGE_MS
import time
import logging

logger = logging.getLogger(__name__)

def liquidity_filter(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Фильтрация арбитражных возможностей по ликвидности и актуальности данных
    
    Args:
        opportunities: Список арбитражных возможностей
        
    Returns:
        Отфильтрованный список возможностей
    """
    filtered = []
    current_time_ms = int(time.time() * 1000)
    
    for opp in opportunities:
        try:
            # Проверка объема торгов
            if opp.get('volume', 0) < MIN_VOLUME_USD:
                logger.debug(f"Фильтрация по объему: {opp['symbol']} {opp['volume']} < {MIN_VOLUME_USD}")
                continue
                
            # Проверка актуальности цен
            timestamp = opp.get('timestamp')
            if timestamp:
                price_age_ms = current_time_ms - timestamp
                if price_age_ms < MIN_PRICE_AGE_MS:
                    logger.debug(f"Цена слишком новая для {opp['symbol']}: {price_age_ms}ms < {MIN_PRICE_AGE_MS}ms")
                    continue
                if price_age_ms > MAX_PRICE_AGE_MS:
                    logger.debug(f"Цена устарела для {opp['symbol']}: {price_age_ms}ms > {MAX_PRICE_AGE_MS}ms")
                    continue
            
            # Проверка глубины стакана (если доступно)
            # В реальной реализации нужно проверять доступный объем в стакане
            
            filtered.append(opp)
            
        except Exception as e:
            logger.error(f"Ошибка при фильтрации ликвидности для {opp.get('symbol', 'unknown')}: {e}")
            continue
    
    logger.info(f"После фильтрации по ликвидности осталось {len(filtered)} возможностей из {len(opportunities)}")
    return filtered