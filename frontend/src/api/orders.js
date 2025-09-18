import { apiPost, apiGet, validateRequiredFields, validatePositiveNumber, formatErrorMessage } from './apiHelpers';

// Using apiHelpers for base URL configuration

/**
 * Places an order.
 * @param {object} orderDetails - The details of the order.
 * @param {string} orderDetails.symbol - The trading symbol (e.g., 'BTCUSDT').
 * @param {string} orderDetails.side - Order side ('BUY' or 'SELL').
 * @param {string} orderDetails.type - Order type ('MARKET' or 'LIMIT').
 * @param {number} orderDetails.amount - The quantity of the asset to trade.
 * @param {number} [orderDetails.price] - The price for LIMIT orders. Required if type is 'LIMIT'.
 * @returns {Promise<object|null>} The response data from the API on success, or null on error.
 */
export const placeOrder = async (orderDetails) => {
  // Validate required fields using helper
  const requiredValidation = validateRequiredFields(
    orderDetails, 
    ['symbol', 'side', 'type', 'amount'], 
    'order placement'
  );
  
  if (!requiredValidation.success) {
    console.error('Validation error:', requiredValidation.error);
    return { error: requiredValidation.error };
  }

  // Validate amount is positive
  const amountValidation = validatePositiveNumber(orderDetails.amount, 'amount', 'order placement');
  if (!amountValidation.success) {
    console.error('Validation error:', amountValidation.error);
    return { error: amountValidation.error };
  }

  // Validate price for LIMIT orders
  if (orderDetails.type === 'LIMIT') {
    const priceValidation = validatePositiveNumber(orderDetails.price, 'price', 'order placement');
    if (!priceValidation.success) {
      console.error('Validation error:', priceValidation.error);
      return { error: priceValidation.error };
    }
  }

  // Use API helper for the request
  const response = await apiPost('/orders/place', orderDetails);
  
  if (response.success) {
    return response.data;
  } else {
    return { error: formatErrorMessage(response, 'Failed to place order') };
  }
};

/**
 * Fetches current orders for all symbols.
 * @returns {Promise<Array|null>} Array of current orders or null on error.
 */
export const getCurrentOrders = async () => {
  try {
    const response = await apiGet('/spot-trades/orders');
    
    if (response.success) {
      return response.data;
    } else {
      console.error('Error fetching current orders:', response.error);
      return null;
    }
  } catch (error) {
    console.error('Error fetching current orders:', error);
    return null;
  }
};
