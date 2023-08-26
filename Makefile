check: black-check isort-check ruff-check

black-check:
	black --check main.py

isort-check:
	isort --check main.py

ruff-check:
	ruff check main.py
