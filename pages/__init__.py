""" WebGui pages """

import os

# The dashboard reads the same configuration file as the bots. Fall back to the
# sample configuration so the dashboard can start before a config.json exists.
CONFIG_FILE = "config.json" if os.path.exists("config.json") else "config.json.sample"
