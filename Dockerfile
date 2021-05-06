FROM python:3.9-slim

RUN mkdir /app

COPY . /app/

WORKDIR /app

RUN python3 -m pip install -r requirements.txt

# Pass parameters to the container run or mount your config.json into /app/
ENTRYPOINT [ "python3", "-u", "pycryptobot.py" ]
