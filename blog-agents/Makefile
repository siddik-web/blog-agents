# Convenience wrapper. `make up` runs the whole thing; `make test` needs no docker.
COMPOSE ?= docker compose
MODEL   ?= llama3.1

.PHONY: up down logs pull-model dev test

up:               ## Build + start app and model (http://localhost:8000)
	$(COMPOSE) up -d --build
	@echo "open http://localhost:8000"

down:             ## Stop containers
	$(COMPOSE) down

logs:             ## Tail logs
	$(COMPOSE) logs -f

pull-model:       ## Pull the model into the in-cluster Ollama (first run)
	$(COMPOSE) exec ollama ollama pull $(MODEL)

dev:              ## Run locally without docker (needs a local model)
	uvicorn app.server:app --reload --port 8000

test:             ## Offline test suite (no docker/model needed)
	python -m tests.run_all
