import React from 'react';
import { useTheme } from '../context/ThemeContext';

const ThemeToggleButton = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="p-2 bg-blue-500 dark:bg-gray-700 rounded-full hover:bg-blue-600 dark:hover:bg-gray-600 text-white dark:text-gray-200 transition-colors"
      style={{
        position: 'fixed',
        top: '20px',
        right: '20px',
        zIndex: 1000,
      }}
      title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
    >
      {theme === 'light' ? (
        // Moon icon
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12.79A9 9 0 1111.21 3a7 7 0 109.79 9.79z" />
        </svg>
      ) : (
        // Sun icon
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="2" fill="currentColor" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 1v2m0 18v2m11-11h-2M3 12H1m16.95 6.95l-1.41-1.41M6.05 6.05L4.64 4.64m12.02 0l-1.41 1.41M6.05 17.95l-1.41 1.41" />
        </svg>
      )}
    </button>
  );
};

export default ThemeToggleButton;
