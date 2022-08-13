import json
import time
from threading import Thread
from websocket import create_connection, WebSocketConnectionClosedException


def main():
    ws = None
    thread = None
    thread_running = False
    thread_keepalive = None

    def websocket_thread():
        global ws

        ws = create_connection("wss://stream.binance.com:9443/ws")
        ws.send(
            json.dumps(
                {
                    "method": "SUBSCRIBE",
                    "params": [
                        "btcusdt@miniTicker",
                        "btcusdt@kline_1m",
                        "btcusdt@kline_5m",
                        "btcusdt@kline_15m",
                        "btcusdt@kline_1h",
                        "btcusdt@kline_6h",
                        "btcusdt@kline_1d",
                    ],
                    "id": 1,
                }
            )
        )

        thread_keepalive.start()
        while not thread_running:
            try:
                data = ws.recv()
                if data != "":
                    msg = json.loads(data)
                else:
                    msg = {}
            except ValueError as e:
                print(e)
                print("{} - data: {}".format(e, data))
            except Exception as e:
                print(e)
                print("{} - data: {}".format(e, data))
            else:
                if "result" not in msg:
                    print(msg)

        try:
            if ws:
                ws.close()
        except WebSocketConnectionClosedException:
            pass
        finally:
            thread_keepalive.join()

    def websocket_keepalive(interval=30):
        global ws
        while ws.connected:
            ws.ping("keepalive")
            time.sleep(interval)

    thread = Thread(target=websocket_thread)
    thread_keepalive = Thread(target=websocket_keepalive)
    thread.start()


if __name__ == "__main__":
    main()
