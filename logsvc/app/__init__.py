import io
import os
import sys
import time
import requests
from threading import Lock
from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit
from pygtail import Pygtail

__all__ = ("follow",)

# threading", "eventlet", "gevent" or None for auto detection
async_mode = None

app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()


def log_reader_thread():
    with io.open("pycryptobot.log") as fp:
        line = fp.readline().strip()
        while line:
            # don't print existing lines
            line = fp.readline().strip()

        while True:
            line = fp.readline().strip()
            if len(line):
                socketio.emit("log_msg", {"data": line})
            socketio.sleep(0.1)


@app.route("/")
def index():
    return render_template("index.html", async_mode=socketio.async_mode)


@socketio.event
def my_event(message):
    session["receive_count"] = session.get("receive_count", 0) + 1
    emit("log_msg", {"data": message["data"]})


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(log_reader_thread)


if __name__ == "__main__":
    socketio.run(app)
