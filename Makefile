check: black-check isort-check

black-check:
	black --check main.py

isort-check:
	isort --check main.py
