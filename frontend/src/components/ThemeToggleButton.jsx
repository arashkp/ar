import React from 'react';
import { useTheme } from '../context/ThemeContext';

const ThemeToggleButton = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="px-4 py-2 font-semibold text-white bg-blue-500 rounded hover:bg-blue-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200"
      style={{
        position: 'fixed',
        top: '20px',
        right: '20px',
        zIndex: 1000, // Ensure it's on top
      }}
    >
      Switch to {theme === 'light' ? 'Dark' : 'Light'} Mode
    </button>
  );
};

export default ThemeToggleButton;
