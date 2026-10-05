"""Регистрирует Lovelace-ресурс для карты YT Subs → Recipe через Supervisor API."""

from __future__ import annotations

import asyncio
import logging
import os

import httpx

_LOGGER = logging.getLogger(__name__)

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
SUPERVISOR_URL = "http://supervisor/core/api"

CARD_URL = "/api/hassio_ingress/yt_subs_recipe/static/yt-subs-recipe-card.js"
RESOURCE_TYPE = "module"


async def _get_existing_resources(client: httpx.AsyncClient) -> list[dict]:
    url = f"{SUPERVISOR_URL}/lovelace/resources"
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}

    resp = await client.get(url, headers=headers)
    if resp.status_code == 404:
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
    return resp.json()


async def _add_resource(client: httpx.AsyncClient) -> bool:
    url = f"{SUPERVISOR_URL}/lovelace/resources"
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"url": CARD_URL, "res_type": RESOURCE_TYPE}

    resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code == 400:
        _LOGGER.debug(
            "Не удалось добавить ресурс (возможно, уже существует): %s",
            resp.text,
        )
        return False
    resp.raise_for_status()
    _LOGGER.info("Ресурс Lovelace успешно зарегистрирован: %s", CARD_URL)
    return True


async def register_lovelace_resource() -> None:
    if not SUPERVISOR_TOKEN:
        _LOGGER.error(
            "SUPERVISOR_TOKEN не найден. Регистрация Lovelace-ресурса пропущена."
        )
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            existing = await _get_existing_resources(client)
            if any(r.get("url") == CARD_URL for r in existing):
                _LOGGER.info("Lovelace-ресурс уже зарегистрирован, пропускаем.")
                return

            await _add_resource(client)
        except Exception as e:  # noqa: BLE001
            _LOGGER.error("Ошибка при регистрации Lovelace-ресурса: %s", e)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    asyncio.run(register_lovelace_resource())