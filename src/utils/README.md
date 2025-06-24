# AR Trading Application - Helper Utilities

This directory contains centralized helper utilities designed to reduce code duplication across the AR trading application. These helpers provide common functionality that can be reused across different modules.

## Overview

The helper utilities are organized into the following modules:

1. **Error Handling** (`error_handlers.py`) - Centralized error handling and validation
2. **API Key Management** (`api_key_manager.py`) - API key retrieval and validation
3. **Exchange Helpers** (`exchange_helpers.py`) - CCXT exchange initialization and management
4. **CRUD Helpers** (`crud_helpers.py`) - Base database operations and patterns

## 1. Error Handling (`error_handlers.py`)

### Purpose
Centralizes error handling patterns to reduce repetitive try-catch blocks across routers and services.

### Key Features
- CCXT exception mapping to appropriate HTTP status codes
- Generic error handling decorators
- Validation helpers for common patterns

### Usage Examples

#### Using Error Handling Decorators

```python
from src.utils.error_handlers import api_error_handler, exchange_error_handler

# For general API endpoints
@api_error_handler("order creation")
async def create_order(order_data, db):
    # Your order creation logic here
    return created_order

# For exchange-specific endpoints
@exchange_error_handler("exchange_id", "balance fetching")
async def get_balance(exchange_id, api_key, api_secret):
    # Your balance fetching logic here
    return balance_data
```

#### Manual Error Handling

```python
from src.utils.error_handlers import handle_ccxt_exception, handle_generic_exception

try:
    # Exchange operation
    result = await exchange.fetch_balance()
    return result
except ccxt.AuthenticationError as e:
    raise handle_ccxt_exception("binance", "balance fetch", e)
except Exception as e:
    raise handle_generic_exception("balance fetch", e)
```

#### Validation Helpers

```python
from src.utils.error_handlers import validate_required_fields, validate_positive_number

# Validate required fields
validate_required_fields(order_data, ["symbol", "amount", "side"], "order creation")

# Validate positive numbers
validate_positive_number(amount, "amount", "order creation")
```

## 2. API Key Management (`api_key_manager.py`)

### Purpose
Centralizes API key retrieval logic from multiple sources (environment variables, query parameters, settings).

### Key Features
- Priority-based key retrieval (query params > settings > env vars)
- Validation for required keys
- Support for both public and private data operations

### Usage Examples

#### Getting API Keys for Public Data (Optional)

```python
from src.utils.api_key_manager import get_api_keys_for_public_data

# For OHLCV data where keys are optional
api_key, api_secret = get_api_keys_for_public_data(
    exchange_id="binance",
    query_api_key=query_api_key,
    query_api_secret=query_api_secret,
    settings=settings
)
```

#### Getting API Keys for Private Data (Required)

```python
from src.utils.api_key_manager import get_api_keys_for_private_data

# For balance/order operations where keys are required
api_key, api_secret = get_api_keys_for_private_data(
    exchange_id="binance",
    query_api_key=query_api_key,
    query_api_secret=query_api_secret,
    settings=settings,
    operation="balance fetching"
)
```

#### Manual Key Retrieval

```python
from src.utils.api_key_manager import get_effective_api_keys, validate_api_keys_required

# Get keys with fallback
api_key, api_secret = get_effective_api_keys(
    exchange_id="binance",
    query_api_key=query_api_key,
    query_api_secret=query_api_secret,
    settings=settings
)

# Validate if required
validate_api_keys_required("binance", api_key, api_secret, "order placement")
```

## 3. Exchange Helpers (`exchange_helpers.py`)

### Purpose
Centralizes CCXT exchange initialization and configuration to reduce duplication.

### Key Features
- Standardized exchange configuration
- Exchange-specific settings
- Safe exchange operations with cleanup
- Order parameter formatting

### Usage Examples

#### Basic Exchange Initialization

```python
from src.utils.exchange_helpers import initialize_exchange

# Initialize exchange with API keys
exchange = await initialize_exchange(
    exchange_id="binance",
    api_key=api_key,
    api_secret=api_secret,
    is_spot=True
)
```

#### Safe Exchange Operations

```python
from src.utils.exchange_helpers import safe_exchange_operation

# Use context manager for safe operations
async with safe_exchange_operation(exchange, "balance fetch", "binance") as ex:
    balance = await ex.fetch_balance()
    return balance
```

#### Order Parameter Formatting

```python
from src.utils.exchange_helpers import format_order_params, parse_exchange_response

# Format order parameters
order_params = format_order_params(
    order_type="limit",
    side="buy",
    amount=0.001,
    symbol="BTC/USDT",
    price=50000,
    client_order_id="my_order_123"
)

# Create order
response = await exchange.create_order(**order_params)

# Parse response for database storage
parsed_data = parse_exchange_response(response, order_data)
```

