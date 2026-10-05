"""Регистрирует Lovelace-ресурс для карты YT Subs → Recipe через Supervisor API."""

from __future__ import annotations

import asyncio
import logging
import os

import aiohttp

_LOGGER = logging.getLogger(__name__)

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
SUPERVISOR_URL = "http://supervisor/core/api"

# URL карты через ingress add-on'а. Зависит от slug (yt_subs_recipe).
CARD_URL = "/api/hassio_ingress/yt_subs_recipe/static/yt-subs-recipe-card.js"
RESOURCE_TYPE = "module"


async def _get_existing_resources(session: aiohttp.ClientSession) -> list[dict]:
    """Возвращает список уже зарегистрированных Lovelace-ресурсов."""
    url = f"{SUPERVISOR_URL}/lovelace/resources"
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}

    async with session.get(url, headers=headers) as resp:
        if resp.status == 404:
            _LOGGER.warning(
                "Lovelace работает в режиме YAML. Автоматическая регистрация "
                "ресурса невозможна. Добавьте вручную в configuration.yaml:\n"
                "  lovelace:\n"
                "    resources:\n"
                "      - url: %s\n"
                "        type: %s",
                CARD_URL,
                RESOURCE_TYPE,
            )
            return []
        resp.raise_for_status()
        return await resp.json()


async def _add_resource(session: aiohttp.ClientSession) -> bool:
    """Добавляет ресурс карты в Lovelace."""
    url = f"{SUPERVISOR_URL}/lovelace/resources"
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"url": CARD_URL, "res_type": RESOURCE_TYPE}

    async with session.post(url, headers=headers, json=payload) as resp:
        if resp.status == 400:
            body = await resp.text()
            _LOGGER.debug(
                "Не удалось добавить ресурс (возможно, уже существует): %s", body
            )
            return False
        resp.raise_for_status()
        _LOGGER.info("Ресурс Lovelace успешно зарегистрирован: %s", CARD_URL)
        return True


async def register_lovelace_resource() -> None:
    """Проверяет и добавляет ресурс, если его нет."""
    if not SUPERVISOR_TOKEN:
        _LOGGER.error(
            "SUPERVISOR_TOKEN не найден. Регистрация Lovelace-ресурса пропущена."
        )
        return

    async with aiohttp.ClientSession() as session:
        try:
            existing = await _get_existing_resources(session)
            if any(r.get("url") == CARD_URL for r in existing):
                _LOGGER.info("Lovelace-ресурс уже зарегистрирован, пропускаем.")
                return

            await _add_resource(session)
        except Exception as e:  # noqa: BLE001
            _LOGGER.error("Ошибка при регистрации Lovelace-ресурса: %s", e)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    asyncio.run(register_lovelace_resource())