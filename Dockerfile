FROM registry.access.redhat.com/ubi8/ubi-minimal

RUN microdnf install -y python38 git && \
  mkdir /app

COPY . /app/

WORKDIR /app

RUN python3 -m pip install -r requirements.txt

# Pass parameters to the container run or mount your config.json into /app/
ENTRYPOINT [ "python3", "pycryptobot.py" ]
