/**
 * API Helper utilities for the AR trading application frontend.
 * 
 * This module provides centralized functions for API calls, error handling,
 * and response processing to reduce code duplication across API modules.
 */

import axios from 'axios';

// Default API configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const DEFAULT_RETRY_ATTEMPTS = 3;
const DEFAULT_RETRY_DELAY = 1000; // 1 second

// Create axios instance with default configuration
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: DEFAULT_TIMEOUT,
    headers: {
        'Content-Type': 'application/json',
    },
});

/**
 * Custom error class for API errors
 */
class APIError extends Error {
    constructor(message, status, data = null) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }
}

/**
 * Handle API response and extract data or throw appropriate error
 * 
 * @param {Object} response - Axios response object
 * @returns {Object} Response data
 * @throws {APIError} If response indicates an error
 */
function handleResponse(response) {
    if (response.status >= 200 && response.status < 300) {
        return response.data;
    }
    
    throw new APIError(
        response.data?.detail || response.statusText || 'Unknown error',
        response.status,
        response.data
    );
}

/**
 * Handle API errors and provide user-friendly error messages
 * 
 * @param {Error} error - The error object
 * @param {string} operation - Description of the operation being performed
 * @returns {Object} Error object with user-friendly message
 */
function handleError(error, operation = 'API operation') {
    console.error(`Error during ${operation}:`, error);
    
    if (error instanceof APIError) {
        return {
            success: false,
            error: error.message,
            status: error.status,
            data: error.data,
        };
    }
    
    if (error.response) {
        // Server responded with error status
        const status = error.response.status;
        const data = error.response.data;
        
        let message = 'An error occurred';
        if (data?.detail) {
            message = data.detail;
        } else if (data?.message) {
            message = data.message;
        } else {
            switch (status) {
                case 400:
                    message = 'Invalid request';
                    break;
                case 401:
                    message = 'Authentication required';
                    break;
                case 403:
                    message = 'Access denied';
                    break;
                case 404:
                    message = 'Resource not found';
                    break;
                case 429:
                    message = 'Too many requests. Please try again later.';
                    break;
                case 500:
                    message = 'Server error. Please try again later.';
                    break;
                default:
                    message = `Server error (${status})`;
            }
        }
        
        return {
            success: false,
            error: message,
            status: status,
            data: data,
        };
    } else if (error.request) {
        // Network error
        return {
            success: false,
            error: 'Network error. Please check your connection and try again.',
            status: null,
            data: null,
        };
    } else {
        // Other error
        return {
            success: false,
            error: error.message || 'An unexpected error occurred',
            status: null,
            data: null,
        };
    }
}

/**
 * Retry function for failed API calls
 * 
 * @param {Function} fn - Function to retry
 * @param {number} attempts - Number of retry attempts
 * @param {number} delay - Delay between retries in milliseconds
 * @returns {Promise} Promise that resolves with function result or rejects with error
 */
async function retry(fn, attempts = DEFAULT_RETRY_ATTEMPTS, delay = DEFAULT_RETRY_DELAY) {
    for (let i = 0; i < attempts; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === attempts - 1) {
                throw error;
            }
            
            // Don't retry on client errors (4xx)
            if (error.response && error.response.status >= 400 && error.response.status < 500) {
                throw error;
            }
            
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, delay * (i + 1)));
        }
    }
}

/**
 * Generic GET request helper
 * 
 * @param {string} endpoint - API endpoint
 * @param {Object} params - Query parameters
 * @param {Object} options - Additional options
 * @returns {Promise<Object>} Promise that resolves with response data or error object
 */
export async function apiGet(endpoint, params = {}, options = {}) {
    const { retryAttempts = DEFAULT_RETRY_ATTEMPTS, retryDelay = DEFAULT_RETRY_DELAY } = options;
    
    try {
        const response = await retry(
            () => apiClient.get(endpoint, { params }),
            retryAttempts,
            retryDelay
        );
        return { success: true, data: handleResponse(response) };
    } catch (error) {
        return handleError(error, `GET ${endpoint}`);
    }
}

/**
 * Generic POST request helper
 * 
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request body data
 * @param {Object} options - Additional options
 * @returns {Promise<Object>} Promise that resolves with response data or error object
 */
export async function apiPost(endpoint, data = {}, options = {}) {
    const { retryAttempts = DEFAULT_RETRY_ATTEMPTS, retryDelay = DEFAULT_RETRY_DELAY } = options;
    
    try {
        const response = await retry(
            () => apiClient.post(endpoint, data),
            retryAttempts,
            retryDelay
        );
        return { success: true, data: handleResponse(response) };
    } catch (error) {
        return handleError(error, `POST ${endpoint}`);
    }
}

