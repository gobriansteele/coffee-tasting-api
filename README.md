# Coffee Tasting API

A production-ready API for tracking coffee tasting notes and brewing parameters.

## Features

- **Coffee Management**: Track coffees from different roasters with detailed origin and processing information
- **Tasting Sessions**: Record brewing parameters and tasting notes for each coffee
- **Flavor Profiles**: Tag coffees and tasting sessions with detailed flavor descriptors
- **Production Ready**: Built with FastAPI, SQLAlchemy, and modern Python practices

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: Supabase Auth integration
- **Package Manager**: uv
- **Logging**: Structured logging with structlog
- **Monitoring**: Prometheus metrics

## Project Structure

```
app/
├── api/                    # API layer
│   └── v1/                # Version 1 API routes
│       ├── endpoints/     # Individual endpoint modules
│       └── api.py         # Main API router
├── core/                  # Core configuration and utilities
│   ├── config.py          # Settings and configuration
│   ├── exceptions.py      # Custom exception classes
│   └── logging.py         # Logging configuration
├── db/                    # Database layer
│   └── database.py        # Database connection and session management
├── models/                # SQLAlchemy models
│   ├── base.py           # Base model class
│   ├── coffee.py         # Coffee-related models
│   └── tasting.py        # Tasting session models
├── repositories/          # Repository pattern for data access
│   └── base.py           # Base repository class
├── schemas/              # Pydantic schemas for API serialization
├── services/             # Business logic layer
└── utils/                # Utility functions
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- uv package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd coffee-tasting-api
```

2. Install dependencies with uv:
```bash
uv sync
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run database migrations:
```bash
uv run alembic upgrade head
```

5. Start the development server:
```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database Schema

### Core Models

- **Roaster**: Coffee roasting companies
- **Coffee**: Individual coffee offerings with origin and processing details
- **FlavorTag**: Reusable flavor descriptors
- **TastingSession**: Brewing sessions with parameters and overall ratings
- **TastingNote**: Individual flavor notes from tasting sessions

### Key Features

- UUID primary keys for all models
- Automatic timestamps (created_at, updated_at)
- Comprehensive brewing parameter tracking
- Flexible flavor tagging system
- User-specific tasting sessions

## Development

### Code Quality

This project uses several tools to maintain code quality:

- **Ruff**: Fast linting and formatting
- **MyPy**: Static type checking
- **Pre-commit**: Git hooks for code quality

Run code quality checks:
```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
```

### Testing

Run the test suite:
```bash
uv run pytest
```

With coverage:
```bash
uv run pytest --cov=app --cov-report=html
```

### Database Migrations

Create a new migration:
```bash
uv run alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
uv run alembic upgrade head
```

## Deployment

### Docker

Build and run with Docker:
```bash
docker build -t coffee-tasting-api .
docker run -p 8000:8000 coffee-tasting-api
```

### Production Considerations

- Set `ENVIRONMENT=production` in your environment variables
- Use a production WSGI server like Gunicorn
- Configure proper database connection pooling
- Set up monitoring and logging aggregation
- Enable SSL/TLS termination at the load balancer level

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details