FROM python:3.9.1-slim-buster

WORKDIR /app

COPY requirements.txt /app/

RUN python -m pip install -U pip &&\
      python -m pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Pass parameters to the container run or mount your config.json into /app/
ENTRYPOINT [ "python3", "-u", "websvc.py" ]
