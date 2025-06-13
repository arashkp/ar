# Project AR API

Welcome to Project AR API! This project provides a backend service with various functionalities,
including integration with cryptocurrency exchanges for market data and account information.

## ✨ Features

*   **Cryptocurrency Exchange Integration**: Leverages the `ccxt` library to connect to multiple exchanges.
    *   Fetch OHLCV (candlestick) market data.
    *   Fetch account balances (requires API keys).
*   **FastAPI Backend**: Built with FastAPI, providing a modern, fast (high-performance) web framework.
*   **Pydantic Settings Management**: Secure and easy configuration via environment variables.
*   **Database Integration**: (Details to be added - currently placeholder `DATABASE_URL`)
*   **Health Check**: `/health` endpoint to monitor API status.

## 🚀 Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd ar
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Create a `.env` file in the project root by copying the example:
    ```bash
    cp .env_example .env
    ```
    Edit the `.env` file with your specific configurations:
    *   `DATABASE_URL`: Your PostgreSQL database connection string.
    *   `EXCHANGE_API_KEY`, `EXCHANGE_API_SECRET`: Generic API credentials if you plan to use one primary exchange configured this way.
    *   Specific exchange keys for supported exchanges if you intend to call them by `exchange_id` (e.g., `BITGET_API_KEY`, `MEXC_API_KEY`, `BITUNIX_API_KEY`). The application will use these if no explicit keys are passed in API requests to the balance endpoint or if an exchange requires them for OHLCV.

5.  **Run the application:**
    ```bash
    uvicorn src.main:app --reload
    ```
    The API will typically be available at `http://127.0.0.1:8000`.

## 📡 API Endpoints

The following are the main API endpoints currently available:

*   **`GET /health`**
    *   Description: Checks the health of the API.
    *   Response: `{"status": "ok"}`

*   **`GET /api/v1/exchange/ohlcv`**
    *   Description: Fetches OHLCV (candlestick) data from a specified exchange.
    *   Query Parameters:
        *   `exchange_id` (str, required): The ID of the exchange (e.g., `bitget`, `mexc`).
        *   `symbol` (str, required): The trading symbol (e.g., `BTC/USDT`).
        *   `timeframe` (str, optional, default: `1h`): The timeframe for data (e.g., `1m`, `5m`, `1h`, `1d`).
        *   `limit` (int, optional, default: `100`): Number of data points.
        *   `api_key` (str, optional): Exchange API key (if required by the exchange for this data).
        *   `api_secret` (str, optional): Exchange API secret (if required).
    *   Example: `/api/v1/exchange/ohlcv?exchange_id=bitget&symbol=BTC/USDT&timeframe=5m`

*   **`GET /api/v1/exchange/balance`**
    *   Description: Fetches account balances from a specified exchange. Requires API credentials.
    *   Query Parameters:
        *   `exchange_id` (str, required): The ID of the exchange.
        *   `api_key` (str, optional): Exchange API key. If not provided, the application will try to use a key from environment variables (e.g., `BITGET_API_KEY`).
        *   `api_secret` (str, optional): Exchange API secret. If not provided, the application will try to use a secret from environment variables.
    *   Example: `/api/v1/exchange/balance?exchange_id=mexc&api_key=your_key&api_secret=your_secret`

*   **`GET /market/market-overview/`**
    *   Description: Provides a real-time market overview for a predefined set of cryptocurrency symbols.
    *   Response: A JSON list, where each item contains:
        *   `symbol`: The cryptocurrency symbol (e.g., "BTC/USDT").
        *   `current_price`: The latest trading price.
        *   `ema_20`: The 20-period Exponential Moving Average (EMA) on the H1 timeframe. Can be `null` if data is insufficient.
        *   `sma_50`: The 50-period Simple Moving Average (SMA) on the H1 timeframe. Can be `null` if data is insufficient.
        *   `support_levels`: A list of identified support levels (up to 5).
        *   `resistance_levels`: A list of identified resistance levels (up to 5).
    *   Details: The endpoint fetches data using the H1 timeframe for indicator calculations and S/R levels. It uses Binance for BTC/USDT, ETH/USDT, DOGE/USDT, and SUI/USDT, and Bitget for POPCAT/USDT and HYPE/USDT. Symbols currently tracked are these six pairs.

## 🧪 How to Run Tests

1.  Ensure you have installed development dependencies (pytest, pytest-asyncio, httpx). If not, you might need to add them to `requirements.txt` or a `requirements-dev.txt` and install them.
    ```bash
    pip install pytest pytest-asyncio httpx
    ```
2.  Navigate to the project root directory.
3.  Run pytest:
    ```bash
    pytest
    ```

## 🤝 Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.
(Further details on contribution guidelines can be added here).

---

*This README is a general guide. Specific project details and advanced configurations might evolve.*
