FROM python:3.11.4-slim-bullseye AS compile-image

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install --no-install-recommends -y \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python -m venv /app
# Make sure we use the virtualenv:
ENV PATH="/app/bin:$PATH"

RUN pip config --user set global.extra-index-url https://www.piwheels.org/simple

COPY requirements.txt .

# RUN python3 -m pip install --no-cache-dir -U pip && \
RUN pip3 install --upgrade --no-cache-dir pip && \
    python3 -m pip install --no-cache-dir -r requirements.txt

COPY . /app

FROM python:3.11.4-slim-bullseye

ARG REPO=whittlem/pycryptobot

LABEL org.opencontainers.image.source https://github.com/${REPO}

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install --no-install-recommends -y \
    libatlas3-base libfreetype6 libjpeg62-turbo \
    libopenjp2-7 libtiff5 libxcb1 && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1000 pycryptobot && \
    useradd -r -u 1000 -g pycryptobot pycryptobot && \
    mkdir -p /app/.config/matplotlib && \
    chown -R pycryptobot:pycryptobot /app

WORKDIR /app

USER pycryptobot

# Make sure we use the virtualenv:
ENV PATH="/app/bin:$PATH"

# Make sure we have a config dir for matplotlib when we not the root user
ENV MPLCONFIGDIR="/app/.config/matplotlib"

COPY --chown=pycryptobot:pycryptobot --from=compile-image /app /app

# Pass parameters to the container run or mount your config.json into /app/
ENTRYPOINT [ "python3", "-u", "pycryptobot.py" ]
