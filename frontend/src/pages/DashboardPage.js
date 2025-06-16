import React, { useState, useEffect } from 'react';
import { getMarketOverview } from '../api/market';
import SymbolOverview from '../components/SymbolOverview'; // Import SymbolOverview

const DashboardPage = () => {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const result = await getMarketOverview();
        // Ensure the result itself is not null and contains the expected 'symbols' array.
        if (result && result.symbols && Array.isArray(result.symbols)) {
          setData(result);
        } else {
          // Handle cases where the API returns null, undefined, or not the expected structure.
          setError('Failed to fetch market overview data or data format is incorrect.');
        }
      } catch (err) {
        setError(err.message || 'An unexpected error occurred.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []); // Empty dependency array means this effect runs once on mount

  if (isLoading) {
    return <div className="text-center py-10 text-xl font-semibold text-gray-500 dark:text-gray-400">Loading...</div>;
  }

  if (error) {
    return <div className="text-center py-10 text-xl font-semibold text-red-500 dark:text-red-400">Error: {error}</div>;
  }

  // Check if data itself or data.symbols is null/undefined or not an array
  if (!data || !data.symbols || !Array.isArray(data.symbols) || data.symbols.length === 0) {
    // This handles cases where data is null, data.symbols is null/undefined/not an array, or symbols array is empty.
    // It can be shown even if there's no error, e.g. API returns an empty symbols list.
    return <div className="text-center py-10 text-xl font-semibold text-gray-500 dark:text-gray-400">No market data available or data is not in the expected format.</div>;
  }

  return (
    <div className="container mx-auto p-4 sm:p-6 lg:p-8">
      <h1 className="text-3xl sm:text-4xl font-bold text-center mb-8 sm:mb-12 text-gray-800 dark:text-gray-100">
        Market Overview
      </h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
        {data.symbols.map((symbolData, index) => (
          // Assuming symbolData has a unique 'symbol_id' or use index as a fallback key.
          // It's better if the API provides a stable unique ID for each symbol.
          <SymbolOverview key={symbolData.symbol_id || `symbol-${index}`} symbolData={symbolData} />
        ))}
      </div>
    </div>
  );
};

export default DashboardPage;
