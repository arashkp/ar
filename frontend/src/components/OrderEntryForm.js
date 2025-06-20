import React, { useState, useEffect } from 'react';
import { placeOrder } from '../api/orders'; // Assuming this path is correct

const OrderEntryForm = ({ selectedSymbol, clickedPrice }) => {
  // State for form inputs
  const [symbol, setSymbol] = useState('');
  const [price, setPrice] = useState(''); // For LIMIT orders
  const [amount, setAmount] = useState(''); // Amount in base asset
  const [side, setSide] = useState('BUY'); // 'BUY' or 'SELL'
  const [type, setType] = useState('LIMIT'); // 'LIMIT' or 'MARKET'

  // State for predefined volume and its calculation
  const [predefinedVolumeUSDT, setPredefinedVolumeUSDT] = useState('100'); // e.g., 100 USDT
  const [calculatedAssetAmount, setCalculatedAssetAmount] = useState(''); // Asset amount from predefined USDT

  // State for API interaction
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState(''); // For success/error messages

  // Effect to update symbol from prop
  useEffect(() => {
    if (selectedSymbol) {
      setSymbol(selectedSymbol);
    }
  }, [selectedSymbol]);

  // Effect to update price from prop if type is LIMIT
  useEffect(() => {
    if (clickedPrice && type === 'LIMIT') {
      setPrice(clickedPrice.toString());
    }
  }, [clickedPrice, type]);

  // Effect to calculate asset amount from predefined USDT volume and price
  // This is a simplified calculation.
  useEffect(() => {
    const numPrice = parseFloat(price);
    const numPredefinedVolume = parseFloat(predefinedVolumeUSDT);
    if (numPrice > 0 && numPredefinedVolume > 0) {
      setCalculatedAssetAmount((numPredefinedVolume / numPrice).toFixed(8)); // Adjust precision as needed
    } else {
      setCalculatedAssetAmount('');
    }
  }, [price, predefinedVolumeUSDT]);

  // Handler for form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setIsLoading(true);

    const orderDetails = {
      symbol,
      side,
      type,
      // Ensure amount is a number; prioritize manually entered amount
      amount: parseFloat(amount) || parseFloat(calculatedAssetAmount) || 0,
      // Price is only sent for LIMIT orders; backend should handle if price is not applicable for MARKET
      price: type === 'LIMIT' ? parseFloat(price) : undefined,
    };

    // Basic validation before sending
    // Validation for amount should check if the final amount is > 0
    if (!orderDetails.symbol || !(orderDetails.amount > 0)) {
      setMessage('Error: Symbol and a valid positive amount are required.');
      setIsLoading(false);
      return;
    }
    if (orderDetails.type === 'LIMIT' && (!orderDetails.price || orderDetails.price <= 0)) {
      setMessage('Error: Price is required for LIMIT orders and must be positive.');
      setIsLoading(false);
      return;
    }

    const result = await placeOrder(orderDetails);
    setIsLoading(false);

    if (result && result.order_id) { // Assuming API returns order_id on success
      setMessage(`Success: Order placed with ID: ${result.order_id}`);
      // Clear form (optional, based on UX preference)
      setPrice('');
      setAmount('');
      // setPredefinedVolumeUSDT(''); // Or keep it for next order
      setCalculatedAssetAmount('');
    } else {
      setMessage(result && result.error ? `Error: ${result.error}` : 'Error: Failed to place order.');
    }
  };

  return (
    <div className="p-4 border rounded-lg shadow-md bg-white dark:bg-gray-800">
      <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">Place Order</h2>

      {/* Predefined Volume */}
      <div className="mb-3">
        <label htmlFor="predefinedVolume" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Predefined Volume (USDT):</label>
        <input
          type="number"
          id="predefinedVolume"
          value={predefinedVolumeUSDT}
          onChange={(e) => setPredefinedVolumeUSDT(e.target.value)}
          placeholder="e.g., 100"
          className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm dark:bg-gray-700 dark:text-gray-200"
        />
      </div>

      {/* Symbol Display */}
      <p className="mb-3 text-sm text-gray-700 dark:text-gray-300">Symbol: <span className="font-semibold">{symbol || 'N/A'}</span></p>

      {/* Type Selector */}
      <div className="mb-3">
        <span className="block text-sm font-medium text-gray-700 dark:text-gray-300">Order Type:</span>
        <div className="mt-1 flex rounded-md shadow-sm">
          <button
            type="button"
            onClick={() => setType('LIMIT')}
            className={`px-4 py-2 rounded-l-md border ${type === 'LIMIT' ? 'bg-indigo-600 text-white dark:bg-indigo-500' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600'} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 text-sm`}
          >
            Limit
          </button>
          <button
            type="button"
            onClick={() => { setType('MARKET'); setPrice(''); }} // Clear price for market orders
            className={`px-4 py-2 rounded-r-md border ${type === 'MARKET' ? 'bg-indigo-600 text-white dark:bg-indigo-500' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600'} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 text-sm`}
          >
            Market
          </button>
        </div>
      </div>

      {/* Price Input (Limit Orders Only) */}
      {type === 'LIMIT' && (
        <div className="mb-3">
          <label htmlFor="price" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Price:</label>
          <input
            type="number"
            id="price"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="Enter price for limit order"
            className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm dark:bg-gray-700 dark:text-gray-200"
          />
        </div>
      )}

      {/* Amount Input */}
      <div className="mb-3">
        <label htmlFor="amount" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Amount (Asset):</label>
        <input
          type="number"
          id="amount"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder={calculatedAssetAmount ? `Default: ${calculatedAssetAmount}` : "Enter amount"}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm dark:bg-gray-700 dark:text-gray-200"
        />
        {calculatedAssetAmount && !amount && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Using calculated amount from predefined volume: {calculatedAssetAmount}</p>}
      </div>

      {/* Side Selector */}
      <div className="mb-4">
        <span className="block text-sm font-medium text-gray-700 dark:text-gray-300">Side:</span>
        <div className="mt-1 flex rounded-md shadow-sm">
          <button
            type="button"
            onClick={() => setSide('BUY')}
            className={`px-4 py-2 rounded-l-md border w-1/2 ${side === 'BUY' ? 'bg-green-600 text-white dark:bg-green-500' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600'} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 text-sm`}
          >
            Buy
          </button>
          <button
            type="button"
            onClick={() => setSide('SELL')}
            className={`px-4 py-2 rounded-r-md border w-1/2 ${side === 'SELL' ? 'bg-red-600 text-white dark:bg-red-500' : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600'} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 text-sm`}
          >
            Sell
          </button>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        onClick={handleSubmit}
        disabled={isLoading}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 dark:disabled:bg-gray-500"
      >
        {isLoading ? 'Placing Order...' : 'Place Order'}
      </button>

      {/* Messages */}
      {message && (
        <p className={`mt-3 text-sm ${message.startsWith('Success:') ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
          {message}
        </p>
      )}
    </div>
  );
};

export default OrderEntryForm;
