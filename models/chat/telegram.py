from re import compile as re_compile
from requests import get, ConnectionError, exceptions, Timeout
from logging import getLogger

class Telegram():
    def __init__(self, token='', client_id=''):
        self.api = 'https://api.telegram.org/bot'
        self._token = token
        self._client_id = str(client_id)
        self.logger = getLogger('pyCryptoBot')

        p = re_compile(r"^\d{1,10}:[A-z0-9-_]{35,35}$")
        if not p.match(token):
            raise Exception('Telegram token is invalid')

        p = re_compile(r"^-*\d{7,10}$")
        if not p.match(client_id):
            raise Exception('Telegram client_id is invalid')

        self.logger.info('Telegram configure with for client "' + client_id + '" with token "' + token + '"')

    def send(self, message='') -> str:
        try:
            escaped_message = message.translate(message.maketrans({"*":  r"\*"}))
            payload = self.api + self._token + '/sendMessage?chat_id=' + self._client_id + '&parse_mode=Markdown&text=' + escaped_message
            resp = get(payload)

            if resp.status_code != 200:
                return ''

            resp.raise_for_status()
            json = resp.json()

        except ConnectionError as err:
            self.logger.error(err)
            return ''

        except exceptions.HTTPError as err:
            self.logger.error(err)
            return ''

        except Timeout as err:
            print(err)
            return ''

        return json