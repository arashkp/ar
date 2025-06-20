import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1'; // Assuming the same base URL

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
  try {
    // Basic validation for required fields
    if (!orderDetails || !orderDetails.symbol || !orderDetails.side || !orderDetails.type || !orderDetails.amount) {
      throw new Error('Missing required order details: symbol, side, type, and amount are required.');
    }
    if (orderDetails.type === 'LIMIT' && (orderDetails.price === undefined || orderDetails.price === null || orderDetails.price <= 0)) {
      throw new Error('Price is required for LIMIT orders and must be a positive number.');
    }

    const response = await axios.post(`${API_BASE_URL}/orders/place`, orderDetails);
    return response.data; // Assuming the API returns data including order ID, status, etc.
  } catch (error) {
    console.error('Error placing order:', error.response ? error.response.data : error.message);
    // In a real application, you might want to throw a more specific error or return an error object
    // that the UI can use to display a user-friendly message.
    // For now, re-throwing the error or returning null based on how you want to handle it in the component.
    // Let's return null for simplicity in this case, so the component can check for it.
    return null;
  }
};
