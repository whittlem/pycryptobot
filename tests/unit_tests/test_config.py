import sys
from cement import TestApp

import pytest

sys.path.append('')
# pylint: disable=import-error
from pycryptobot.models.PyCryptoBot import PyCryptoBot


def test_get_version_from_readme():
    with TestApp() as cementApp:
        cementApp.run()
        app = PyCryptoBot(cementApp)
        version = app.getVersionFromREADME()
        assert version != 'v0.0.0'
