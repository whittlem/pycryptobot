from requests import get, post, ConnectionError, exceptions, Timeout



class Twilio():
    def __init__(self, twilio_account_sid='', twilio_auth_token='', twilio_from_phone_number='', twilio_to_phone_number=''):
        self.api = 'https://api.twilio.com/2010-04-01/Accounts/'+ twilio_account_sid +'/Messages.json'
        self._twilio_account_sid = twilio_account_sid
        self._twilio_auth_token = twilio_auth_token
        self._twilio_from_phone_number = twilio_from_phone_number
        self._twilio_to_phone_number = twilio_to_phone_number

    def send(self, message='') -> str:
        try:
            payload = {
                'Body': message,
                'From': self._twilio_from_phone_number,
                'To': self._twilio_to_phone_number
            }
            resp = post(self.api, data=payload, auth=(self._twilio_account_sid, self._twilio_auth_token))

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