import React, { useState } from 'react';
import { FaRegCommentDots } from 'react-icons/fa';

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

const SymbolOverview = ({ symbolData, onPriceClick, onSymbolClick }) => {
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
    amount,
    // DCA Analysis fields
    dca_signal,
    dca_confidence,
    dca_amount_multiplier,
    dca_reasoning = [],
    rsi_14,
    volume_ratio,
    volume_ratio_avg,
    vol_price_ratio,
    volume_status,
    market_sentiment
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

  // DCA Signal styling
  const getDCASignalStyle = (signal) => {
    switch (signal) {
      case 'strong_buy':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border-green-300 dark:border-green-700';
      case 'buy':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 border-blue-300 dark:border-blue-700';
      case 'hold':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 border-yellow-300 dark:border-yellow-700';
      case 'wait':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400 border-orange-300 dark:border-orange-700';
      case 'avoid':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border-red-300 dark:border-red-700';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400 border-gray-300 dark:border-gray-700';
    }
  };

  const handleSymbolClick = () => {
    if (onSymbolClick && symbolData) {
      onSymbolClick(symbolData);
    }
  };

  // For display: resistance (red), price (highlighted), support (green)
  return (
    <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-3 sm:p-4 flex flex-col items-stretch border border-gray-200 dark:border-gray-700 hover:shadow-xl cursor-pointer transition-all duration-200">
      <div className="flex items-center justify-between mb-2">
        {/* Prompt Icon Button */}
        <button
          onClick={(e) => { e.stopPropagation(); if (onSymbolClick) onSymbolClick(symbolData); }}
          className="mr-2 p-1 rounded-full hover:bg-blue-100 dark:hover:bg-blue-900/40 focus:outline-none"
          title="Show LLM Prompt"
          tabIndex={0}
        >
          <FaRegCommentDots className="w-5 h-5 text-blue-500" />
        </button>
        <h2 className="text-sm sm:text-lg font-bold bg-gradient-to-r from-teal-500 to-blue-600 bg-clip-text text-transparent drop-shadow-sm truncate flex-1">
          {symbolName}
        </h2>
        
        {/* DCA Signal Badge */}
        {dca_signal && (
          <div className={`px-1 sm:px-2 py-1 rounded-full text-xs font-semibold border ${getDCASignalStyle(dca_signal)} flex-shrink-0`}>
            <span className="hidden sm:inline">{dca_signal.replace('_', ' ').toUpperCase()}</span>
            <span className="sm:hidden">{dca_signal.replace('_', ' ').toUpperCase().split(' ')[0]}</span>
          </div>
        )}
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
        <div className="flex justify-between items-center font-bold text-base sm:text-lg py-1 my-1">
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
        
        {/* DCA Analysis Section */}
        {dca_signal && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <div className="space-y-1 sm:space-y-2">
              {/* Confidence and Multiplier */}
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 dark:text-gray-400">Conf:</span>
                <span className="font-semibold">{dca_confidence?.toFixed(1)}%</span>
              </div>
              
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 dark:text-gray-400">Amt:</span>
                <span className="font-semibold">{dca_amount_multiplier?.toFixed(2)}x</span>
              </div>
              
              {/* Technical Indicators - Compact for mobile */}
              {rsi_14 && (
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-600 dark:text-gray-400">RSI:</span>
                  <span className={`font-semibold ${
                    rsi_14 < 30 ? 'text-green-600 dark:text-green-400' : 
                    rsi_14 > 70 ? 'text-red-600 dark:text-red-400' : 
                    'text-gray-600 dark:text-gray-400'
                  }`}>
                    {rsi_14.toFixed(1)}
                  </span>
                </div>
              )}
              
              {volume_ratio && (
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-600 dark:text-gray-400">Vol:</span>
                  <span className={`font-semibold ${
                    volume_status === 'very_high' ? 'text-green-600 dark:text-green-400' : 
                    volume_status === 'high' ? 'text-blue-600 dark:text-blue-400' : 
                    volume_status === 'low' ? 'text-red-600 dark:text-red-400' : 
                    'text-gray-600 dark:text-gray-400'
                  }`}>
                    <span className="hidden sm:inline">{volume_ratio.toFixed(2)}x ({volume_status})</span>
                    <span className="sm:hidden">{volume_ratio.toFixed(1)}x</span>
                  </span>
                </div>
              )}
              
              {volume_ratio_avg && (
                <div className="hidden sm:flex justify-between items-center text-xs">
                  <span className="text-gray-600 dark:text-gray-400">Trend:</span>
                  <span className={`font-semibold ${
                    volume_ratio_avg > 1.3 ? 'text-green-600 dark:text-green-400' : 
                    volume_ratio_avg < 0.7 ? 'text-red-600 dark:text-red-400' : 
                    'text-gray-600 dark:text-gray-400'
                  }`}>
                    {volume_ratio_avg > 1.3 ? '↗️' : volume_ratio_avg < 0.7 ? '↘️' : '→'} {volume_ratio_avg.toFixed(2)}x
                  </span>
                </div>
              )}
              
              {/* Market Sentiment */}
              {market_sentiment && (
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-600 dark:text-gray-400">Sent:</span>
                  <span className={`font-semibold ${
                    market_sentiment === 'bullish' ? 'text-green-600 dark:text-green-400' : 
                    market_sentiment === 'bearish' ? 'text-red-600 dark:text-red-400' : 
                    'text-gray-600 dark:text-gray-400'
                  }`}>
                    <span className="hidden sm:inline">{market_sentiment.toUpperCase()}</span>
                    <span className="sm:hidden">{market_sentiment.toUpperCase()[0]}</span>
                  </span>
                </div>
              )}
            </div>
            
            {/* Top Reasoning - Hidden on mobile for space */}
            {dca_reasoning && dca_reasoning.length > 0 && (
              <div className="hidden sm:block mt-2 text-xs text-gray-600 dark:text-gray-400">
                <div className="font-semibold mb-1">Key Points:</div>
                <ul className="list-disc list-inside space-y-1">
                  {dca_reasoning.slice(0, 2).map((reason, index) => (
                    <li key={index} className="text-xs">{reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SymbolOverview;
