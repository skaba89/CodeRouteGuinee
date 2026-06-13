up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test-backend:
	cd backend && pytest

build-frontend:
	cd frontend && npm install && npm run build
