import { apiGet, formatErrorMessage } from './apiHelpers';

export const getMarketOverview = async () => {
  const response = await apiGet('/market_overview');
  
  if (response.success) {
    return response.data;
  } else {
    console.error('Error fetching market overview:', formatErrorMessage(response, 'Failed to fetch market overview'));
    return null;
  }
};
