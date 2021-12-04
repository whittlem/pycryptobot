FROM python:3.9-slim-bullseye AS compile-image

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python -m venv /app
# Make sure we use the virtualenv:
ENV PATH="/app/bin:$PATH"

RUN pip config --user set global.extra-index-url https://www.piwheels.org/simple

COPY requirements.txt .

RUN python -m pip install -U pip && \
    python3 -m pip install --no-cache-dir -r requirements.txt

COPY . /app

# FROM python:3.9-slim-bullseye

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y libatlas-base-dev libopenjp2-7 && \
    rm -rf /var/lib/apt/lists/*

# WORKDIR /app

# COPY --from=compile-image /app /app

# Make sure we use the virtualenv:
# ENV PATH="/app/bin:$PATH"

# Pass parameters to the container run or mount your config.json into /app/
ENTRYPOINT [ "python3", "-u", "pycryptobot.py" ]
