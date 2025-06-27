lint:
	pylint $$(find . -name "*.py" -not -path "./.rag_env/*" -not -path "./*env/*")
	isort . --skip-glob "*env/*"
	black . --exclude ".*env([\\/])|migrations"

format:
	autoflake --in-place --recursive .
	isort .
	black .