import asyncio
import json
import logging

from shared.database import AsyncSessionFactory
from shared.models import Lead
from shared.redis_client import DEDUP_TTL, LEADS_QUEUE, get_redis

logger = logging.getLogger(__name__)


def _dedup_key(data: dict) -> str:
    return (
        f"dedup:{data['name']}:{data['phone']}"
        f":{data['offer_id']}:{data['affiliate_id']}"
    )


async def process_lead(data: dict, redis) -> None:
    key = _dedup_key(data)

    # Перевіряємо дедуплікацію SET NX з TTL
    is_new = await redis.set(key, "1", ex=DEDUP_TTL, nx=True)
    if not is_new:
        logger.info("Дублікат, пропускаємо: %s", key)
        return

    async with AsyncSessionFactory() as session:
        lead = Lead(
            name=data["name"],
            phone=data["phone"],
            country=data["country"],
            offer_id=data["offer_id"],
            affiliate_id=data["affiliate_id"],
        )
        session.add(lead)
        await session.commit()
        logger.info("Лід збережено: id=%s", lead.id)


async def run_worker() -> None:
    logger.info("Воркер запущено, слухаємо чергу '%s'", LEADS_QUEUE)
    redis = get_redis()
    try:
        while True:
            try:
                # BRPOP блокує до появи елемента, timeout=5 для graceful shutdown
                result = await redis.brpop(LEADS_QUEUE, timeout=5)
                if result is None:
                    continue
                _, raw = result
                data = json.loads(raw)
                await process_lead(data, redis)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Помилка обробки ліда: %s", exc)
                await asyncio.sleep(1)
    finally:
        await redis.aclose()
        logger.info("Воркер зупинено")