#### Validation Helpers

```python
from src.utils.exchange_helpers import validate_exchange_capability, validate_symbol

# Check if exchange supports OHLCV
await validate_exchange_capability(exchange, "fetchOHLCV", "binance")

# Validate symbol availability
await validate_symbol(exchange, "BTC/USDT", "binance")
```

## 4. CRUD Helpers (`crud_helpers.py`)

### Purpose
Provides base CRUD operations and common database patterns.

### Key Features
- Generic CRUD operations
- Pagination and filtering
- Error handling and validation
- Date range filtering

### Usage Examples

#### Creating a CRUD Helper for a Model

```python
from src.utils.crud_helpers import BaseCRUDHelper
from src.database.models import Order

# Create a CRUD helper for the Order model
order_crud = BaseCRUDHelper(Order)

# Use the helper for common operations
def create_order(db: Session, order_data: dict) -> Order:
    return order_crud.create(db, order_data)

def get_order(db: Session, order_id: int) -> Order:
    return order_crud.get_by_id_or_404(db, order_id)

def list_orders(db: Session, skip: int = 0, limit: int = 100) -> List[Order]:
    return order_crud.get_multi(db, skip=skip, limit=limit)
```

#### Using Filters and Pagination

```python
# Get orders with filters
filters = {
    "exchange_id": "binance",
    "status": "filled",
    "side": "buy"
}

orders = order_crud.get_multi_with_filters(
    db=db,
    filters=filters,
    skip=0,
    limit=50,
    order_by="timestamp",
    order_desc=True
)
```

#### Validation Helpers

```python
from src.utils.crud_helpers import validate_pagination_params

# Validate pagination parameters
validate_pagination_params(skip=0, limit=100, max_limit=1000)
```

## Integration Examples

### Before (with duplication):

```python
# In orders.py router
@router.post("/place")
async def place_order(order_request: OrderRequest, db: Session = Depends(get_db)):
    try:
        # Get API keys (duplicated logic)
        api_key = os.getenv(f"{order_request.exchange_id.upper()}_API_KEY")
        api_secret = os.getenv(f"{order_request.exchange_id.upper()}_API_SECRET")
        
        if not api_key or not api_secret:
            raise HTTPException(status_code=400, detail="API keys required")
        
        # Initialize exchange (duplicated logic)
        exchange_class = getattr(ccxt, order_request.exchange_id)
        exchange = exchange_class({'apiKey': api_key, 'secret': api_secret})
        
        # Place order
        response = await exchange.create_order(...)
        
        return response
    except ccxt.AuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Auth failed: {e}")
    except ccxt.InsufficientFunds as e:
        raise HTTPException(status_code=400, detail=f"Insufficient funds: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    finally:
        if hasattr(exchange, 'close'):
            await exchange.close()
```

### After (using helpers):

```python
# In orders.py router
from src.utils.error_handlers import exchange_error_handler
from src.utils.api_key_manager import get_api_keys_for_private_data
from src.utils.exchange_helpers import initialize_exchange, safe_exchange_operation

@router.post("/place")
@exchange_error_handler("exchange_id", "order placement")
async def place_order(order_request: OrderRequest, db: Session = Depends(get_db)):
    # Get API keys using helper
    api_key, api_secret = get_api_keys_for_private_data(
        exchange_id=order_request.exchange_id,
        operation="order placement"
    )
    
    # Initialize exchange using helper
    exchange = await initialize_exchange(
        exchange_id=order_request.exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        is_spot=order_request.is_spot
    )
    
    # Safe operation with automatic cleanup
    async with safe_exchange_operation(exchange, "order placement", order_request.exchange_id):
        response = await exchange.create_order(...)
        return response
```

## Benefits

1. **Reduced Code Duplication**: Common patterns are centralized
2. **Consistent Error Handling**: Standardized error responses across the application
3. **Easier Maintenance**: Changes to common logic only need to be made in one place
4. **Better Testing**: Helper functions can be tested independently
5. **Improved Readability**: Business logic is more focused and easier to understand

## Migration Strategy

1. **Phase 1**: Use helpers in new code
2. **Phase 2**: Gradually refactor existing code to use helpers
3. **Phase 3**: Remove duplicated code once all modules use helpers

## Testing

Each helper module includes comprehensive error handling and can be tested independently. Consider creating unit tests for each helper function to ensure reliability.

## Future Enhancements

- Add caching helpers for frequently accessed data
- Create validation schemas for common data structures
- Add logging helpers for consistent log formatting
- Create middleware helpers for common request/response processing 