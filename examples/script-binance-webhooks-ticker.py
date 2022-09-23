import os
import sys
import time
import signal

sys.path.insert(0, ".")

from models.exchange.binance import WebSocketClient as BWebSocketClient  # noqa: E402
from models.exchange.Granularity import Granularity  # noqa: E402


def cls():
    os.system("cls" if os.name == "nt" else "clear")


def signal_handler(signum, frame):
    if signum == 2:
        print(" -> not finished yet!")
        return


try:
    websocket = BWebSocketClient(["BTCUSDT"], Granularity.ONE_MINUTE)
    websocket.start()
    message_count = 0
    while True:
        if websocket:
            if message_count != websocket.message_count and websocket.tickers is not None:
                cls()
                print(f"Start time: {websocket.getStartTime()}")
                print(f"Time elapsed: {websocket.time_elapsed} seconds")
                print("\nMessageCount =", "%i \n" % websocket.message_count)

                print("Ticker:")
                print(websocket.tickers)
                print("")

                print("Candles:")
                print(websocket.candles)
                print("")

                message_count = websocket.message_count
                time.sleep(1)  # output every 5 seconds, websocket is realtime

# catches a keyboard break of app, exits gracefully
except KeyboardInterrupt:
    signal.signal(signal.SIGINT, signal_handler)
    print("\nPlease wait while threads complete gracefully.")
    websocket.close()
    sys.exit(0)
