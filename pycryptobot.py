#!/usr/bin/env python3
# encoding: utf-8

"""Python Crypto Bot"""

import sys

from controllers.PyCryptoBot import PyCryptoBot


def main() -> None:
    app = PyCryptoBot()
    app.run()


if __name__ == "__main__":
    if sys.version_info < (3, 6, 0):
        sys.stderr.write("You need python 3.6 or higher to run this script\n")
        exit(1)

    main()
