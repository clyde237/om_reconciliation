# Raccourcis de développement. `make` seul affiche cette aide.

VENV   := .venv
PYTHON := $(VENV)/bin/python
PIP    := $(PYTHON) -m pip

.DEFAULT_GOAL := help
.PHONY: help install run test fixtures clean

help:  ## Affiche les commandes disponibles
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

$(PYTHON):
	python3 -m venv $(VENV)

install: $(PYTHON)  ## Crée l'environnement et installe les dépendances
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run: $(PYTHON)  ## Lance l'application (jamais `python app.py`)
	$(VENV)/bin/streamlit run app.py

test: $(PYTHON)  ## Exécute la suite de tests
	$(PYTHON) -m pytest -q

fixtures: $(PYTHON)  ## Régénère les classeurs d'exemple des tests
	$(PYTHON) tests/fixtures/generer_fixtures.py

clean:  ## Supprime les fichiers de cache Python
	find . -type d -name __pycache__ -not -path './$(VENV)/*' -exec rm -rf {} +
	rm -rf .pytest_cache
