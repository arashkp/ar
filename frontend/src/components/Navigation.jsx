import React, { useContext } from 'react';
import { ThemeContext } from '../context/ThemeContext.jsx';

const Navigation = ({ currentPage, onPageChange, onLogout }) => {
  const { theme, toggleTheme } = useContext(ThemeContext);
  
  return (
    <nav className="w-full bg-white dark:bg-gray-800 shadow-md border-b border-gray-200 dark:border-gray-700">
      <div className="w-full px-2 sm:px-4 lg:px-8">
        <div className="flex justify-between items-center h-12 sm:h-16">
          <div className="flex items-center space-x-2 sm:space-x-4">
            <h1 className="text-sm sm:text-lg lg:text-xl font-bold text-gray-900 dark:text-white truncate">
              Crypto Dashboard
            </h1>
            <div className="flex space-x-1 sm:space-x-2 lg:space-x-4">
              <button
                onClick={() => onPageChange('dashboard')}
                className={`px-1 py-0.5 sm:px-2 sm:py-1 lg:px-3 lg:py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                  currentPage === 'dashboard'
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                <span className="hidden sm:inline">DCA Strategy</span>
                <span className="sm:hidden">DCA</span>
              </button>
              <button
                onClick={() => onPageChange('asset-overview')}
                className={`px-1 py-0.5 sm:px-2 sm:py-1 lg:px-3 lg:py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                  currentPage === 'asset-overview'
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                <span className="hidden sm:inline">Asset Overview</span>
                <span className="sm:hidden">Overview</span>
              </button>
              <button
                onClick={() => onPageChange('telegram')}
                className={`px-1 py-0.5 sm:px-2 sm:py-1 lg:px-3 lg:py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                  currentPage === 'telegram'
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                <span className="hidden sm:inline">🤖 Telegram</span>
                <span className="sm:hidden">Telegram</span>
              </button>
              <button
                onClick={() => onPageChange('funding-rates')}
                className={`px-1 py-0.5 sm:px-2 sm:py-1 lg:px-3 lg:py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                  currentPage === 'funding-rates'
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                <span className="hidden sm:inline">Funding Rates</span>
                <span className="sm:hidden">Rates</span>
              </button>
            </div>
          </div>
          
          {/* Logout and Theme Toggle */}
          <div className="flex items-center space-x-1 sm:space-x-2">
            <button
              onClick={onLogout}
              className="px-1 py-0.5 sm:px-2 sm:py-1 lg:px-3 lg:py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-xs sm:text-sm"
            >
              Logout
            </button>
            <button
              onClick={toggleTheme}
              className="p-1 sm:p-2 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation; 