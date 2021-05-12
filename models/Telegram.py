import requests, re

class Telegram():
    def __init__(self, token='', client_id=''):
        self.api = 'https://api.telegram.org/bot'
        self._token = token
        self._client_id = str(client_id)

        p = re.compile(r"^\d{1,10}:[A-z0-9-_]{35,35}$")
        if not p.match(token):
            raise Exception('Telegram token is invalid')

        p = re.compile(r"^-*\d{7,10}$")
        if not p.match(client_id):
            raise Exception('Telegram client_id is invalid')

    def send(self, message=''):
        try:
            payload = self.api + self._token + '/sendMessage?chat_id=' + self._client_id + '&parse_mode=Markdown&text=' + message
            resp = requests.get(payload)

            if resp.status_code != 200:
                return None

            resp.raise_for_status()
            json = resp.json()

        except requests.ConnectionError as err:
            print (err)
            return ('')

        except requests.exceptions.HTTPError as err:
            print (err)
            return ('')

        except requests.Timeout as err:
            print (err)
            return ('')

        return json