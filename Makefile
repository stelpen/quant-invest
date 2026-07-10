.PHONY: install frontend-install frontend-build dev-backend dev-frontend init-data test clean

# --- Backend ---
install:
	pip install -r requirements.txt

dev-backend:
	python run.py --reload

init-data:
	python -c "from core.data.fetcher import AKShareFetcher; from core.data.storage import DataStorage; from core.data.updater import DataUpdater; s = DataStorage(); s.init_db(); DataUpdater(AKShareFetcher(), s).init_data()"

# --- Frontend ---
frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

dev-frontend:
	cd frontend && npm run dev

# --- Test ---
test:
	python -m pytest tests/ -v

# --- Deploy ---
deploy-build: frontend-build
	@echo "Frontend built. Deploy backend with: python run.py --host 0.0.0.0 --port 8000"

# --- Cleanup ---
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/dist 2>/dev/null || true
	rm -rf .pytest_cache 2>/dev/null || true
