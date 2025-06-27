lint:
	flake8 .
	isort . --skip-glob "*env/*"
	black . --exclude ".*env([\\/])|migrations"

format:
	autoflake --in-place --recursive .
	isort .
	black .