import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export const getMarketOverview = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/market_overview`);
    return response.data;
  } catch (error) {
    console.error('Error fetching market overview:', error);
    // In a real application, you might want to throw the error or return a specific error object.
    return null;
  }
};
