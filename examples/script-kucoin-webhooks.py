import os
import sys
import time
import signal

sys.path.insert(0, ".")

from models.exchange.kucoin import WebSocketClient as KWebSocketClient  # noqa: E402
from models.exchange.Granularity import Granularity  # noqa: E402


def cls():
    os.system("cls" if os.name == "nt" else "clear")


def handler(signum, frame):
    if signum == 2:
        print(" -> not finished yet!")
        return


try:
    websocket = KWebSocketClient(["NHCT-USDT"], Granularity.FIVE_MINUTES)
    websocket.start()
    message_count = 0
    while True:
        if websocket:
            if (
                message_count != websocket.message_count
                and websocket.tickers is not None
            ):
                cls()
                print("\nMessageCount =", "%i \n" % websocket.message_count)
                print(websocket.candles)
                print(websocket.tickers)
                message_count = websocket.message_count
                time.sleep(5)  # output every 5 seconds, websocket is realtime

# catches a keyboard break of app, exits gracefully
except KeyboardInterrupt:
    signal.signal(signal.SIGINT, handler)
    print("\nPlease wait while threads complete gracefully.")
    websocket.close()
    sys.exit(0)
