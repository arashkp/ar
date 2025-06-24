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
        const result = await getMarketOverview();
        if (result && result.symbols && Array.isArray(result.symbols)) {
          setData(result);
          // Set an initial selected symbol (e.g., the first one from the list)
          if (result.symbols.length > 0 && result.symbols[0].symbol) {
            setSelectedSymbol(result.symbols[0].symbol);
          }
        } else {
          setError('Failed to fetch market overview data or data format is incorrect.');
        }
      } catch (err) {
        setError(err.message || 'An unexpected error occurred.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Handler for when a price is clicked in SymbolOverview
  const handlePriceClick = (price, symbol) => {
    setClickedPrice(price);
    // Optionally, update selectedSymbol if the click is associated with a specific symbol
    // For now, SymbolOverview doesn't pass its symbol on click, but it could be enhanced.
    // If SymbolOverview were to pass its symbol: setSelectedSymbol(symbol);
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

  if (!data || !data.symbols || !Array.isArray(data.symbols) || data.symbols.length === 0) {
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
            {data.symbols.map((symbolData) => (
              // Enhance SymbolOverview to pass its own symbol on click if needed for context
              // For now, handlePriceClick might not know which symbol's price was clicked unless SymbolOverview is modified
              // Or, we can pass a partially applied function: onPriceClick={(price) => handlePriceClick(price, symbolData.symbol)}
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
