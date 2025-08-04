# AR Trading API

A FastAPI-based trading analysis and management system.

## Features

- Trading analysis and management
- Market overview and historical performance
- Order management
- Investment tracking
- Multi-exchange support (Bitget, MEXC, Bitunix)

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL (for production)

### Setup

1. Clone the repository
2. Create virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Set up environment variables (create `.env` file):
   ```env
   DATABASE_URL=postgresql://user:password@localhost/dbname
   # Add your API keys for exchanges
   ```

5. Run the application:
    ```bash
   python -m uvicorn src.main:app --reload
   ```

6. Access the API documentation at `http://localhost:8000/docs`

## Deployment Options

### Railway (Recommended - Free)

1. Push your code to GitHub
2. Go to [Railway](https://railway.app)
3. Connect your GitHub repository
4. Add PostgreSQL database from Railway dashboard
5. Set environment variables in Railway dashboard
6. Deploy automatically

### Render (Free Tier)

1. Push your code to GitHub
2. Go to [Render](https://render.com)
3. Create new Web Service
4. Connect your GitHub repository
5. Set build command: `pip install -r requirements.txt`
6. Set start command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
7. Add PostgreSQL database
8. Set environment variables

### Fly.io (Free Tier)

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Create app: `fly launch`
4. Set secrets: `fly secrets set DATABASE_URL=your_db_url`
5. Deploy: `fly deploy`

## Environment Variables

Required environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- Exchange API keys (optional, for trading features)

## API Endpoints

- `/docs` - API documentation
- `/health` - Health check
- `/market/*` - Market analysis endpoints
- `/orders/*` - Order management
- `/trades/*` - Trade history
- `/investment/*` - Investment tracking

## Project Structure

```
src/
├── main.py              # FastAPI application
├── routers/             # API route handlers
├── services/            # Business logic
├── database/            # Database models and session
├── schemas/             # Pydantic models
├── utils/               # Utility functions
└── core/               # Core configuration
```
