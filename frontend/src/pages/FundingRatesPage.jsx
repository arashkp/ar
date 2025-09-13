import React, { useState, useEffect } from 'react';
import { 
  getAllFundingRates, 
  getSymbolFundingRates, 
  getExchangeFundingRates, 
  getCustomFundingRates,
  getSupportedExchanges,
  getSupportedSymbols
} from '../api/funding_rates';

const FundingRatesPage = () => {
  const [fundingRates, setFundingRates] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: 'symbol', direction: 'asc' });

  // Fetch funding rates data
  const fetchFundingRates = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await getAllFundingRates();
      
      if (data) {
        setFundingRates(data);
        setLastUpdated(data.last_updated);
      } else {
        setError('Failed to fetch funding rates data');
      }
    } catch (error) {
      console.error('Error fetching funding rates:', error);
      setError('Error fetching funding rates data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFundingRates();
  }, []);

  // Transform data for matrix display
  const transformDataForMatrix = () => {
    if (!fundingRates?.rates) return { symbols: [], exchanges: [], matrix: {} };

    const exchanges = new Set();
    const symbols = new Set();
    const matrix = {};

    // First pass: collect all exchanges and symbols
    fundingRates.rates.forEach(symbolData => {
      // Extract base symbol (remove USDT suffix and handle special cases)
      let baseSymbol = symbolData.symbol.replace('USDT', '');
      
      // Handle Bitunix special cases (e.g., 1000PEPEUSDT -> PEPE)
      if (baseSymbol.startsWith('1000')) {
        baseSymbol = baseSymbol.substring(4); // Remove '1000' prefix
      }
      
      symbols.add(baseSymbol);
      symbolData.rates.forEach(rate => {
        // Normalize exchange names to lowercase for consistency
        exchanges.add(rate.exchange.toLowerCase());
      });
    });

    const exchangesList = Array.from(exchanges).sort();
    const symbolsList = Array.from(symbols).sort();

    // Second pass: build the matrix
    symbolsList.forEach(symbol => {
      matrix[symbol] = {};
      exchangesList.forEach(exchange => {
        matrix[symbol][exchange] = null;
      });
    });

    // Third pass: fill in the data
    fundingRates.rates.forEach(symbolData => {
      // Extract base symbol (remove USDT suffix and handle special cases)
      let baseSymbol = symbolData.symbol.replace('USDT', '');
      
      // Handle Bitunix special cases (e.g., 1000PEPEUSDT -> PEPE)
      if (baseSymbol.startsWith('1000')) {
        baseSymbol = baseSymbol.substring(4); // Remove '1000' prefix
      }
      
      symbolData.rates.forEach(rate => {
        // Normalize exchange name to lowercase
        const normalizedExchange = rate.exchange.toLowerCase();
        if (matrix[baseSymbol] && matrix[baseSymbol][normalizedExchange] === null) {
          matrix[baseSymbol][normalizedExchange] = {
            funding_rate: rate.funding_rate,
            price: rate.mark_price || rate.last_price || null
          };
        }
      });
    });

    return {
      symbols: symbolsList,
      exchanges: exchangesList,
      matrix: matrix
    };
  };

  // Sort symbols
  const sortSymbols = (symbols, matrix) => {
    if (!sortConfig.key) return symbols;

    return [...symbols].sort((a, b) => {
      if (sortConfig.key === 'symbol') {
        if (sortConfig.direction === 'asc') {
          return a.localeCompare(b);
        } else {
          return b.localeCompare(a);
        }
      }
      
      // Sort by funding rate of a specific exchange
      const exchange = sortConfig.key;
      const aRate = matrix?.[a]?.[exchange]?.funding_rate || 0;
      const bRate = matrix?.[b]?.[exchange]?.funding_rate || 0;
      
      if (sortConfig.direction === 'asc') {
        return aRate - bRate;
      } else {
        return bRate - aRate;
      }
    });
  };

  // Handle sorting
  const handleSort = (key) => {
    setSortConfig(prevConfig => ({
      key,
      direction: prevConfig.key === key && prevConfig.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  // Get sort indicator
  const getSortIndicator = (key) => {
    if (sortConfig.key !== key) return '↕️';
    return sortConfig.direction === 'asc' ? '↑' : '↓';
  };

  // Format funding rate
  const formatFundingRate = (rate) => {
    if (rate === null || rate === undefined) return 'N/A';
    return `${rate.toFixed(4)}%`;
  };

  // Format price
  const formatPrice = (price) => {
    if (price === null || price === undefined) return '';
    return `$${parseFloat(price).toLocaleString()}`;
  };

  // Get rate color based on value
  const getRateColor = (rate) => {
    if (rate === null || rate === undefined) return 'text-gray-400';
    if (rate > 0) return 'text-green-600 dark:text-green-400';
    if (rate < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  // Format exchange name for display
  const formatExchangeName = (exchange) => {
    return exchange.charAt(0).toUpperCase() + exchange.slice(1);
  };

  // Transform and process data
  const data = transformDataForMatrix();
  const sortedSymbols = sortSymbols(data.symbols, data.matrix);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading funding rates...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="bg-red-100 dark:bg-red-900 border border-red-400 text-red-700 dark:text-red-300 px-4 py-3 rounded">
              <p className="font-medium">Error: {error}</p>
              <button
                onClick={fetchFundingRates}
                className="mt-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Funding Rates Matrix
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Compare funding rates across exchanges. Click column headers to sort by exchange rates.
          </p>
          {lastUpdated && (
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
              Last updated: {new Date(lastUpdated).toLocaleString()}
            </p>
          )}
        </div>

        {/* Refresh Button */}
        <div className="mb-6 text-center">
          <button
            onClick={fetchFundingRates}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
          >
            Refresh Data
          </button>
        </div>

        {/* Results Summary */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
          <div className="text-center">
            <p className="text-gray-600 dark:text-gray-400">
              Showing <span className="font-semibold">{data.symbols.length}</span> symbols across <span className="font-semibold">{data.exchanges.length}</span> exchanges
            </p>
          </div>
        </div>

        {/* Funding Rates Matrix */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600" onClick={() => handleSort('symbol')}>
                    Symbol {getSortIndicator('symbol')}
                  </th>
                  {data.exchanges.map(exchange => (
                    <th 
                      key={exchange}
                      className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
                      onClick={() => handleSort(exchange)}
                    >
                      {formatExchangeName(exchange)} {getSortIndicator(exchange)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {sortedSymbols.map(symbol => (
                  <tr key={symbol} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {symbol}
                      </div>
                    </td>
                    {data.exchanges.map(exchange => {
                      const cellData = data.matrix[symbol]?.[exchange];
                      return (
                        <td key={exchange} className="px-6 py-4 whitespace-nowrap">
                          {cellData ? (
                            <div className="text-center">
                              <div className={`text-lg font-bold ${getRateColor(cellData.funding_rate)}`}>
                                {formatFundingRate(cellData.funding_rate)}
                              </div>
                              {cellData.price && (
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                  {formatPrice(cellData.price)}
                                </div>
                              )}
                            </div>
                          ) : (
                            <div className="text-center text-gray-400 text-sm">
                              N/A
                            </div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Empty State */}
        {data.symbols.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500 dark:text-gray-400">
              No funding rates found.
            </p>
          </div>
        )}

        {/* Legend */}
        <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="text-center">
            <div className="inline-flex items-center space-x-6 text-sm text-gray-600 dark:text-gray-400">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span>Positive Rate (Long pays Short)</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span>Negative Rate (Short pays Long)</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                <span>Zero Rate</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FundingRatesPage;
