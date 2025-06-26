import React, { useState, useEffect } from 'react';
import { placeOrder } from '../api/orders'; // Assuming this path is correct

const OrderEntryForm = ({ selectedSymbol, clickedPrice, side, setSide, predefinedVolumeUSDT, setPredefinedVolumeUSDT }) => {
  // Defensive fallback for undefined props
  const safePredefinedVolume = predefinedVolumeUSDT !== undefined && predefinedVolumeUSDT !== null ? predefinedVolumeUSDT : '100';
  // State for form inputs
  const [symbol, setSymbol] = useState('');
  const [price, setPrice] = useState(''); // For LIMIT orders
  const [amount, setAmount] = useState(''); // Amount in base asset
  const [type, setType] = useState('LIMIT'); // 'LIMIT' or 'MARKET'

  // State for API interaction
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState(''); // For success/error messages

  // Effect to update symbol from prop
  useEffect(() => {
    if (selectedSymbol) {
      setSymbol(selectedSymbol);
    } else {
      setSymbol(''); // Handle case where selectedSymbol might become null or undefined
    }
  }, [selectedSymbol]);

  // Effect to update price and amount from clickedPrice
  useEffect(() => {
    if (clickedPrice !== undefined && clickedPrice !== null) {
      if (!symbol) {
        return;
      }

      try {
        const pricePrecision = getSymbolPrecision(symbol);

        const parsedClickedPrice = parseFloat(clickedPrice);
        if (isNaN(parsedClickedPrice)) {
          setPrice(''); // Clear price if NaN
          setAmount(''); // Clear amount if price is NaN
          return;
        }
        const formattedPrice = parsedClickedPrice.toFixed(pricePrecision);
        setPrice(formattedPrice);

        // Also set amount based on predefined volume
        const numPrice = parseFloat(formattedPrice); // Use the formatted price for consistency
        const numPredefinedVolume = parseFloat(safePredefinedVolume);

        if (numPrice > 0 && numPredefinedVolume > 0) {
          const amountPrecision = getAmountPrecision(symbol);
          const rawAmount = numPredefinedVolume / numPrice;
          const flooredAmount = floorToPrecision(rawAmount, amountPrecision);
          const finalAmount = flooredAmount.toFixed(amountPrecision);
          setAmount(finalAmount);
        } else {
          setAmount('');
        }
      } catch (error) {
        // Potentially clear fields or show an error state
        setPrice('');
        setAmount('');
      }
    }
  }, [clickedPrice, safePredefinedVolume, symbol]); // `symbol` here is the local state

  // Helper to get precision for price and amount
  const getSymbolPrecision = (symbol) => {
    if (!symbol) return 2;
    if (symbol.includes('DOGE') || symbol.includes('POPCAT')) return 4;
    if (symbol.includes('BTC')) return 0;
    if (symbol.includes('ETH')) return 1;
    return 2;
  };

  // Helper to get amount precision (BTC: 8, others: same as price precision)
  const getAmountPrecision = (symbol) => {
    if (symbol.includes('DOGE') || symbol.includes('POPCAT')) return 1;
    if (symbol.includes('BTC')) return 6;
    if (symbol.includes('ETH')) return 4;
    return 3;
  };

  // Helper to floor a number to a given precision
  const floorToPrecision = (value, precision) => {
    const factor = Math.pow(10, precision);
    return Math.floor(parseFloat(value) * factor) / factor;
  };

  // Helper to get display precision for amount label (BTC: 8, others: 2)
  const getAmountDisplayPrecision = () => {
    return 2;
  };

  // Handler for percent buttons
  const handlePercentChange = (percent) => {
    const current = parseFloat(price) || 0;
    const pricePrecision = getSymbolPrecision(symbol);
    const newPrice = current + (current * percent / 100);
    setPrice(newPrice.toFixed(pricePrecision));
    // Also update amount
    const numPredefinedVolume = parseFloat(safePredefinedVolume);
    if (newPrice > 0 && numPredefinedVolume > 0) {
      const amountPrecision = getAmountPrecision(symbol);
      const rawAmount = numPredefinedVolume / newPrice;
      const flooredAmount = floorToPrecision(rawAmount, amountPrecision);
      setAmount(flooredAmount.toFixed(amountPrecision));
    }
  };

  // Format price and amount on blur
  const handlePriceBlur = () => {
    const pricePrecision = getSymbolPrecision(symbol);
    if (price) setPrice(parseFloat(price).toFixed(pricePrecision));
  };
  const handleAmountBlur = () => {
    const amountPrecision = getAmountPrecision(symbol);
    if (amount) setAmount(floorToPrecision(amount, amountPrecision).toFixed(amountPrecision));
  };

  // Handler for form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setIsLoading(true);

    const orderDetails = {
      symbol,
      side,
      type,
      amount: parseFloat(amount) || 0,
      price: type === 'LIMIT' ? parseFloat(price) : undefined,
    };

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

    if (result && result.order_id) {
      setMessage(`Success: Order placed with ID: ${result.order_id}`);
      setPrice('');
      setAmount('');
    } else {
      setMessage(result && result.error ? `Error: ${result.error}` : 'Error: Failed to place order.');
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold mb-6 text-gray-800 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-3">
        Place Order
      </h2>

      {/* Symbol Display (no label, styled) */}
      {symbol && (
        <div className="mb-4 flex justify-center">
          <span className="inline-block px-3 py-1 rounded bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200 font-bold text-lg tracking-wide">
            {symbol}
          </span>
        </div>
      )}

      {/* Predefined Volume */}
      <div className="mb-4">
        <label htmlFor="predefinedVolume" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Predefined Volume (USDT):
        </label>
        <input
          type="number"
          id="predefinedVolume"
          value={safePredefinedVolume}
          onChange={(e) => setPredefinedVolumeUSDT(e.target.value)}
          placeholder="e.g., 100"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400"
        />
      </div>

      {/* Type Selector */}
      <div className="mb-4 flex justify-center">
        <button
          type="button"
          onClick={() => setType('LIMIT')}
          className={`flex-1 px-4 py-2 border text-sm font-medium transition-colors ${
            type === 'LIMIT' 
              ? 'bg-blue-600 text-white border-blue-600' 
              : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
          } rounded-l-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
        >
          Spot
        </button>
        <button
          type="button"
          onClick={() => { setType('MARKET'); setPrice(''); }}
          className={`flex-1 px-4 py-2 border text-sm font-medium transition-colors ml-2 ${
            type === 'MARKET' 
              ? 'bg-blue-600 text-white border-blue-600' 
              : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
          } rounded-r-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
        >
          Future
        </button>
      </div>

      {/* Price and Amount Inputs (no labels, always shown) */}
      <div className="mb-4">
        <div className="flex justify-center gap-1 mb-2">
          <button type="button" onClick={() => handlePercentChange(2)} className="text-xs px-1 py-0.5 rounded bg-green-100 text-green-700 hover:bg-green-200 min-w-[32px]">+2%</button>
          <button type="button" onClick={() => handlePercentChange(0.5)} className="text-xs px-1 py-0.5 rounded bg-green-100 text-green-700 hover:bg-green-200 min-w-[32px]">+.5%</button>
          <button type="button" onClick={() => handlePercentChange(-0.5)} className="text-xs px-1 py-0.5 rounded bg-red-100 text-red-700 hover:bg-red-200 min-w-[32px]">-.5%</button>
          <button type="button" onClick={() => handlePercentChange(-2)} className="text-xs px-1 py-0.5 rounded bg-red-100 text-red-700 hover:bg-red-200 min-w-[32px]">-2%</button>
        </div>
        <div className="relative mb-2">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none">$</span>
          <input
            type="text"
            id="price"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            onBlur={handlePriceBlur}
            placeholder="Price"
            className="w-full pl-7 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 text-center"
          />
        </div>
        <input
          type="text"
          id="amount"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          onBlur={handleAmountBlur}
          placeholder="Amount"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 text-center"
        />
        {/* Actual amount label */}
        {amount && price && (
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 text-center">
            Actual: $
            <span className="font-mono">
              {(parseFloat(amount) * parseFloat(price)).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
            </span>
          </div>
        )}
      </div>

      {/* Side Selector */}
      <div className="mb-6 flex justify-center">
        <button
          type="button"
          onClick={() => setSide('BUY')}
          className={`flex-1 px-4 py-2 border text-sm font-medium transition-colors ${
            side === 'BUY' 
              ? 'bg-green-600 text-white border-green-600' 
              : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
          } rounded-l-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500`}
        >
          Buy
        </button>
        <button
          type="button"
          onClick={() => setSide('SELL')}
          className={`flex-1 px-4 py-2 border text-sm font-medium transition-colors ml-2 ${
            side === 'SELL' 
              ? 'bg-red-600 text-white border-red-600' 
              : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
          } rounded-r-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500`}
        >
          Sell
        </button>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        onClick={handleSubmit}
        disabled={isLoading}
        className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 dark:disabled:bg-gray-500 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? 'Placing Order...' : 'Place Order'}
      </button>

      {/* Messages */}
      {message && (
        <div className={`mt-4 p-3 rounded-md text-sm ${
          message.startsWith('Success:') 
            ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800' 
            : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800'
        }`}>
          {message}
        </div>
      )}
    </div>
  );
};

export default OrderEntryForm;
