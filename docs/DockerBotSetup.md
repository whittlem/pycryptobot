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

# Basic Configuratons (Latest release)

### Build a Folder Structure

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

### Populate your docker-compose file

When creating the docker-compose file you will need to ensure that the volume mappings are setup correctly to the files that you have added to the folder structure above.
When configuring volumes in the compose file the left hand side of the : is the local folder and the right hand side is the location in the "app" that it will map the files to inside of the container.
Edit the left hand side as appropiate (it should work out the box if you have the folder structure above. )

The other important note is the _entrypoint_ property this overrides the default entrypoint in the dockerfile with the entrypoint specified in the docker-compose file. In the example below I am calling the telegram-bot.py script instead of the default pycryptobot.py script.

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

Your scanner is now alive and ready to play.
