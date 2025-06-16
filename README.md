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
    *   `DATABASE_URL`: Your database connection string (e.g., `sqlite:///./ar_trade.db` for SQLite, or a PostgreSQL URL).
    *   Exchange API Keys: The application uses `ccxt` to interact with exchanges, which requires API credentials for many operations, especially trading. These should be set in your `.env` file. The naming convention is:
        *   `EXCHANGENAME_API_KEY` (e.g., `BINANCE_API_KEY`)
        *   `EXCHANGENAME_API_SECRET` (e.g., `BINANCE_API_SECRET`)
        *   `EXCHANGENAME_PASSWORD` (this is optional and only required by a few exchanges like KuCoin for API trading, e.g., `KUCOIN_PASSWORD`)
    *   Refer to `.env.example` for a template.

5.  **Run the application:**
    Ensure your `.env` file is configured, then run:
    ```bash
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
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
    *   Description: Fetches account balances from a specified exchange. Requires API credentials (loaded from environment variables as per the convention `EXCHANGENAME_API_KEY` / `EXCHANGENAME_API_SECRET`).
    *   Query Parameters:
        *   `exchange_id` (str, required): The ID of the exchange.
        *   `api_key` (str, optional): **Deprecated**. API keys are now primarily managed via environment variables. Providing keys via query parameters might be removed or disabled for security reasons in future versions.
        *   `api_secret` (str, optional): **Deprecated**.
    *   Example: `/api/v1/exchange/balance?exchange_id=binance` (assuming `BINANCE_API_KEY` and `BINANCE_API_SECRET` are set in `.env`).

*   **`POST /api/v1/orders/place`**
    *   Description: Places a new order on the specified exchange and records it in the database.
    *   Request Body (`OrderRequest` schema):
        *   `exchange_id` (str): ID of the exchange (e.g., "binance").
        *   `symbol` (str): Trading symbol (e.g., "BTC/USDT").
        *   `amount` (float): Quantity of the asset to buy/sell.
        *   `side` (str): "buy" or "sell".
        *   `type` (str): "market" or "limit".
        *   `price` (Optional[float]): Required if `type` is "limit".
        *   `user_id` (Optional[int]): Placeholder for user identification (default: 1).
        *   `is_spot` (bool): `true` for spot trading, `false` for futures (default: `true`).
        *   `client_order_id` (Optional[str]): A unique client-side identifier for the order.
    *   Response (`OrderResponse` schema): Includes the fields from `OrderRequest` plus:
        *   `id` (int): Internal database ID of the order.
        *   `exchange_order_id` (Optional[str]): The ID assigned to the order by the exchange.
        *   `timestamp` (datetime): Order creation timestamp (UTC).
        *   `status` (str): Current status of the order (e.g., "open", "filled", "rejected", "rejected_insufficient_funds").
        *   `filled_amount` (float): Amount of the asset that has been filled.
        *   `remaining_amount` (float): Amount remaining to be filled.
        *   `cost` (float): Total cost of the filled portion of the order.
        *   `fee` (Optional[float]): Trading fee paid.
        *   `fee_currency` (Optional[str]): Currency of the trading fee.
    *   Example: `POST /api/v1/orders/place` with JSON body:
        ```json
        {
          "exchange_id": "binance",
          "symbol": "BTC/USDT",
          "amount": 0.001,
          "side": "buy",
          "type": "limit",
          "price": 25000.0
        }
        ```

*   **`GET /market/market-overview/`**
    *   Description: Provides a real-time market overview for a predefined set of cryptocurrency symbols.
    *   Response: A JSON list, where each item contains:
        *   `symbol`: The cryptocurrency symbol (e.g., "BTC/USDT").
        *   `current_price`: The latest trading price.
        *   `ema_20`: The 20-period Exponential Moving Average (EMA) on the H1 timeframe. Can be `null` if data is insufficient.
        *   `sma_50`: The 50-period Simple Moving Average (SMA) on the H1 timeframe. Can be `null` if data is insufficient.
        *   `support_levels`: A list of identified support levels (up to 5).
        *   `resistance_levels`: A list of identified resistance levels (up to 5).
    *   Details: The endpoint fetches data using the H1 timeframe for indicator calculations and S/R levels. It uses Binance for BTC/USDT, ETH/USDT, DOGE/USDT, and SUI/USDT, and Bitget for POPCAT/USDT and HYPE/USDT.
    *   **Configuration:** The list of cryptocurrency symbols and the exchanges they are fetched from is configured via the `SYMBOL_CONFIG` list at the top of the `src/routers/market_overview.py` file. This allows for easy modification, addition, or removal of symbols and their target exchanges.

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