/**
 * Generic PUT request helper
 * 
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request body data
 * @param {Object} options - Additional options
 * @returns {Promise<Object>} Promise that resolves with response data or error object
 */
export async function apiPut(endpoint, data = {}, options = {}) {
    const { retryAttempts = DEFAULT_RETRY_ATTEMPTS, retryDelay = DEFAULT_RETRY_DELAY } = options;
    
    try {
        const response = await retry(
            () => apiClient.put(endpoint, data),
            retryAttempts,
            retryDelay
        );
        return { success: true, data: handleResponse(response) };
    } catch (error) {
        return handleError(error, `PUT ${endpoint}`);
    }
}

/**
 * Generic DELETE request helper
 * 
 * @param {string} endpoint - API endpoint
 * @param {Object} options - Additional options
 * @returns {Promise<Object>} Promise that resolves with response data or error object
 */
export async function apiDelete(endpoint, options = {}) {
    const { retryAttempts = DEFAULT_RETRY_ATTEMPTS, retryDelay = DEFAULT_RETRY_DELAY } = options;
    
    try {
        const response = await retry(
            () => apiClient.delete(endpoint),
            retryAttempts,
            retryDelay
        );
        return { success: true, data: handleResponse(response) };
    } catch (error) {
        return handleError(error, `DELETE ${endpoint}`);
    }
}

/**
 * Validate required fields in an object
 * 
 * @param {Object} data - Object to validate
 * @param {Array<string>} requiredFields - Array of required field names
 * @param {string} operation - Description of the operation for error messages
 * @returns {Object} Validation result with success flag and error message if applicable
 */
export function validateRequiredFields(data, requiredFields, operation = 'operation') {
    const missingFields = requiredFields.filter(field => !data[field]);
    
    if (missingFields.length > 0) {
        return {
            success: false,
            error: `Missing required fields for ${operation}: ${missingFields.join(', ')}`,
        };
    }
    
    return { success: true };
}

/**
 * Validate that a value is a positive number
 * 
 * @param {any} value - Value to validate
 * @param {string} fieldName - Name of the field for error messages
 * @param {string} operation - Description of the operation for error messages
 * @returns {Object} Validation result with success flag and error message if applicable
 */
export function validatePositiveNumber(value, fieldName, operation = 'operation') {
    const numValue = parseFloat(value);
    
    if (isNaN(numValue)) {
        return {
            success: false,
            error: `${fieldName} must be a valid number for ${operation}`,
        };
    }
    
    if (numValue <= 0) {
        return {
            success: false,
            error: `${fieldName} must be a positive number for ${operation}`,
        };
    }
    
    return { success: true };
}

/**
 * Format error message for display
 * 
 * @param {Object} errorResult - Error result from API call
 * @param {string} defaultMessage - Default message if no specific error
 * @returns {string} Formatted error message
 */
export function formatErrorMessage(errorResult, defaultMessage = 'An error occurred') {
    if (!errorResult || !errorResult.error) {
        return defaultMessage;
    }
    
    return errorResult.error;
}

/**
 * Check if an API response indicates success
 * 
 * @param {Object} response - API response object
 * @returns {boolean} True if response indicates success
 */
export function isSuccessResponse(response) {
    return response && response.success === true;
}

/**
 * Extract data from successful API response
 * 
 * @param {Object} response - API response object
 * @returns {any} Response data or null if not successful
 */
export function extractData(response) {
    return isSuccessResponse(response) ? response.data : null;
}

/**
 * Set API base URL (useful for different environments)
 * 
 * @param {string} baseURL - New base URL
 */
export function setApiBaseURL(baseURL) {
    apiClient.defaults.baseURL = baseURL;
}

/**
 * Set default timeout for API requests
 * 
 * @param {number} timeout - Timeout in milliseconds
 */
export function setApiTimeout(timeout) {
    apiClient.defaults.timeout = timeout;
}

/**
 * Add request interceptor for authentication, logging, etc.
 * 
 * @param {Function} interceptor - Interceptor function
 */
export function addRequestInterceptor(interceptor) {
    apiClient.interceptors.request.use(interceptor);
}

/**
 * Add response interceptor for logging, error handling, etc.
 * 
 * @param {Function} interceptor - Interceptor function
 */
export function addResponseInterceptor(interceptor) {
    apiClient.interceptors.response.use(interceptor);
}

// Export the API client for direct use if needed
export { apiClient }; 