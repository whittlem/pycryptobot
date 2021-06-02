from requests import get, post, ConnectionError, exceptions, Timeout



class Discord():
    def __init__(self, webhook=''):
        self._webhook = webhook

    def send(self, message='') -> str:
        try:
            payload = {'content': message}
            resp = post(self._webhook, data=payload)

            if resp.status_code != 200:
                return ''

            resp.raise_for_status()
            json = resp.json()

        except ConnectionError as err:
            print(err)
            return ''

        except exceptions.HTTPError as err:
            print(err)
            return ''

        except Timeout as err:
            print(err)
            return ''

        return json