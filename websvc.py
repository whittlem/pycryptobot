#!/usr/bin/env python3
# encoding: utf-8

import os
import re
import argparse
from websvc.app import app

import sys

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

args = parser.parse_args()

# listen on local host
http_host = "127.0.0.1"
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", http_port))
    app.run(host=http_host, port=port, debug=True)
