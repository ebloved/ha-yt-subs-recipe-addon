# Changelog

Все значимые изменения проекта фиксируются в этом файле.
Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии соответствуют [Semantic Versioning](https://semver.org/lang/ru/).

## [1.0.0] - 2026-10-05

### Added

- Первый релиз add-on'а для Home Assistant.
- Скачивание субтитров YouTube Shorts через `yt-dlp` (автоматические и ручные треки).
- Генерация кулинарного рецепта в Markdown с YAML front matter через Google Gemini.
- Автоматический fallback между моделями Gemini при ошибках 503/429.
- Поддержка HTTP(S)-прокси для запросов к Gemini API.
- Поддержка cookies-файла для обхода блокировок YouTube.
- Веб-интерфейс через ingress Home Assistant.
- REST API: `/api/download`, `/api/generate-recipe`, `/api/health`, `/files/{filename}`.
- Lovelace-карта `yt-subs-recipe-card` с UI для скачивания и генерации.
- Автоматическая регистрация Lovelace-ресурса при старте add-on'а.
- CORS-поддержка для работы карты с add-on'ом напрямую через порт.
- Многоархитектурная сборка: `aarch64`, `amd64`, `armv7`.
- Настройка через UI Supervisor (options: `gemini_api_key`, `gemini_models`, `gemini_proxy`, `sub_langs`, `cookies_file`).