/**
 * Historical Performance API helper functions.
 * 
 * This module provides functions to fetch historical performance data
 * calculated from OHLCV data.
 */

/**
 * Get historical performance data for specified symbols
 * @param {string[]} symbols - Array of symbols (e.g., ['BTC/USDT', 'ETH/USDT'])
 * @param {string[]} timeframes - Array of timeframes (e.g., ['7d', '14d', '1m', '3m', '6m', '1y', 'ytd'])
 * @returns {Promise<Array|null>} Historical performance data or null if error
 */
export const getHistoricalPerformance = async (symbols = null, timeframes = null) => {
  try {
    let url = 'http://localhost:8000/api/v1/historical/performance';
    const params = new URLSearchParams();
    
    if (symbols && symbols.length > 0) {
      symbols.forEach(symbol => params.append('symbols', symbol));
    }
    
    if (timeframes && timeframes.length > 0) {
      timeframes.forEach(timeframe => params.append('timeframes', timeframe));
    }
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    const response = await fetch(url);
    
    if (response.ok) {
      return await response.json();
    } else {
      console.error('Error fetching historical performance:', response.statusText);
      return null;
    }
  } catch (error) {
    console.error('Error fetching historical performance:', error);
    return null;
  }
};

/**
 * Get historical performance data for a specific symbol
 * @param {string} symbol - Trading symbol (e.g., 'BTC/USDT')
 * @param {string[]} timeframes - Array of timeframes
 * @returns {Promise<Object|null>} Performance data for the symbol or null if error
 */
export const getSymbolPerformance = async (symbol, timeframes = null) => {
  try {
    let url = `http://localhost:8000/api/v1/historical/performance/symbol/${encodeURIComponent(symbol)}`;
    
    if (timeframes && timeframes.length > 0) {
      const params = new URLSearchParams();
      timeframes.forEach(timeframe => params.append('timeframes', timeframe));
      url += `?${params.toString()}`;
    }
    
    const response = await fetch(url);
    
    if (response.ok) {
      return await response.json();
    } else {
      console.error(`Error fetching performance for ${symbol}:`, response.statusText);
      return null;
    }
  } catch (error) {
    console.error(`Error fetching performance for ${symbol}:`, error);
    return null;
  }
};

/**
 * Get supported symbols and timeframes
 * @returns {Promise<Object|null>} Supported symbols and timeframes or null if error
 */
export const getSupportedSymbolsAndTimeframes = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/v1/historical/supported');
    
    if (response.ok) {
      return await response.json();
    } else {
      console.error('Error fetching supported symbols and timeframes:', response.statusText);
      return null;
    }
  } catch (error) {
    console.error('Error fetching supported symbols and timeframes:', error);
    return null;
  }
};

/**
 * Format performance value for display
 * @param {number} value - Performance percentage
 * @returns {string} Formatted performance string
 */
export const formatPerformance = (value) => {
  if (value === null || value === undefined) return 'N/A';
  
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

/**
 * Get performance color based on value
 * @param {number} value - Performance percentage
 * @returns {string} CSS color class
 */
export const getPerformanceColor = (value) => {
  if (value === null || value === undefined) return 'text-gray-500 dark:text-gray-400';
  return value >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
};

/**
 * Get timeframe display name
 * @param {string} timeframe - Timeframe key (e.g., '7d', '1m')
 * @returns {string} Display name
 */
export const getTimeframeDisplayName = (timeframe) => {
  const displayNames = {
    '7d': '7 Days',
    '14d': '14 Days',
    '1m': '1 Month',
    '3m': '3 Months',
    '6m': '6 Months',
    '1y': '1 Year',
    'ytd': 'YTD'
  };
  
  return displayNames[timeframe] || timeframe;
};

/**
 * Format price value for display
 * @param {number} value - Price value
 * @returns {string} Formatted price string
 */
export const formatPrice = (value) => {
  if (value === null || value === undefined) return 'N/A';
  return value.toFixed(6);
}; 