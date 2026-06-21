SHELL          := /usr/bin/env bash
.SHELLFLAGS    := -Eeuo pipefail -c
.DEFAULT_GOAL  := help

COMPOSE        ?= docker compose
COMPOSE_FILE   ?= docker-compose.yml
REGISTRY       ?= ghcr.io/itm-skills/sim-prov
TAG            ?= dev
TF_DIR         ?= terraform/envs/prod
K8S_OVERLAY    ?= k8s/overlays/prod

SERVICES       := api worker mock-hlr frontend

.PHONY: help up down restart logs ps seed test lint build push \
        tf-init tf-plan tf-apply tf-destroy \
        k8s-build k8s-deploy k8s-diff \
        vault-bootstrap smoke load-test clean

help: ## Show this help
	@awk 'BEGIN{FS=":.*##"; printf "\nTargets:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ─── docker-compose ────────────────────────────────────────────────────────────
up: ## Start the local stack
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build
	@echo "Frontend  : http://localhost:5173"
	@echo "API       : http://localhost:8000/docs"
	@echo "Grafana   : http://localhost:3000  (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "Kibana    : http://localhost:5601"
	@echo "Vault     : http://localhost:8200  (token: root-dev-token)"

down: ## Stop the local stack (preserve volumes)
	$(COMPOSE) -f $(COMPOSE_FILE) down

restart: down up ## Restart the local stack

logs: ## Tail logs for all services (or SERVICE=api)
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f $(SERVICE)

ps: ## Show running services
	$(COMPOSE) -f $(COMPOSE_FILE) ps

# ─── application ──────────────────────────────────────────────────────────────
seed: ## Seed sample SIMs / plans into postgres
	./scripts/seed-postgres.sh

test: ## Run backend unit tests inside docker
	$(COMPOSE) -f $(COMPOSE_FILE) run --rm api pytest -q

lint: ## Ruff + hadolint
	docker run --rm -v "$(PWD)/app/backend":/src -w /src python:3.11-slim sh -c "pip install --quiet ruff==0.6.9 && ruff check ."
	@for f in docker/Dockerfile.*; do echo "::: $$f"; docker run --rm -i hadolint/hadolint:v2.12.0 hadolint --no-fail - < "$$f"; done

# ─── container images ─────────────────────────────────────────────────────────
build: ## Build all images locally (TAG=dev)
	@for s in $(SERVICES); do \
	  case $$s in \
	    api)      df=docker/Dockerfile.api ;; \
	    worker)   df=docker/Dockerfile.worker ;; \
	    mock-hlr) df=docker/Dockerfile.mock-hlr ;; \
	    frontend) df=docker/Dockerfile.frontend ;; \
	  esac; \
	  echo "build :: $$s ($$df)"; \
	  docker build -f $$df -t $(REGISTRY)/$$s:$(TAG) .; \
	done

push: ## Push all images (TAG=dev)
	@for s in $(SERVICES); do docker push $(REGISTRY)/$$s:$(TAG); done

# ─── terraform ────────────────────────────────────────────────────────────────
tf-init: ## terraform init
	cd $(TF_DIR) && terraform init

tf-plan: ## terraform plan
	cd $(TF_DIR) && terraform plan -out=plan.tfplan

tf-apply: ## terraform apply (consumes plan.tfplan)
	cd $(TF_DIR) && terraform apply plan.tfplan

tf-destroy: ## terraform destroy
	cd $(TF_DIR) && terraform destroy

# ─── kubernetes ───────────────────────────────────────────────────────────────
k8s-build: ## Render manifests
	kustomize build $(K8S_OVERLAY)

k8s-diff: ## Server-side diff
	kustomize build $(K8S_OVERLAY) | kubectl diff -f - || true

k8s-deploy: ## kustomize build | kubectl apply
	kustomize build $(K8S_OVERLAY) | kubectl apply -f -
	kubectl -n sim-prov rollout status deploy/api    --timeout=5m
	kubectl -n sim-prov rollout status deploy/worker --timeout=5m
	kubectl -n sim-prov rollout status deploy/frontend --timeout=5m

# ─── vault ────────────────────────────────────────────────────────────────────
vault-bootstrap: ## Seed secrets, policies, k8s auth
	VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root-dev-token ./vault/scripts/bootstrap.sh

# ─── smoke / load ─────────────────────────────────────────────────────────────
smoke: ## Hit the local stack with the smoke-test script
	BASE_URL=http://localhost:8000 ./scripts/smoke-test.sh

load-test: ## Locust headless: 50 RPS for 60s
	docker run --rm --network provisioning-net \
	  -v "$(PWD)/scripts":/mnt/locust \
	  -e LOCUST_HOST=http://api:8000 \
	  locustio/locust:2.31.5 \
	  -f /mnt/locust/load-test-locustfile.py --headless -u 50 -r 10 -t 60s

# ─── housekeeping ─────────────────────────────────────────────────────────────
clean: ## Remove containers, networks, volumes
	$(COMPOSE) -f $(COMPOSE_FILE) down --volumes --remove-orphans
	docker image prune -f
