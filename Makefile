.PHONY: clean virtualenv test docker dist dist-upload

clean:
	find . -name '*.py[co]' -delete

virtualenv:
	virtualenv --prompt '|> pycryptobot <| ' env
	env/bin/pip install -r requirements-dev.txt
	env/bin/python setup.py develop
	@echo
	@echo "VirtualENV Setup Complete. Now run: source env/bin/activate"
	@echo

test:
	python -m pytest \
		-v \
		--cov=pycryptobot \
		--cov-report=term \
		--cov-report=html:coverage-report \
		tests/

docker: clean
	docker build -t pycryptobot:latest .

dist: clean
	rm -rf dist/*
	python setup.py sdist
	python setup.py bdist_wheel

dist-upload:
	twine upload dist/*
