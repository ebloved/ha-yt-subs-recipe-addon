ARG BUILD_FROM
FROM ${BUILD_FROM}

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        ca-certificates \
        nodejs \
        jq \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp — всегда последняя версия
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp \
        -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir curl_cffi

COPY app/ /app/

RUN mkdir -p /downloads /data

EXPOSE 8000

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]