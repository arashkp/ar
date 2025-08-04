import { apiGet, formatErrorMessage, wakeUpBackend } from './apiHelpers';
import axios from 'axios';

export const getMarketOverview = async () => {
  try {
    // Wake up the backend first
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    await wakeUpBackend(apiBaseUrl);
    
    // Use axios directly with the correct base URL for this specific endpoint
    const apiKey = localStorage.getItem('apiKey');
    const headers = {};
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    
    const response = await axios.get(`${apiBaseUrl}/market/market-overview/`, { 
      headers,
      timeout: 120000 // 2 minutes timeout for Render wake-up
    });
    
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
