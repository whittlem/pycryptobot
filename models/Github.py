import requests


class Github:
    def __init__(
        self, user="whittlem", repo="pycryptobot", api_url="https://api.github.com"
    ):
        self.api_url = api_url
        self.user = user
        self.repo = repo

        # options
        self.debug = False
        self.die_on_api_error = False

    def get_branch_commits(self, branch=""):
        return self.api("GET", f"/repos/{self.user}/{self.repo}/commits/{branch}")

    def get_branch_commit_stats(self, branch=""):
        return self.get_branch_commits(branch)["stats"]

    def getMainBranchCommitTotal(self):
        try:
            return self.get_branch_commit_stats("main")["total"]
        except Exception:
            return -1

    def get_commits(self):
        return self.api("GET", f"/repos/{self.user}/{self.repo}/commits")

    def get_repo(self):
        return self.api("GET", f"/repos/{self.user}/{self.repo}")

    def get_repo_releases(self):
        return self.api("GET", f"/repos/{self.user}/{self.repo}/releases")

    def get_latest_release(self):
        resp = self.get_repo_releases()

        if len(resp) == 0:
            return ""

        return resp[0]

    def get_latest_release_name(self):
        try:
            resp = self.get_repo_releases()

            if len(resp) == 0:
                return ""

            return resp[0]["name"]
        except Exception:
            return ""

    def get_repo_tags(self):
        return self.api("GET", f"/repos/{self.user}/{self.repo}/tags")

    def get_latest_tag(self):
        resp = self.get_repo_tags()

        if len(resp) == 0:
            return ""

        return resp[0]["name"]

    def api(self, method, uri, payload=""):
        if not isinstance(method, str):
            raise TypeError("Method is not a string.")

        if not method not in ["GET", "POST"]:
            raise TypeError("Method not GET or POST.")

        if not isinstance(uri, str):
            raise TypeError("Method is not a string.")

        try:
            if method == "GET":
                resp = requests.get(self.api_url + uri)
            elif method == "POST":
                resp = requests.post(self.api_url + uri, json=payload)

            if resp.status_code != 200:
                if self.die_on_api_error:
                    raise Exception(
                        f"{method.upper()}GET ({resp.status_code}) {self.api_url}{uri} - {resp.json()['message']}"
                    )
                else:
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
                    raise SystemExit(f"ConnectionError: {self.api_url}")
                else:
                    print(f"ConnectionError: {self.api_url}")
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
                    raise SystemExit(f"HTTPError: {self.api_url}")
                else:
                    print(f"HTTPError: {self.api_url}")
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
                    raise SystemExit(f"Timeout: { self.api_url}")
                else:
                    print(f"Timeout: {self.api_url}")
                    return None
