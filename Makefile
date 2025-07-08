# Makefile

PYTHON := python3.11
PIP := $(PYTHON) -m pip

.PHONY: install-dev lint type-check check

install-dev:
	$(PIP) install --upgrade pip
	# Install development tools
	$(PIP) install flake8 mypy pre-commit

lint:
	# Run flake8 over application and tests
	flake8 app/

type-check:
	# Run mypy on the 'app' package, explicitly mapping module 'app' to the current dir
	mypy -p app \
			--ignore-missing-imports \
			--allow-untyped-globals \
			--allow-untyped-defs \
			--no-warn-return-any

check: lint type-check
	@echo "✅ Linting and type-checking passed!"
