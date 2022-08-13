import os
import sys
import time
import signal
from models.exchange.coinbase_pro import WebSocketClient as CWebSocketClient
from models.exchange.Granularity import Granularity


def cls():
    os.system("cls" if os.name == "nt" else "clear")


def handler(signum, frame):
    if signum == 2:
        print(" -> not finished yet!")
        return


try:
    websocket = CWebSocketClient(["ADA-USD"], Granularity.FIVE_MINUTES)
    websocket.start()
    message_count = 0
    while True:
        if websocket:
            if (
                message_count != websocket.message_count
                and websocket.candles is not None
            ):
                cls()
                print("\nMessageCount =", "%i \n" % websocket.message_count)
                print(websocket.candles)
                message_count = websocket.message_count
                time.sleep(5)  # output every 5 seconds, websocket is realtime

# catches a keyboard break of app, exits gracefully
except KeyboardInterrupt:
    signal.signal(signal.SIGINT, handler)
    print("\nPlease wait while threads complete gracefully.")
    websocket.close()
    sys.exit(0)
