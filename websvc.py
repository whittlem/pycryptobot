#!/usr/bin/env python3
# encoding: utf-8

import os
import re
import sys
import argparse
import webbrowser
from threading import Timer
from websvc.app import app

parser = argparse.ArgumentParser(description="PyCryptoBot Web Portal")
parser.add_argument(
    "--host",
    type=str,
    help="web service ip (default: 127.0.0.1)",
)
parser.add_argument(
    "--port",
    type=int,
    help="web service port (default: 5000)",
)
parser.add_argument("--quiet", action="store_true", help="don't open browser")
parser.add_argument("--debug", action="store_true", help="enable debugging")

args = parser.parse_args()

# listen on local host
http_host = "0.0.0.0"
if args.host is not None:
    p = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    if p.match(args.host):
        http_host = args.host
    else:
        parser.print_help(sys.stderr)

# flask listening port
http_port = 5000
if args.port is not None:
    if args.port >= 0 and args.port <= 65535:
        http_port = args.port
    else:
        parser.print_help(sys.stderr)


def open_browser() -> None:
    webbrowser.open_new(f"http://{http_host}:{http_port}/")


if __name__ == "__main__":
    if args.quiet is False:
        Timer(1, open_browser).start()

    port = int(os.environ.get("PORT", http_port))

    # pyright: reportUndefinedVariable=false
    app.run(host=http_host, port=port, debug=args.debug)  # noqa: F821
