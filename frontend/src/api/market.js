import { apiGet, formatErrorMessage } from './apiHelpers';
import axios from 'axios';

export const getMarketOverview = async () => {
  try {
    // Use axios directly with the correct base URL for this specific endpoint
    const response = await axios.get('http://localhost:8000/market/market-overview/');
    
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
