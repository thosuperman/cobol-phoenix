# COBOL Phoenix developer tasks
PY      := backend/.venv/bin/python
RUFF    := backend/.venv/bin/ruff
SAMPLE  := backend/phoenix/samples/phoenix-mutual

.PHONY: help setup runner-image dev-backend dev-frontend test test-backend test-backend-fast test-frontend \
        lint fmt-py lint-frontend validate-generated security corpus sample-expected e2e up down clean

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-20s %s\n", $$1, $$2}'

setup: ## Create the backend venv, install frontend deps, build the GnuCOBOL runner image
	cd backend && uv venv -q .venv --python 3.13 && uv pip install -q --python .venv/bin/python -e ".[dev]"
	cd frontend && npm ci --no-audit --no-fund
	$(MAKE) runner-image

runner-image: ## Build the sandboxed GnuCOBOL runner image
	docker build -t cobol-phoenix-runner:latest runner

dev-backend: ## Run the API on :8000 (docker executor)
	cd backend && PHOENIX_DATA_DIR=./data .venv/bin/uvicorn phoenix.api.main:app --reload --port 8000

dev-frontend: ## Run the web app on :3000
	cd frontend && npm run dev

test: test-backend test-frontend ## Run all tests

test-backend: ## Backend tests (GnuCOBOL tests skip with a reason if the runner image is missing)
	cd backend && .venv/bin/python -m pytest tests -p no:warnings -rs

test-backend-fast: ## Backend tests without GnuCOBOL / corpus (used by Kiro save hook)
	cd backend && .venv/bin/python -m pytest tests -q -p no:warnings -m "not cobol and not corpus"

test-frontend: lint-frontend ## Frontend type-check and production build
	cd frontend && npm run build

lint: fmt-py lint-frontend ## Lint everything

fmt-py: ## Format and lint Python
	$(RUFF) format backend/phoenix backend/tests runner scripts
	$(RUFF) check backend/phoenix backend/tests runner --fix

lint-frontend: ## TypeScript type-check
	cd frontend && npx tsc --noEmit

validate-generated: ## Regenerate the sample service and run its own generated test suite
	rm -rf /tmp/phoenix-validate && $(PY) scripts/validate_generated.py /tmp/phoenix-validate

security: ## Static security checks (bandit) and a secret scan
	cd backend && .venv/bin/bandit -q -r phoenix -x phoenix/samples -s B101,B404,B603,B607,B311
	@! git grep -nIE '(api[_-]?key|secret|password)\s*=\s*["'"'"'][A-Za-z0-9/+_-]{16,}' -- ':!*.md' ':!*.lock' ':!*package-lock.json' || (echo "possible secret committed" && false)

corpus: ## Fetch the external COBOL test corpus at pinned commits (not committed)
	scripts/fetch-corpus.sh

sample-expected: runner-image ## Re-capture the sample expected output from GnuCOBOL
	docker run --rm --network none -e COB_CURRENT_DATE="2026/01/01 09:30:00" -v $(PWD)/$(SAMPLE):/src:ro --entrypoint sh cobol-phoenix-runner:latest \
	  -c 'cd /tmp && cobc -x -I /src/copy -o p /src/cobol/PREMCALC.cbl /src/cobol/RATEENG.cbl 2>/dev/null && ./p < /src/fixtures/policies.txt' > $(SAMPLE)/fixtures/expected-output.txt

e2e: ## Playwright end-to-end test of the demo workflow (needs backend + frontend running)
	cd frontend && npx playwright test

up: ## docker compose up --build
	docker compose up --build -d

down:
	docker compose down

clean:
	rm -rf backend/data frontend/.next
