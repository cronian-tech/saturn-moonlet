check: black-check isort-check ruff-check pip-audit

black-check:
	black --check main.py

isort-check:
	isort --check main.py

ruff-check:
	ruff check main.py

pip-audit:
	pip-audit --strict --desc -r dev-requirements.txt -r requirements.txt
