# PyCryptoBot and Docker

PyCryptoBot can run in two modes Botfight and Telegram Control mode. For Botfight mode setup see [docker-compose option 2](https://github.com/whittlem/pycryptobot#docker-compose-option-2) in the main README file.
This guide is going to concentrate on the Telegram Control and Scanner mode, it will focus on the docker configuration and supplying som ebasic bot config but will not be going in depth to the bot configuration file in this guide.

## Prerquisites

The following software should be installed before starting this guide.

-   Docker
-   docker-compose
-   GIT
-   Visual Sutdio Code (Optional you just need a text editor)
-   Dockerhub account (optional only for cross compiling builds)

## Contents

INSERT TOC HERE!

# Basic Configuratons (Latest release)

## Build a Folder Structure

Build a basic folder structure containing the required configuration files as detailed below.
I reccomend following [this guide](https://playful-curio-e62.notion.site/Scanning-the-market-fd9b58b059dd4cf8addb167af7f36311) for information on how to setup the config.json and scanner.json files. I will post mine at the end of the guide but will highly reccomend creating your own instead of copy pasting configuration.

    ├── market
    │ ├── graphs
    │ │ └── .gitkeep
    │ └── telegram_data
    │ │ └── .gitkeep
    │ ├── binance.key
    │ ├── config.json
    │ ├── pycryptobot.log
    │ ├── scanner.json
    └── docker-compose.yml

## Populate your docker-compose file

When creating the docker-compose file you will need to ensure that the volume mappings are setup correctly to the files that you have added to the folder structure above.
When configuring volumes in the compose file the left hand side of the : is the local folder and the right hand side is the location in the "app" that it will map the files to inside of the container.
Edit the left hand side as appropiate (it should work out the box if you have the folder structure above. )

The other important note is the _entrypoint_ property this overrides the default entrypoint in the dockerfile with the entrypoint specified in the docker-compose file. In the example below I am calling the telegram-bot.py script instead of the default pycryptobot.py script.

docker-compose.yml

```
version: "3.9"

services:
    pycryptobot:
        image: ghcr.io/whittlem/pycryptobot/pycryptobot:latest
        container_name: pycryptobot
        volumes:
            - ./market/binance.key:/app/keys/binance.key:ro
            - ./market/config.json:/app/config.json
            - ./market/pycryptobot.log:/app/pycryptobot.log
            - ./market/scanner.json:/app/scanner.json
            - ./market:/app/telegram_data
            - ./market/graphs:/app/graphs
            - /etc/timezone:/etc/timezone:ro
            - /etc/localtime:/etc/localtime:ro
        environment:
            - PYTHONUNBUFFERED=1
        entrypoint: ["python3", "-u", "telegram_bot.py"]
        restart: always

```

To start the container run the following command from inside the folder that contains the docker-compose.yml file

`docker-compose up -d`

Your scanner is now alive and ready to play.

# Building a container with the Beta Branch

## Clone the beta branch

From a terminal screen clone the beta branch by running the following command, this will download the latest bata branch into a folder called pycryptobot.

If you wish to use a different branch then change the branch name from beta to your chosen branch.

`git clone --branch beta https://github.com/whittlem/pycryptobot`

## Patch as required

At this step you can go in and update or patch any of the files in the pycryptobot folder, do not add your personal config or keys to this folder as you do not want these to be baked into the image.

If you have a git patch file this is where you can apply it using this command replcing the patch file name as needed.

`git apply ~/scanner-go-brrrrrr.patch`

## Build a local copy of your beta container

Build the docker container with all of your chanes by running this command from within the pycryptobot folder. This will compile all of the required files into a docker image that can be ran as a container.

In the example below it assuemes you are going to run docker-compose on the same device you ran the build on. Also note that it is not advisable to run the build on a low powered device like a raspberry pi as this can take up to 7 hours for a complete build. See the Compile for ARM section below on how do build an image for a Raspberry Pi.

`docker build . -file Dockerfile -tag pycryptobot`

If you wish to run the docker container on a different device it is reccomended to push the image to docker hub and download it from there on ther other device. To do this change the "tag" from pycrytobot to dockerhub_usernamer/pycryptobot see the following example.

`docker build . -file Dockerfile -tag mattwa/pycryptobot:beta`

You can then push the image to dockerhub if you wish, this will push the image to your docker hub account.

`docker push mattwa/pycryptobot:beta`

## Run the beta container

Follow the steps above in the Basic confiuration section but modify the image: section of the docker-compose file to have the name that you tagged the image in the build step above.

docker-compose.yml

```
version: "3.9"

services:
    pycryptobot:
        image: pycryptobot
        container_name: pycryptobot
        volumes:
            - ./market/binance.key:/app/keys/binance.key:ro
            - ./market/config.json:/app/config.json
            - ./market/pycryptobot.log:/app/pycryptobot.log
            - ./market/scanner.json:/app/scanner.json
            - ./market:/app/telegram_data
            - ./market/graphs:/app/graphs
            - /etc/timezone:/etc/timezone:ro
            - /etc/localtime:/etc/localtime:ro
        environment:
            - PYTHONUNBUFFERED=1
        entrypoint: ["python3", "-u", "telegram_bot.py"]
        restart: always

```

To start the container run the following command from inside the folder that contains the docker-compose.yml file

`docker-compose up -d`

Your scanner is now alive and ready to play.

# Cross Compiling for ARM

# Appendix

## Useful Docker commands

Run all containers in the docker-compose.yml file

`docker-compose up -d`

Stop and Destry all containers in the docker-compose.yml file

`docker-compose down`

View all logs for all containers in docker-compose.yml (Follow and Tail _Ctrl + C_ to unfollow log. )

`docker-compose logs -f -t`

Show all running containers

`docker ps`

Follow logs of specific container

`docker container logs container_name --follow`

"Exec" into a container This will give you a # prompt for the container that you can mess around inside of it for debuggings. (Dont change any files inside the container as the changes will get lost when the container updates. )

`docker exec -it container_name bash`

## My Config files

I reccomend not blindly copying these and testing out your own versions of these files as I am still tuning my bot to suit my needs.

scanner.json

```
{
    "binance": {
        "quote_currency": ["BUSD"]
    }
}
```

config.json

```
{
    "binance": {
        "api_url": "https://api.binance.com",
        "config": {
            "base_currency": "BTC",
            "quote_currency": "BUSD",
            "enabletelegrambotcontrol": 1,
            "live": 1,
            "disablebullonly": 1,
            "sellupperpcnt": 5,
            "disablebuyelderray": 1,
            "sellatloss": 1,
            "websocket": 1,
            "disablelog": 0,
            "autorestart": 1,
            "enableinsufficientfundslogging": 1,
            "logbuysellinjson": 1,
            "graphs": 1,
            "filelog": 1,
            "logfile": "pycryptobot.log",
            "recvWindow": 20000,
            "fileloglevel": "DEBUG",
            "consolelog": 1,
            "consoleloglevel": "DEBUG"
        },
        "api_key_file": "/app/keys/binance.key"
    },
    "telegram": {
        "token": <Seceret Code>,
        "client_id": <Seceret Code>,
        "user_id": <Seceret Code>,
        "datafolder": "/app/telegram_data"
    },
    "scanner": {
        "atr72_pcnt": 3.0,
        "enableexitaftersell": 1,
        "enableleverage": 0,
        "maxbotcount": 10,
        "autoscandelay": 1,
        "enable_buy_next": 1
    }
}

```
