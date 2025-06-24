import React, { useState, useEffect } from 'react';
import { getMarketOverview } from '../api/market';
import SymbolOverview from '../components/SymbolOverview.jsx';
import OrderEntryForm from '../components/OrderEntryForm.jsx'; // Import OrderEntryForm

const DashboardPage = () => {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for Order Entry Form integration
  const [selectedSymbol, setSelectedSymbol] = useState(''); // Could be e.g., 'BTCUSDT'
  const [clickedPrice, setClickedPrice] = useState(null); // Stores price from on-click actions

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const result = await getMarketOverview(); // result is expected to be an array
        if (result && Array.isArray(result)) {
          setData(result); // Store the array directly
          // Set an initial selected symbol (e.g., the first one from the list)
          if (result.length > 0 && result[0].symbol) {
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
      }
    };

    fetchData();
  }, []);

  // Handler for when a price is clicked in SymbolOverview
  const handlePriceClick = (price, symbol) => {
    setClickedPrice(price);
    // Updated: The symbol is now passed from the map function
    if (symbol) {
      setSelectedSymbol(symbol);
    }
    console.log(`Price clicked: ${price}, for symbol (if available): ${symbol}`); // For debugging
  };

  // Handler for when a symbol overview card is clicked (to set it as selected)
  const handleSymbolSelect = (symbolTicker) => {
    setSelectedSymbol(symbolTicker);
    setClickedPrice(null); // Reset clicked price when a new symbol is selected
    console.log(`Symbol selected: ${symbolTicker}`); // For debugging
  };


  if (isLoading) {
    return <div className="text-center py-10 text-xl font-semibold text-gray-500 dark:text-gray-400">Loading...</div>;
  }

  if (error) {
    return <div className="text-center py-10 text-xl font-semibold text-red-500 dark:text-red-400">Error: {error}</div>;
  }

  // Adjust the check for 'data' to expect an array directly
  if (!data || !Array.isArray(data) || data.length === 0) {
    return <div className="text-center py-10 text-xl font-semibold text-gray-500 dark:text-gray-400">No market data available.</div>;
  }

  return (
    <div className="container mx-auto p-4 sm:p-6 lg:p-8">
      <h1 className="text-3xl sm:text-4xl font-bold text-center mb-8 sm:mb-12 text-gray-800 dark:text-gray-100">
        Market Dashboard
      </h1>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Symbols Overview Section */}
        <div className="lg:w-3/4">
          <h2 className="text-2xl font-semibold mb-6 text-gray-700 dark:text-gray-200">Market Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-6">
            {/* 'data' is now the array, so we map over it directly */}
            {data.map((symbolData) => (
              <div key={symbolData.symbol_id || symbolData.symbol} onClick={() => handleSymbolSelect(symbolData.symbol)}>
                <SymbolOverview
                  symbolData={symbolData}
                  onPriceClick={(price) => handlePriceClick(price, symbolData.symbol)} // Pass symbol context here
                />
              </div>
            ))}
          </div>
        </div>

        {/* Order Entry Section */}
        <div className="lg:w-1/4">
          <h2 className="text-2xl font-semibold mb-6 text-gray-700 dark:text-gray-200">Order Entry</h2>
          <div className="sticky top-6"> {/* Make form sticky on larger screens */}
            <OrderEntryForm
              selectedSymbol={selectedSymbol}
              clickedPrice={clickedPrice}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
