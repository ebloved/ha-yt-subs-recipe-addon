# YT Subs → Recipe (Home Assistant Add-on)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Home Assistant add-on, который скачивает субтитры YouTube Shorts через `yt-dlp` и генерирует кулинарный рецепт в Markdown с помощью Google Gemini.

## Возможности

- 🔗 **Скачивание субтитров** YouTube Shorts (автоматические и ручные треки)
- 🤖 **Генерация рецепта** в Markdown с YAML front matter через Google Gemini
- 🔁 **Автоматический fallback** между моделями Gemini при перегрузке (503/429)
- 🌐 **Опциональный HTTP-прокси** для запросов к Gemini API
- 🍪 **Поддержка cookies** для обхода блокировок YouTube
- 🧩 **Lovelace-карта** для работы прямо из дашборда
- ⚙️ **Настройка через UI** Supervisor
- 🐳 **Многоархитектурная сборка**: `aarch64`, `amd64`, `armv7`

## Установка

1. Откройте **Supervisor → Add-ons → Add-on Store**.
2. Нажмите **⋮ → Repositories**.
3. Вставьте URL репозитория:
   ```
   https://github.com/YOUR_USERNAME/ha-yt-subs-recipe-addon
   ```
4. Нажмите **Add**, закройте окно.
5. Найдите **YT Subs → Recipe** в списке и нажмите **Install**.
6. После установки откройте вкладку **Configuration** и заполните параметры (см. ниже).
7. Нажмите **Save**, затем **Start**.

## Настройка

| Параметр | Описание | По умолчанию |
|---|---|---|
| **gemini_api_key** | API-ключ Google Gemini | — (обязательно) |
| **gemini_models** | Список моделей через запятую, по приоритету | `gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash` |
| **gemini_proxy** | HTTP(S)-прокси для запросов к Gemini (опционально) | — |
| **sub_langs** | Языки субтитров | `ru.*` |
| **cookies_file** | Путь к cookies.txt внутри `/config/` (опционально) | — |

