import React from 'react';

const SymbolOverview = ({ symbolData }) => {
  if (!symbolData) {
    return <div className="p-4 text-center text-gray-500 dark:text-gray-400">No symbol data provided.</div>;
  }

  // Assuming symbol_name might not always be present, provide a fallback.
  const symbolName = symbolData.symbol_name || symbolData.symbol || 'Unnamed Symbol';
  const { current_price, h1_indicators, nearby_levels } = symbolData;

  return (
    <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-6 transform hover:scale-105 transition-transform duration-200">
      <h2 className="text-2xl font-bold mb-4 text-blue-600 dark:text-blue-400 border-b pb-2 border-gray-200 dark:border-gray-700">
        {symbolName}
      </h2>
      <p className="text-3xl font-semibold my-4 text-center text-green-600 dark:text-green-400">
        ${current_price !== undefined ? current_price.toFixed(2) : 'N/A'}
      </p>

      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-3 text-gray-700 dark:text-gray-300">H1 Indicators</h3>
        {h1_indicators && Object.keys(h1_indicators).length > 0 ? (
          <ul className="space-y-2">
            {Object.entries(h1_indicators).map(([key, value]) => (
              <li key={key} className="flex justify-between text-sm text-gray-600 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 py-1">
                <span className="font-medium text-gray-700 dark:text-gray-300">{key.toUpperCase()}:</span>
                <span>
                  {value !== undefined && value !== null ? value.toFixed(2) : 'N/A'}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">No H1 indicators available.</p>
        )}
      </div>

      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-3 text-gray-700 dark:text-gray-300">Support Levels</h3>
        {nearby_levels && nearby_levels.support && nearby_levels.support.length > 0 ? (
          <ul className="space-y-1">
            {nearby_levels.support.map((level, index) => (
              <li key={`support-${index}`} className="text-sm text-green-700 dark:text-green-500">
                ${level !== undefined ? level.toFixed(2) : 'N/A'}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">No support levels available.</p>
        )}
      </div>

      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-3 text-gray-700 dark:text-gray-300">Resistance Levels</h3>
        {nearby_levels && nearby_levels.resistance && nearby_levels.resistance.length > 0 ? (
          <ul className="space-y-1">
            {nearby_levels.resistance.map((level, index) => (
              <li key={`resistance-${index}`} className="text-sm text-red-700 dark:text-red-500">
                ${level !== undefined ? level.toFixed(2) : 'N/A'}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">No resistance levels available.</p>
        )}
      </div>
    </div>
  );
};

export default SymbolOverview;
