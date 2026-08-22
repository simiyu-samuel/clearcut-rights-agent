.PHONY: api-dev api-test api-lint web-dev web-build contracts-check

api-dev:
	uvicorn clearcut_api.main:app --app-dir services/api/src --reload

api-test:
	pytest services/api/tests

api-lint:
	ruff check services/api/src services/api/tests

web-dev:
	npm --workspace apps/web run dev

web-build:
	npm --workspace apps/web run build

contracts-check:
	npm --workspace packages/contracts run typecheck

