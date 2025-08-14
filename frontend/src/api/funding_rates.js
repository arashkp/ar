/**
 * Funding Rates API helper functions.
 * 
 * This module provides functions to fetch funding rate data
 * from multiple exchanges.
 */

/**
 * Get all funding rates for all supported symbols and exchanges
 * @param {string[]} symbols - Optional array of symbols (e.g., ['BTC', 'ETH'])
 * @param {string[]} exchanges - Optional array of exchanges (e.g., ['kucoin', 'mexc'])
 * @returns {Promise<Object|null>} Funding rates data or null if error
 */
export const getAllFundingRates = async (symbols = null, exchanges = null) => {
  try {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    let url = `${apiBaseUrl}/funding-rates/`;
    const params = new URLSearchParams();
    
    if (symbols && symbols.length > 0) {
      symbols.forEach(symbol => params.append('symbols', symbol));
    }
    
    if (exchanges && exchanges.length > 0) {
      exchanges.forEach(exchange => params.append('exchanges', exchange));
    }
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    const apiKey = localStorage.getItem('apiKey');
    const headers = {};
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    
    const response = await fetch(url, { headers });
    
    if (response.ok) {
      return await response.json();
    } else {
      console.error('Error fetching all funding rates:', response.statusText);
      return null;
    }
  } catch (error) {
    console.error('Error fetching all funding rates:', error);
    return null;
  }
};

/**
 * Get funding rates for a specific symbol across all exchanges
 * @param {string} symbol - Trading symbol (e.g., 'BTC')
 * @param {string[]} exchanges - Optional array of exchanges
 * @returns {Promise<Object|null>} Funding rates for the symbol or null if error
 */
export const getSymbolFundingRates = async (symbol, exchanges = null) => {
  try {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    let url = `${apiBaseUrl}/funding-rates/${symbol}`;
    
    if (exchanges && exchanges.length > 0) {
      const params = new URLSearchParams();
      exchanges.forEach(exchange => params.append('exchanges', exchange));
      url += `?${params.toString()}`;
    }
    
    const apiKey = localStorage.getItem('apiKey');
    const headers = {};
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    
    const response = await fetch(url, { headers });
    
    if (response.ok) {
      return await response.json();
    } else {
      console.error(`Error fetching funding rates for ${symbol}:`, response.statusText);
      return null;
    }
  } catch (error) {
    console.error(`Error fetching funding rates for ${symbol}:`, error);
    return null;
  }
};

/**
 * Get funding rates for all symbols from a specific exchange
 * @param {string} exchangeId - Exchange identifier (e.g., 'kucoin')
 * @param {string[]} symbols - Optional array of symbols
 * @returns {Promise<Array|null>} Funding rates from the exchange or null if error
 */
export const getExchangeFundingRates = async (exchangeId, symbols = null) => {
  try {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    let url = `${apiBaseUrl}/funding-rates/exchange/${exchangeId}`;
    
    if (symbols && symbols.length > 0) {
      const params = new URLSearchParams();
      symbols.forEach(symbol => params.append('symbols', symbol));
      url += `?${params.toString()}`;
    }
    
    const apiKey = localStorage.getItem('apiKey');
    const headers = {};
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    
    const response = await fetch(url, { headers });
    
    if (response.ok) {
      return await response.json();
    } else {
      console.error(`Error fetching funding rates from ${exchangeId}:`, response.statusText);
      return null;
    }
  } catch (error) {
    console.error(`Error fetching funding rates from ${exchangeId}:`, error);
    return null;
  }
};

/**
 * Get custom funding rates with specific parameters
 * @param {Object} request - Request object with exchanges and symbols
 * @returns {Promise<Object|null>} Custom funding rates data or null if error
 */
export const getCustomFundingRates = async (request) => {
  try {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const url = `${apiBaseUrl}/funding-rates/custom`;
    
    const apiKey = localStorage.getItem('apiKey');
    const headers = {
      'Content-Type': 'application/json'
    };
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(request)
    });
    
    if (response.ok) {
      return await response.json();
    } else {
      console.error('Error fetching custom funding rates:', response.statusText);
      return null;
    }
  } catch (error) {
    console.error('Error fetching custom funding rates:', error);
    return null;
  }
};

/**
 * Get list of supported exchanges for funding rates
 * @returns {Promise<Object|null>} Supported exchanges or null if error
 */
export const getSupportedExchanges = async () => {
  try {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const url = `${apiBaseUrl}/funding-rates/supported/exchanges`;
    
    const apiKey = localStorage.getItem('apiKey');
    const headers = {};
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    
    const response = await fetch(url, { headers });
    
    if (response.ok) {
      return await response.json();
    } else {
      console.error('Error fetching supported exchanges:', response.statusText);
      return null;
    }
  } catch (error) {
    console.error('Error fetching supported exchanges:', error);
    return null;
  }
};

/**
 * Get list of supported symbols for funding rates
 * @returns {Promise<Object|null>} Supported symbols or null if error
 */
export const getSupportedSymbols = async () => {
  try {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const url = `${apiBaseUrl}/funding-rates/supported/symbols`;
    
    const apiKey = localStorage.getItem('apiKey');
    const headers = {};
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    
    const response = await fetch(url, { headers });
    
    if (response.ok) {
      return await response.json();
    } else {
      console.error('Error fetching supported symbols:', response.statusText);
      return null;
    }
  } catch (error) {
    console.error('Error fetching supported symbols:', error);
    return null;
  }
};
