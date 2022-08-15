flake8 . --count --select=E203,E266,E501,W503,F403,F401,C901 --max-line-length=160 --show-source --statistics
codespell --ignore-words-list hist --skip "*.json,./tests/unit_tests/responses,./.git/logs"
