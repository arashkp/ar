import React, { useState } from 'react';
import { useTheme } from '../context/ThemeContext';
import {
  getHistoricalPerformance,
  getPerformanceColor,
  getTimeframeDisplayName
} from '../api/historical';

// Helper for price formatting with a thousand separators and precision
const getSymbolPrecision = (symbol) => {
  if (!symbol) return 2;
  if (symbol.includes('DOGE') || symbol.includes('POPCAT')) return 4;
  if (symbol.includes('PEPE')) return 6;  // PEPE needs high precision (6 decimal places)
  if (symbol.includes('BTC')) return 0;
  if (symbol.includes('ETH')) return 1;
  return 2;
};
const formatPrice = (value, symbol) => {
  if (value === null || value === undefined) return 'N/A';
  const precision = getSymbolPrecision(symbol);
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: precision, maximumFractionDigits: precision });
};

const formatPercent = (value) => {
  if (value === null || value === undefined) return 'N/A';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

// Move 1y to the end
const TIMEFRAMES = ['7d', '14d', '1m', '3m', '6m', 'ytd', '1y'];

const HistoricalPerformance = () => {
  const { } = useTheme();
  const [performanceData, setPerformanceData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  const fetchPerformanceData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getHistoricalPerformance(null, TIMEFRAMES);
      if (data) {
        setPerformanceData(data);
        setLastUpdated(data[0]?.last_updated || new Date().toISOString());
      } else {
        setError('Failed to fetch performance data');
      }
    } catch (err) {
      setError(err.message || 'An error occurred while fetching data');
    } finally {
      setLoading(false);
    }
  };

  // Sorting function
  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  // Sort data based on current sort configuration
  const sortedData = React.useMemo(() => {
    if (!sortConfig.key) return performanceData;

    return [...performanceData].sort((a, b) => {
      let aValue, bValue;

      if (sortConfig.key === 'symbol') {
        aValue = a.symbol;
        bValue = b.symbol;
      } else {
        // For timeframe columns, sort by performance value
        aValue = a.performance?.[sortConfig.key] ?? 0;
        bValue = b.performance?.[sortConfig.key] ?? 0;
      }

      if (aValue < bValue) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
  }, [performanceData, sortConfig]);

  // Helper to render sort indicator
  const renderSortIndicator = (key) => {
    if (sortConfig.key !== key) {
      return <span className="text-gray-400">↕</span>;
    }
    return sortConfig.direction === 'asc' ? <span className="text-blue-500">↑</span> : <span className="text-blue-500">↓</span>;
  };

  // Helper to render a cell for a timeframe
  const renderTimeframeCell = (item, timeframe) => {
    const value = item.performance?.[timeframe];
    const high = item.highs?.[timeframe];
    const low = item.lows?.[timeframe];
    const current = item.current_prices?.[timeframe];
    const symbol = item.symbol;
    // % from low: (current-low)/(high-low) * 100
    let pctFromLow = null, pctFromHigh = null;
    if (current != null && high != null && low != null && high !== low) {
      pctFromLow = ((current - low) / (high - low)) * 100;
      pctFromHigh = ((high - current) / (high - low)) * 100;
    }
    
    // Add gray background for 1y column
    const is1yColumn = timeframe === '1y';
    return (
      <td key={timeframe} className={`px-2 py-2 text-center align-middle whitespace-nowrap group`}>
        <div className={`text-sm font-semibold ${getPerformanceColor(value)}`}>{formatPercent(value)}</div>
        <div className="flex flex-col items-center gap-0.5">
          <span className={`text-xs text-gray-500`} title={`High: ${formatPrice(high, symbol)}`}>H: {formatPrice(high, symbol)}
            {pctFromHigh != null && (
              <span className="ml-1 text-[10px] font-normal" title={`Current is -${Math.abs(pctFromHigh).toFixed(1)}% below high`}>
                (-{Math.abs(pctFromHigh).toFixed(1)}%)
              </span>
            )}
          </span>
          <span className={`text-xs text-gray-500`} title={`Low: ${formatPrice(low, symbol)}`}>L: {formatPrice(low, symbol)}
            {pctFromLow != null && (
              <span className="ml-1 text-[10px] font-normal" title={`Current is +${Math.abs(pctFromLow).toFixed(1)}% above low`}>
                (+{Math.abs(pctFromLow).toFixed(1)}%)
              </span>
            )}
          </span>
        </div>
      </td>
    );
  };

  return (
    <div className="space-y-4 mt-8">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-200">Historical Performance</h3>
          <button
            onClick={fetchPerformanceData}
            disabled={loading}
            className={`p-2 rounded-full bg-transparent transition-colors ${loading ? 'text-gray-500 cursor-not-allowed' : 'hover:bg-gray-200 dark:hover:bg-gray-700'}`}
            title="Refresh Data"
            aria-label="Refresh Data"
          >
            {loading ? (
              <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
          </button>
        </div>
        {error && (
          <div className={`px-6 py-2 text-sm text-red-600`}>{error}</div>
        )}
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs md:text-sm bg-white dark:bg-gray-800">
            <thead className="dark:bg-gray-700 sticky top-0 z-10 shadow-sm">
              <tr>
                <th 
                  className="px-2 py-3 text-left font-bold uppercase tracking-wider text-gray-500 dark:text-gray-300 cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  onClick={() => handleSort('symbol')}
                >
                  <div className="flex items-center gap-1">
                    Symbol {renderSortIndicator('symbol')}
                  </div>
                </th>
                {TIMEFRAMES.map(tf => (
                  <th 
                    key={tf} 
                    className={`px-2 py-3 text-center font-bold uppercase tracking-wider text-gray-500 dark:text-gray-300 cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors`}
                    onClick={() => handleSort(tf)}
                  >
                    <div className="flex items-center justify-center gap-1">
                      {getTimeframeDisplayName(tf)} {renderSortIndicator(tf)}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {sortedData.map(item => (
                <tr key={item.symbol} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-2 py-2 font-medium text-gray-900 dark:text-gray-200">{item.symbol}</td>
                  {TIMEFRAMES.map(tf => renderTimeframeCell(item, tf))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {performanceData.length > 0 && (
          <div className={`px-6 py-2 text-xs text-right text-gray-500`}>Last updated: {new Date(lastUpdated).toLocaleTimeString()}</div>
        )}
      </div>
    </div>
  );
};

export default HistoricalPerformance; 