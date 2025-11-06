# Docker Setup Guide

This guide explains how to run the Marketing Copilot application using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

## Quick Start

1. **Set environment variables** (optional):
   ```bash
   export SECRET_KEY=your-secret-key-here
   ```

2. **Build and start all services**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Services

The Docker Compose setup includes:

- **postgres**: PostgreSQL 16 database
- **redis**: Redis 7 cache
- **backend**: FastAPI application (port 8000)
- **frontend**: Next.js application (port 3000)

## Environment Variables

### Backend

- `DATABASE_URL`: PostgreSQL connection string (automatically set)
- `SECRET_KEY`: JWT secret key (default: `change-me-in-production`)
- `APP_ENV`: Application environment (default: `production`)
- `APP_NAME`: Application name (default: `Marketing Copilot`)

### Frontend

- `NODE_ENV`: Node environment (default: `production`)
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: `http://localhost:8000`)

## Commands

### Start services
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Rebuild services
```bash
docker-compose up -d --build
```

### Run database migrations
```bash
docker-compose exec backend alembic -c alembic.ini upgrade head
```

### Access database
```bash
docker-compose exec postgres psql -U marketing_copilot -d marketing_copilot_db
```

## Development

For development with hot reload:

1. **Backend**: The backend code is mounted as a volume, so changes are reflected immediately.

2. **Frontend**: Rebuild the frontend container after making changes:
   ```bash
   docker-compose up -d --build frontend
   ```

## Troubleshooting

### Port conflicts
If ports 3000, 8000, 5432, or 6379 are already in use, modify the port mappings in `docker-compose.yml`.

### Database connection issues
Ensure the postgres service is healthy before starting the backend:
```bash
docker-compose ps postgres
```

### Rebuild from scratch
```bash
docker-compose down -v
docker-compose up -d --build
```

## Production Considerations

1. **Set a strong SECRET_KEY**:
   ```bash
   export SECRET_KEY=$(openssl rand -hex 32)
   ```

2. **Use environment-specific configuration**:
   - Create a `.env` file or use Docker secrets
   - Update `NEXT_PUBLIC_API_URL` for production domain

3. **Enable HTTPS**:
   - Use a reverse proxy (nginx, Traefik)
   - Configure SSL certificates

4. **Database backups**:
   - Set up regular backups for the `postgres_data` volume
   - Consider using managed database services in production

