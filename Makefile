PY ?= backend/.venv/Scripts/python

.PHONY: install test test-backend test-frontend backend frontend sample

install:
	py -3.11 -m venv backend/.venv || python3.11 -m venv backend/.venv
	$(PY) -m pip install -r backend/requirements.txt
	cd frontend && npm install

test: test-backend test-frontend

test-backend:
	cd backend && ../$(PY) -m pytest

test-frontend:
	cd frontend && npm test

backend:
	cd backend && ../$(PY) app.py

frontend:
	cd frontend && npm run dev

sample:
	$(PY) sample_data/generate_synthetic.py 600 7
