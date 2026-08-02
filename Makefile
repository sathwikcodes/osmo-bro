.PHONY: format
format:
	black .

.PHONY: check-format
check-format:
	black --check .

.PHONY: lint
lint:
	flake8 .

.PHONY: install
install:
	pip install -r requirements.txt

.PHONY: run
run:
	uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

.PHONY: run-dev
run-dev:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

.PHONY: docker-build
docker-build:
	docker build -t resolvewithai-api .

.PHONY: docker-run
docker-run:
	docker run -p 8000:8000 resolvewithai-api

.PHONY: docker-compose-up
docker-compose-up:
	docker-compose up --build

.PHONY: docker-compose-down
docker-compose-down:
	docker-compose down

.PHONY: test
test:
	pytest tests/ -v