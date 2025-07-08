import React, { useContext } from 'react';
import { ThemeContext } from '../context/ThemeContext.jsx';

const ThemeToggleButton = ({ iconOnly, buttonClassName }) => {
  const { theme, toggleTheme } = useContext(ThemeContext);
  return (
    <button
      onClick={toggleTheme}
      className={buttonClassName ? buttonClassName : (iconOnly ? 'p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors' : 'px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors')}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m8.66-8.66l-.71.71M4.05 19.07l-.71.71M21 12h-1M4 12H3m16.95-7.07l-.71.71M4.05 4.93l-.71-.71" />
      </svg>
    </button>
  );
};

export default ThemeToggleButton;
