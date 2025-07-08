import React, { useState, useEffect } from 'react';
import { getMarketOverview } from '../api/market';
import SymbolOverview from '../components/SymbolOverview.jsx';
import OrderEntryForm from '../components/OrderEntryForm.jsx'; // Import OrderEntryForm
import LLMPromptGenerator from '../components/LLMPromptGenerator.jsx'; // Import LLM Prompt Generator
import DCAAnalysisSummary from '../components/DCAAnalysisSummary.jsx'; // Import DCA Analysis Summary
import HistoricalPerformance from '../components/HistoricalPerformance.jsx'; // Import Historical Performance
import ThemeToggleButton from '../components/ThemeToggleButton.jsx'; // Import Theme Toggle

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
  
  // State for LLM Prompt Generator
  const [selectedSymbolData, setSelectedSymbolData] = useState(null);
  const [showLLMPrompt, setShowLLMPrompt] = useState(false);
  
  // State for Order Form Toggle
  const [showOrderForm, setShowOrderForm] = useState(false);

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

  // Handler for when a symbol card is clicked to show LLM prompt
  const handleSymbolClick = (symbolData) => {
    setSelectedSymbolData(symbolData);
    setShowLLMPrompt(true);
  };

  // Handler to close LLM prompt
  const handleCloseLLMPrompt = () => {
    setShowLLMPrompt(false);
    setSelectedSymbolData(null);
  };

  // Handler for refresh button
  const handleRefresh = () => {
    fetchData(true);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center w-full px-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-xl font-semibold text-gray-600 dark:text-gray-400">Loading market data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center w-full max-w-md mx-auto p-6">
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
        <div className="text-center w-full max-w-md mx-auto p-6">
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 w-screen">
      <div className="w-full max-w-none px-0 py-6">
        {/* Centered Header */}
        <div className="flex flex-col items-center justify-center mb-8 w-full">
          <div className="flex flex-row items-center justify-center space-x-4 w-full">
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white text-center">Market Dashboard</h1>
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="p-2 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 hover:bg-blue-600 hover:text-white rounded transition-colors disabled:opacity-50"
              title="Refresh data"
            >
              <svg className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button
              onClick={() => setShowOrderForm(!showOrderForm)}
              className={`p-2 rounded-lg transition-colors ${
                showOrderForm 
                  ? 'bg-green-600 text-white hover:bg-green-700' 
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
              title={showOrderForm ? 'Hide Order Form' : 'Show Order Form'}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </button>
            {/* Icon-only theme toggle */}
            <ThemeToggleButton iconOnly buttonClassName={`p-2 rounded-lg transition-colors bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600`} />
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-4 text-center">
            Real-time market analysis with enhanced volume indicators and DCA strategy insights
          </p>
          {isRefreshing && (
            <div className="mt-2 text-sm text-blue-600 dark:text-blue-400 text-center">
              Refreshing data...
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Market Overview Section */}
          <div className={`${showOrderForm ? 'lg:w-2/3' : 'w-full'}`}>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-3">
                  Market Overview
                </h2>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {data.length} symbols loaded
                </div>
              </div>
              
              {/* Optimized Grid: 6 per row on desktop, 2 per row on mobile */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
                {data.map((symbolData) => (
                  <div 
                    key={symbolData.symbol_id || symbolData.symbol} 
                    className={`transform transition-all duration-200 hover:scale-105 ${
                      selectedSymbol === symbolData.symbol ? 'ring-2 ring-blue-500 ring-opacity-50' : ''
                    }`}
                  >
                    <SymbolOverview
                      symbolData={symbolData}
                      onPriceClick={handlePriceClick}
                      onSymbolClick={handleSymbolClick}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* DCA Analysis Summary */}
            <DCAAnalysisSummary marketData={data} />
            
            {/* Historical Performance Section */}
            <HistoricalPerformance selectedSymbol={selectedSymbol} />
          </div>

          {/* Order Entry Section - Conditional */}
          {showOrderForm && (
            <div className="lg:w-1/3">
              <div className="sticky top-6">
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
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>Click on any symbol card to generate LLM prompts for DCA strategy</p>
          <p className="mt-1">Click on any price to automatically fill the order form</p>
          <p className="mt-1">Data updates in real-time from multiple exchanges</p>
          <p className="mt-1">Last updated: {new Date().toLocaleTimeString()}</p>
        </div>

        {/* Metrics Explained Section */}
        <div className="w-full max-w-5xl mx-auto mt-8">
          <details className="bg-gray-100 dark:bg-gray-800 rounded-lg shadow p-4 cursor-pointer select-none" closed>
            <summary className="font-semibold text-lg text-gray-800 dark:text-gray-200 mb-2">Metrics Explained</summary>
            <ul className="list-disc list-inside space-y-2 text-gray-700 dark:text-gray-300 text-sm mt-2">
              <li><b>Vol:</b> <span>Relative trading volume compared to the recent average. <b>Ranges:</b> <span className="text-green-600">very high</span> (&gt;2.0x), <span className="text-blue-600">high</span> (&gt;1.2x), <span className="text-gray-600">normal</span> (0.5x-1.2x), <span className="text-red-600">low</span> (&lt;0.5x).</span></li>
              <li><b>Trend:</b> <span>5-period average of volume ratio. <b>Ranges:</b> <span className="text-green-600">Uptrend</span> (&gt;1.3x), <span className="text-red-600">Downtrend</span> (&lt;0.7x), <span className="text-gray-600">Sideways</span> (0.7x-1.3x).</span></li>
              <li><b>RSI:</b> <span>Relative Strength Index (14-period). <b>Ranges:</b> <span className="text-green-600">Oversold</span> (&lt;30), <span className="text-blue-600">Potential Buy</span> (30-40), <span className="text-gray-600">Neutral</span> (40-70), <span className="text-red-600">Overbought</span> (&gt;70).</span></li>
              <li><b>Conf:</b> <span>Confidence score for the DCA signal (0-100%).</span></li>
              <li><b>Amt:</b> <span>DCA amount multiplier (e.g., 1.10x means increase position size by 10%).</span></li>
              <li><b>Sent:</b> <span>Market sentiment: <span className="text-green-600">Bullish</span>, <span className="text-red-600">Bearish</span>, or <span className="text-gray-600">Neutral</span>.</span></li>
            </ul>
          </details>
        </div>
      </div>

      {/* LLM Prompt Generator Modal */}
      {showLLMPrompt && (
        <LLMPromptGenerator
          selectedSymbol={selectedSymbolData}
          onClose={handleCloseLLMPrompt}
        />
      )}
    </div>
  );
};

export default DashboardPage;

