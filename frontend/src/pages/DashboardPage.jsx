import React, { useState, useEffect } from 'react';
import { getMarketOverview } from '../api/market';
import SymbolOverview from '../components/SymbolOverview.jsx';
import OrderEntryForm from '../components/OrderEntryForm.jsx'; // Import OrderEntryForm

//const MOCK_MARKET_OVERVIEW_DATA = []

const DashboardPage = () => {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // State for Order Entry Form integration
  const [selectedSymbol, setSelectedSymbol] = useState(''); // Could be e.g., 'BTCUSDT'
  const [clickedPrice, setClickedPrice] = useState(null); // Stores price from on-click actions
  const [side, setSide] = useState('BUY');
  const [predefinedVolumeUSDT, setPredefinedVolumeUSDT] = useState('100');

  const fetchData = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);
      
      const result = await getMarketOverview(); // result is expected to be an array | MOCK_MARKET_OVERVIEW_DATA;
      if (result && Array.isArray(result)) {
        setData(result); // Store the array directly
        // Set an initial selected symbol (e.g., the first one from the list)
        if (result.length > 0 && result[0].symbol && !selectedSymbol) {
          setSelectedSymbol(result[0].symbol);
        }
      } else {
        // This 'else' block will now catch cases where 'result' is null, undefined, or not an array.
        // The error message from api/market.js (if the fetch itself failed) would likely be caught by the catch block.
        // This specifically handles if getMarketOverview resolves but with invalid data.
        setError('Failed to fetch market overview data or data format is incorrect.');
      }
    } catch (err) {
      // This will catch errors from getMarketOverview (e.g., network errors)
      // or errors during the processing within the try block.
      setError(err.message || 'An unexpected error occurred while fetching data.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Handler for when a price is clicked in SymbolOverview
  const handlePriceClick = (price, symbol, sideFromClick) => {
    setClickedPrice(price);
    if (symbol) setSelectedSymbol(symbol);
    if (sideFromClick) setSide(sideFromClick.toUpperCase());
  };

  // Handler for when a symbol overview card is clicked (to set it as selected)
  const handleSymbolSelect = (symbolTicker) => {
    setSelectedSymbol(symbolTicker);
    setClickedPrice(null); // Reset clicked price when a new symbol is selected
    console.log(`Symbol selected: ${symbolTicker}`); // For debugging
  };

  // Handler for refresh button
  const handleRefresh = () => {
    fetchData(true);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-xl font-semibold text-gray-600 dark:text-gray-400">Loading market data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <div className="text-xl font-semibold text-red-600 dark:text-red-400 mb-2">Error Loading Data</div>
          <div className="text-gray-600 dark:text-gray-400 mb-6">{error}</div>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Adjust the check for 'data' to expect an array directly
  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-gray-500 text-6xl mb-4">📊</div>
          <div className="text-xl font-semibold text-gray-600 dark:text-gray-400 mb-2">No Market Data</div>
          <div className="text-gray-500 dark:text-gray-500 mb-6">No market data is currently available.</div>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-4">
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white">
              Market Dashboard
            </h1>
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="ml-4 p-2 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 hover:bg-blue-600 hover:text-white rounded transition-colors disabled:opacity-50"
              title="Refresh data"
            >
              <svg 
                className={`w-6 h-6 ${isRefreshing ? 'animate-spin' : ''}`} 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
          <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Real-time market analysis with technical indicators and support/resistance levels
          </p>
          {isRefreshing && (
            <div className="mt-4 text-sm text-blue-600 dark:text-blue-400">
              Refreshing data...
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="flex flex-col xl:flex-row gap-8">
          {/* Market Overview Section */}
          <div className="xl:w-3/4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-3">
                  Market Overview
                </h2>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {data.length} symbols loaded
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 2xl:grid-cols-3 gap-4">
                {/* 'data' is now the array, so we map over it directly */}
                {data.map((symbolData) => (
                  <div 
                    key={symbolData.symbol_id || symbolData.symbol} 
                    onClick={() => handleSymbolSelect(symbolData.symbol)}
                    className={`cursor-pointer transform transition-all duration-200 hover:scale-105 ${
                      selectedSymbol === symbolData.symbol ? 'ring-2 ring-blue-500 ring-opacity-50' : ''
                    }`}
                  >
                    <SymbolOverview
                      symbolData={symbolData}
                      onPriceClick={handlePriceClick}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Order Entry Section */}
          <div className="xl:w-1/4">
            <div className="sticky top-8">
              <OrderEntryForm
                selectedSymbol={selectedSymbol}
                clickedPrice={clickedPrice}
                side={side}
                setSide={setSide}
                predefinedVolumeUSDT={predefinedVolumeUSDT}
                setPredefinedVolumeUSDT={setPredefinedVolumeUSDT}
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-16 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>Click on any price to automatically fill the order form</p>
          <p className="mt-1">Data updates in real-time from multiple exchanges</p>
          <p className="mt-1">Last updated: {new Date().toLocaleTimeString()}</p>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
