import requests

class Github():
    def __init__(self, user='whittlem', repo='pycryptobot', api_url='https://api.github.com'):
        self.api_url = api_url
        self.user = user
        self.repo = repo

        # options
        self.debug = False
        self.die_on_api_error = False

    def getBranchCommits(self, branch=''):
        return self.API('GET', f'/repos/{self.user}/{self.repo}/commits/{branch}')

    def getBranchCommitStats(self, branch=''):
        return self.getBranchCommits(branch)['stats']

    def getMainBranchCommitTotal(self):
        try:
            return self.getBranchCommitStats('main')['total']
        except:
            return -1

    def getCommits(self):
        return self.API('GET', f'/repos/{self.user}/{self.repo}/commits')

    def getRepo(self):
        return self.API('GET', f'/repos/{self.user}/{self.repo}')

    def getRepoReleases(self):
        return self.API('GET', f'/repos/{self.user}/{self.repo}/releases')

    def getLatestRelease(self):
        resp = self.getRepoReleases()

        if len(resp) == 0:
            return ''

        return resp[0]

    def getLatestReleaseName(self):
        try:
            resp = self.getRepoReleases()

            if len(resp) == 0:
                return ''

            return resp[0]['name']
        except:
            return ''

    def getRepoTags(self):
        return self.API('GET', f'/repos/{self.user}/{self.repo}/tags')

    def getLatestTag(self):
        resp = self.getRepoTags()

        if len(resp) == 0:
            return ''

        return resp[0]['name']

    def API(self, method, uri, payload=''):
        if not isinstance(method, str):
            raise TypeError('Method is not a string.')

        if not method in ['GET', 'POST']:
            raise TypeError('Method not GET or POST.')

        if not isinstance(uri, str):
            raise TypeError('Method is not a string.')

        try:
            if method == 'GET':
                resp = requests.get(self.api_url + uri)
            elif method == 'POST':
                resp = requests.post(self.api_url + uri, json=payload)

            if resp.status_code != 200:
                if self.die_on_api_error:
                    raise Exception(f"{method.upper()}GET ({resp.status_code}) {self.api_url}{uri} - {resp.json()['message']}")
                else:
                    #print('error:', method.upper() + ' (' + '{}'.format(resp.status_code) + ') ' + self.api_url + uri + ' - ' + '{}'.format(resp.json()['message']))
                    return []

            resp.raise_for_status()
            json = resp.json()
            return json

        except requests.ConnectionError as err:
            if self.debug:
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print(err)
                    return None
            else:
                if self.die_on_api_error:
                    raise SystemExit(f'ConnectionError: {self.api_url}')
                else:
                    print(f'ConnectionError: {self.api_url}')
                    return None

        except requests.exceptions.HTTPError as err:
            if self.debug:
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print(err)
                    return None
            else:
                if self.die_on_api_error:
                    raise SystemExit(f'HTTPError: {self.api_url}')
                else:
                    print(f'HTTPError: {self.api_url}')
                    return None

        except requests.Timeout as err:
            if self.debug:
                if self.die_on_api_error:
                    raise SystemExit(err)
                else:
                    print(err)
                    return None
            else:
                if self.die_on_api_error:
                    raise SystemExit(f'Timeout: { self.api_url}')
                else:
                    print(f'Timeout: {self.api_url}')
                    return None