from re import compile as re_compile
from requests import get, exceptions, Timeout

class Telegram():
    """Telegram client"""
    def __init__(self, token='', client_id=''):
        """Create telegram class defaults"""
        self.api = 'https://api.telegram.org/bot'
        self._token = token
        self._client_id = str(client_id)

        p = re_compile(r"^\d{1,10}:[A-z0-9-_]{35,35}$")
        if not p.match(token):
            raise Exception('Telegram token is invalid')

        p = re_compile(r"^-?\d{7,13}$")
        if not p.match(client_id):
            raise Exception('Telegram client_id is invalid')

        #print('Telegram configure with for client "' + client_id + '" with token "' + token + '"')

    def send(self, message='', parsemode='Markdown') -> str:
        """Send telegram message"""
        try:
            escaped_message = message.translate(message.maketrans({"*":  r"\*"}))
            payload = f'{self.api}{self._token}/sendMessage?chat_id={self._client_id}&parse_mode={parsemode}&text={escaped_message}'
            resp = get(payload)

            if resp.status_code != 200:
                return ''

            resp.raise_for_status()
            json = resp.json()

        except exceptions.ConnectionError as err:
            print(err)
            return ''

        except exceptions.HTTPError as err:
            print(err)
            return ''

        except Timeout as err:
            print(err)
            return ''

        return json