API-ключ можно получить на [Google AI Studio](https://aistudio.google.com/apikey).

### Пример конфигурации

```yaml
gemini_api_key: "AIzaSy..."
gemini_models: "gemini-3.8-flash,gemini-3.7-flash"
gemini_proxy: ""
sub_langs: "ru.*"
cookies_file: ""
```

## Использование

### Встроенный веб-интерфейс

После запуска add-on'а откройте вкладку **Info** и нажмите **Open Web UI**. Откроется страница с полем для ссылки и кнопками:

- **Скачать и сгенерировать** — комбо-действие одной кнопкой
- **Только субтитры** — получить `job_id` без обращения к Gemini
- **Только рецепт** — если `job_id` уже есть

UI доступен через ingress Home Assistant, авторизация — ваша сессия HA.

### Lovelace-карта

При первом запуске add-on автоматически регистрирует Lovelace-ресурс через Supervisor API. Карта становится доступна в списке **Custom: YT Subs → Recipe**.

Добавьте на дашборд:

```yaml
type: custom:yt-subs-recipe-card
title: Рецепт из Shorts
addon_url: http://homeassistant.local:8000
```

Если HA и add-on на разных машинах — замените `homeassistant.local` на IP хоста.

Если авторегистрация не сработала (например, Lovelace в YAML-режиме), добавьте ресурс вручную:

**Настройки → Панели управления → ⋮ → Ресурсы → Добавить**:

- URL: `/api/hassio_ingress/yt_subs_recipe/static/yt-subs-recipe-card.js`
- Тип: **JavaScript Module**

### REST API

Add-on пробрасывает порт `8000` на хост. Все эндпоинты доступны без авторизации (только локальная сеть).

**Скачать субтитры:**

```bash
curl -X POST http://homeassistant.local:8000/api/download \
  -F "url=https://youtube.com/shorts/VIDEO_ID"
```

Ответ:

```json
{
  "status": "ok",
  "video_id": "nPZcWrUEO6Y",
  "job_id": "5ae2cb10",
  "count": 2,
  "files": [
    {
      "filename": "5ae2cb10_...ru-orig.srt",
      "download_url": "files/5ae2cb10_...ru-orig.srt"
    }
  ]
}
```

**Сгенерировать рецепт:**

```bash
curl -X POST http://homeassistant.local:8000/api/generate-recipe \
  -F "job_id=5ae2cb10"
```

Ответ:

```json
{
  "status": "ok",
  "job_id": "5ae2cb10",
  "model": "gemini-3.7-flash",
  "markdown": "---\ntitle: ...",
  "file": "5ae2cb10_recipe.md",
  "download_url": "files/5ae2cb10_recipe.md"
}
```

**Проверка состояния:**

```bash
curl http://homeassistant.local:8000/api/health
```

**Скачать файл:**

```bash
curl -O http://homeassistant.local:8000/files/5ae2cb10_recipe.md
```

## Обход блокировок

### Gemini API

Если `generativelanguage.googleapis.com` недоступен напрямую, укажите в настройках add-on'а HTTP(S)-прокси:

```
http://proxy.example.com:8080
```

или

```
socks5://user:pass@proxy.example.com:1080
```

### YouTube

Если YouTube блокирует IP или выдаёт `429 Too Many Requests`:

1. Установите в браузере расширение **Get cookies.txt LOCALLY**.
2. Зайдите на YouTube под своим аккаунтом.
3. Экспортируйте cookies в формате Netscape.
4. Сохраните файл как `/config/yt_cookies.txt` (через Samba, SSH или File Editor).
5. В настройках add-on'а укажите:
   ```yaml
   cookies_file: "/config/yt_cookies.txt"
   ```
6. Перезапустите add-on.

Cookies существенно повышают лимиты и уменьшают вероятность блокировок.

## Структура add-on'а

```
ha-yt-subs-recipe-addon/
├── repository.yaml
├── README.md
├── LICENSE
└── yt_subs_recipe/
    ├── config.yaml
    ├── build.yaml
    ├── Dockerfile
    ├── run.sh
    ├── requirements.txt
    ├── CHANGELOG.md
    ├── icon.png
    ├── logo.png
    └── app/
        ├── main.py
        ├── register_lovelace.py
        ├── recipe_template.md
        └── static/
            ├── index.html
            └── yt-subs-recipe-card.js
```

## Требования

- Home Assistant OS или Supervised (для поддержки add-on'ов)
- Архитектура: `aarch64`, `amd64` или `armv7`
- Ключ Google Gemini API
- Свободный порт `8000` на хосте HA (можно изменить в `config.yaml`)

## Troubleshooting

### Add-on не запускается

Проверьте лог в **Supervisor → YT Subs → Log**. Частые причины:

- Не задан `gemini_api_key` — add-on запустится, но генерация рецепта не сработает.
- Порт `8000` занят — измените проброс в `config.yaml`.

### Ошибка `503 UNAVAILABLE` от Gemini

Модель перегружена. Add-on автоматически пробует следующие модели из `gemini_models`. Если все недоступны — увеличьте список.

### Ошибка `429 Too Many Requests` от YouTube

Скачивание субтитров ограничено. Решения:

1. Подключите `cookies_file` (см. выше).
2. Уменьшите `sub_langs` — вместо `ru.*,en.*` оставьте только `ru.*`.
3. Подождите 10–15 минут и попробуйте снова.

### Карта не появляется в списке

1. Проверьте **Developer Tools → Console** в браузере на ошибки JS.
2. Перезагрузите страницу с `Ctrl+Shift+R`.
3. Откройте **Настройки → Панели управления → ⋮ → Ресурсы** — должен быть ресурс с URL `/api/hassio_ingress/yt_subs_recipe/static/yt-subs-recipe-card.js`.
4. Если ресурса нет — добавьте вручную (см. раздел «Lovelace-карта»).

### Субтитры не найдены

Некоторые видео не имеют субтитров вообще. Проверьте на странице YouTube — если субтитров нет, `yt-dlp` их не скачает.

## Безопасность

Порт `8000` открыт в вашей локальной сети **без авторизации**. Это значит:

- Любой в локалке может дёргать API и расходовать ваши Gemini-квоты.
- **Не пробрасывайте порт наружу** через роутер.
- Если нужно ограничить доступ — используйте firewall на хосте HA.

Ingress-интерфейс (через вкладку **Open Web UI**) защищён сессией Home Assistant.

## Разработка

### Локальная сборка

```bash
cd yt_subs_recipe
docker build --build-arg BUILD_FROM=python:3.12-slim -t yt-subs-recipe:dev .
docker run --rm -p 8000:8000 \
  -e GEMINI_API_KEY=your_key \
  -v $(pwd)/test_data:/downloads \
  yt-subs-recipe:dev
```

### Установка в HA для тестирования

1. Скопируйте папку `yt_subs_recipe/` в `/addons/yt_subs_recipe/` на хосте HA (через Samba или SSH).
2. В **Supervisor → Add-ons → Add-on Store → ⋮ → Check for updates** появится локальный add-on.
3. Установите и тестируйте.

## Лицензия

[MIT](LICENSE)

## Благодарности

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — скачивание субтитров
- [Google Gemini](https://ai.google.dev/) — генерация рецептов
- [Home Assistant](https://www.home-assistant.io/) — платформа