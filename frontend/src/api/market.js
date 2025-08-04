import { apiGet, formatErrorMessage } from './apiHelpers';
import axios from 'axios';

export const getMarketOverview = async () => {
  try {
    // Use axios directly with the correct base URL for this specific endpoint
    const apiKey = localStorage.getItem('apiKey');
    const headers = {};
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const response = await axios.get(`${apiBaseUrl}/market/market-overview/`, { headers });
    
    if (response.status >= 200 && response.status < 300) {
      return response.data;
    } else {
      console.error('Error fetching market overview:', 'Failed to fetch market overview');
      return null;
    }
  } catch (error) {
    console.error('Error fetching market overview:', formatErrorMessage(
      { error: error.message || 'Network error' }, 
      'Failed to fetch market overview'
    ));
    return null;
  }
};
