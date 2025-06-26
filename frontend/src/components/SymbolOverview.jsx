import React, { useState } from 'react';

// Helper function to format numbers with thousand separators and proper precision
const formatNumber = (value, symbol = '') => {
  if (value === undefined || value === null) return 'N/A';
  
  // Determine precision based on symbol
  let precision = 2;
  if (symbol.includes('DOGE') || symbol.includes('POPCAT')) {
    precision = 4; // More precision for smaller value coins
  } else if (symbol.includes('BTC')) {
    precision = 0; // Standard precision for BTC
  } else if (symbol.includes('ETH')) {
    precision = 1; // Standard precision for ETH
  }
  
  const num = parseFloat(value);
  if (isNaN(num)) return 'N/A';
  
  // Format with thousand separators and proper precision
  return num.toLocaleString('en-US', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision
  });
};

// Helper function to make elements clickable and call onPriceClick
const ClickablePrice = ({ price, onPriceClick, children, className, symbol }) => {
  const [isClicked, setIsClicked] = useState(false);

  const handleClick = (event) => { // Add event parameter
    if (typeof onPriceClick === 'function' && price !== undefined && price !== null) {
      event.stopPropagation(); // Stop the event from bubbling up
      setIsClicked(true);
      onPriceClick(parseFloat(price), symbol);
      // Reset the clicked state after a short delay
      setTimeout(() => setIsClicked(false), 300);
    }
  };

  // Add some basic styling to indicate clickability if onPriceClick is provided
  const clickableStyles = typeof onPriceClick === 'function'
    ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 p-1 rounded transition-all duration-200'
    : '';

  const clickedStyles = isClicked ? 'bg-blue-100 dark:bg-blue-900/30 scale-105' : '';

  return (
    <span onClick={handleClick} className={`${className} ${clickableStyles} ${clickedStyles}`}>
      {children}
    </span>
  );
};

// Tooltip component for technical indicators
const Tooltip = ({ children, content }) => {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        className="cursor-help"
      >
        {children}
      </div>
      {isVisible && (
        <div className="absolute z-10 w-64 p-3 text-sm text-white bg-gray-900 dark:bg-gray-800 rounded-lg shadow-lg border border-gray-700 -top-2 left-full ml-2">
          {content}
          <div className="absolute top-3 -left-1 w-2 h-2 bg-gray-900 dark:bg-gray-800 transform rotate-45 border-l border-b border-gray-700"></div>
        </div>
      )}
    </div>
  );
};

const SymbolOverview = ({ symbolData, onPriceClick }) => {
  if (!symbolData) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded mb-3"></div>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded mb-4"></div>
          <div className="space-y-1">
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  const symbolName = symbolData.symbol || 'Unnamed Symbol';
  const { 
    current_price, 
    ema_21, 
    ema_89, 
    sma_30, 
    sma_150, 
    sma_300, 
    atr_14,
    support_levels = [],
    resistance_levels = [],
    amount
  } = symbolData;

  // Gather all levels (support, resistance, EMAs, SMAs, etc.)
  const levels = [
    ...resistance_levels.map(l => ({ ...l, type: 'resistance', label: l.strength })),
    ...support_levels.map(l => ({ ...l, type: 'support', label: l.strength })),
    ...(ema_21 ? [{ level: ema_21, type: 'ema', label: 'EMA 21' }] : []),
    ...(ema_89 ? [{ level: ema_89, type: 'ema', label: 'EMA 89' }] : []),
    ...(sma_30 ? [{ level: sma_30, type: 'sma', label: 'SMA 30' }] : []),
    ...(sma_150 ? [{ level: sma_150, type: 'sma', label: 'SMA 150' }] : []),
    ...(sma_300 ? [{ level: sma_300, type: 'sma', label: 'SMA 300' }] : [])
  ];

  // Remove duplicates (by level+label)
  const uniqueLevels = Array.from(new Map(levels.map(l => [l.level + '-' + l.label, l])).values());

  // Sort: resistance (above price, descending), price, support (below price, descending)
  const above = uniqueLevels.filter(l => l.level > current_price).sort((a, b) => b.level - a.level);
  const below = uniqueLevels.filter(l => l.level < current_price).sort((a, b) => b.level - a.level);

  // Find the top 2 strength levels in resistance and support
  const getTopStrengthIndexes = (arr) => {
    const sorted = [...arr].sort((a, b) => (parseInt(b.label) || 0) - (parseInt(a.label) || 0));
    return sorted.slice(0, 2).map(l => arr.findIndex(x => x.level === l.level && x.label === l.label));
  };
  const topResIdx = getTopStrengthIndexes(above);
  const topSupIdx = getTopStrengthIndexes(below);

  // For display: resistance (red), price (highlighted), support (green)
  return (
    <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-4 flex flex-col items-stretch border border-gray-200 dark:border-gray-700 hover:shadow-xl min-w-[200px]">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-bold bg-gradient-to-r from-teal-500 to-blue-600 bg-clip-text text-transparent drop-shadow-sm">{symbolName}</h2>
      </div>
      <div className="flex flex-col w-full">
        {above.map((level, idx) => (
          <div key={`above-${idx}`} className={`flex justify-between items-center text-red-700 dark:text-red-500 py-0 ${topResIdx.includes(idx) ? 'font-bold' : ''}`}>
            <ClickablePrice price={level.level} onPriceClick={(price, symbol) => onPriceClick(price, symbol, 'sell')} symbol={symbolName}>
              {formatNumber(level.level, symbolName)}
            </ClickablePrice>
            <span className="text-xs ml-2 italic">{level.label}</span>
          </div>
        ))}
        {/* Current Price */}
        <div className="flex justify-between items-center font-bold text-lg py-1 my-1">
          <ClickablePrice price={current_price} onPriceClick={(price, symbol) => onPriceClick(price, symbol, null)} symbol={symbolName}>
            {formatNumber(current_price, symbolName)}
          </ClickablePrice>
          <span className="text-xs ml-2">Price</span>
        </div>
        {below.map((level, idx) => (
          <div key={`below-${idx}`} className={`flex justify-between items-center text-green-700 dark:text-green-500 py-0 ${topSupIdx.includes(idx) ? 'font-bold' : ''}`}>
            <ClickablePrice price={level.level} onPriceClick={(price, symbol) => onPriceClick(price, symbol, 'buy')} symbol={symbolName}>
              {formatNumber(level.level, symbolName)}
            </ClickablePrice>
            <span className="text-xs ml-2 italic">{level.label}</span>
          </div>
        ))}
        {amount && current_price && (
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 text-center">
            Actual: $
            <span className="font-mono">
              {(parseFloat(amount) * parseFloat(current_price)).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default SymbolOverview;
