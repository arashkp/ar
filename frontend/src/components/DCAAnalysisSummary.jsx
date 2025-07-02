import React from 'react';

const DCAAnalysisSummary = ({ marketData }) => {
  if (!marketData || !Array.isArray(marketData)) {
    return null;
  }

  // Group symbols by DCA signal
  const groupedBySignal = marketData.reduce((acc, symbol) => {
    const signal = symbol.dca_signal || 'hold';
    if (!acc[signal]) {
      acc[signal] = [];
    }
    acc[signal].push(symbol);
    return acc;
  }, {});

  // Sort signals by priority
  const signalOrder = ['strong_buy', 'buy', 'hold', 'wait', 'avoid'];
  
  const getSignalColor = (signal) => {
    switch (signal) {
      case 'strong_buy':
        return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
      case 'buy':
        return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20';
      case 'hold':
        return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20';
      case 'wait':
        return 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20';
      case 'avoid':
        return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
      default:
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  const getSignalIcon = (signal) => {
    switch (signal) {
      case 'strong_buy':
        return '🚀';
      case 'buy':
        return '📈';
      case 'hold':
        return '⏸️';
      case 'wait':
        return '⏳';
      case 'avoid':
        return '⚠️';
      default:
        return '📊';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          DCA Strategy Summary
        </h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {marketData.length} symbols analyzed
        </div>
      </div>

      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Strong Buy and Buy in one row */}
          <div className="space-y-6">
            {['strong_buy', 'buy'].map(signal => {
              const symbols = groupedBySignal[signal] || [];
              if (symbols.length === 0) return null;
              return (
                <div key={signal} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-2xl">{getSignalIcon(signal)}</span>
                      <h3 className={`text-lg font-semibold ${getSignalColor(signal)} px-3 py-1 rounded-full`}>
                        {signal.replace('_', ' ').toUpperCase()} ({symbols.length})
                      </h3>
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Avg Confidence: {(
                        symbols.reduce((sum, s) => sum + (s.dca_confidence || 0), 0) / symbols.length
                      ).toFixed(1)}%
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {symbols.map(symbol => (
                      <div 
                        key={symbol.symbol} 
                        className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base">
                            {symbol.symbol}
                          </span>
                          <span className="text-xs sm:text-sm font-mono text-gray-600 dark:text-gray-400">
                            ${symbol.current_price?.toLocaleString('en-US', { 
                              minimumFractionDigits: 2, 
                              maximumFractionDigits: 4 
                            })}
                          </span>
                        </div>
                        
                        <div className="flex items-center justify-between text-xs sm:text-sm">
                          <span className="text-gray-600 dark:text-gray-400">
                            Conf: {symbol.dca_confidence?.toFixed(1)}%
                          </span>
                          <span className="text-gray-600 dark:text-gray-400">
                            Amt: {symbol.dca_amount_multiplier?.toFixed(2)}x
                          </span>
                        </div>

                        {/* Key indicators */}
                        <div className="flex items-center justify-between text-xs mt-2 text-gray-500 dark:text-gray-400">
                          <span>RSI: {symbol.rsi_14?.toFixed(1) || 'N/A'}</span>
                          <span>Vol: {symbol.volume_ratio?.toFixed(1) || 'N/A'}x</span>
                          <span className={`${
                            symbol.market_sentiment === 'bullish' ? 'text-green-600 dark:text-green-400' :
                            symbol.market_sentiment === 'bearish' ? 'text-red-600 dark:text-red-400' :
                            'text-gray-600 dark:text-gray-400'
                          }`}>
                            <span className="hidden sm:inline">{symbol.market_sentiment?.toUpperCase() || 'NEUTRAL'}</span>
                            <span className="sm:hidden">{symbol.market_sentiment?.toUpperCase()[0] || 'N'}</span>
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          {/* Wait and Avoid in one row */}
          <div className="space-y-6">
            {['wait', 'avoid'].map(signal => {
              const symbols = groupedBySignal[signal] || [];
              if (symbols.length === 0) return null;
              return (
                <div key={signal} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-2xl">{getSignalIcon(signal)}</span>
                      <h3 className={`text-lg font-semibold ${getSignalColor(signal)} px-3 py-1 rounded-full`}>
                        {signal.replace('_', ' ').toUpperCase()} ({symbols.length})
                      </h3>
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Avg Confidence: {(
                        symbols.reduce((sum, s) => sum + (s.dca_confidence || 0), 0) / symbols.length
                      ).toFixed(1)}%
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {symbols.map(symbol => (
                      <div 
                        key={symbol.symbol} 
                        className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base">
                            {symbol.symbol}
                          </span>
                          <span className="text-xs sm:text-sm font-mono text-gray-600 dark:text-gray-400">
                            ${symbol.current_price?.toLocaleString('en-US', { 
                              minimumFractionDigits: 2, 
                              maximumFractionDigits: 4 
                            })}
                          </span>
                        </div>
                        
                        <div className="flex items-center justify-between text-xs sm:text-sm">
                          <span className="text-gray-600 dark:text-gray-400">
                            Conf: {symbol.dca_confidence?.toFixed(1)}%
                          </span>
                          <span className="text-gray-600 dark:text-gray-400">
                            Amt: {symbol.dca_amount_multiplier?.toFixed(2)}x
                          </span>
                        </div>

                        {/* Key indicators */}
                        <div className="flex items-center justify-between text-xs mt-2 text-gray-500 dark:text-gray-400">
                          <span>RSI: {symbol.rsi_14?.toFixed(1) || 'N/A'}</span>
                          <span>Vol: {symbol.volume_ratio?.toFixed(1) || 'N/A'}x</span>
                          <span className={`${
                            symbol.market_sentiment === 'bullish' ? 'text-green-600 dark:text-green-400' :
                            symbol.market_sentiment === 'bearish' ? 'text-red-600 dark:text-red-400' :
                            'text-gray-600 dark:text-gray-400'
                          }`}>
                            <span className="hidden sm:inline">{symbol.market_sentiment?.toUpperCase() || 'NEUTRAL'}</span>
                            <span className="sm:hidden">{symbol.market_sentiment?.toUpperCase()[0] || 'N'}</span>
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        {/* Hold in its own row */}
        {['hold'].map(signal => {
          const symbols = groupedBySignal[signal] || [];
          if (symbols.length === 0) return null;
          return (
            <div key={signal} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <span className="text-2xl">{getSignalIcon(signal)}</span>
                  <h3 className={`text-lg font-semibold ${getSignalColor(signal)} px-3 py-1 rounded-full`}>
                    {signal.replace('_', ' ').toUpperCase()} ({symbols.length})
                  </h3>
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Avg Confidence: {(
                    symbols.reduce((sum, s) => sum + (s.dca_confidence || 0), 0) / symbols.length
                  ).toFixed(1)}%
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {symbols.map(symbol => (
                  <div 
                    key={symbol.symbol} 
                    className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base">
                        {symbol.symbol}
                      </span>
                      <span className="text-xs sm:text-sm font-mono text-gray-600 dark:text-gray-400">
                        ${symbol.current_price?.toLocaleString('en-US', { 
                          minimumFractionDigits: 2, 
                          maximumFractionDigits: 4 
                        })}
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-between text-xs sm:text-sm">
                      <span className="text-gray-600 dark:text-gray-400">
                        Conf: {symbol.dca_confidence?.toFixed(1)}%
                      </span>
                      <span className="text-gray-600 dark:text-gray-400">
                        Amt: {symbol.dca_amount_multiplier?.toFixed(2)}x
                      </span>
                    </div>

                    {/* Key indicators */}
                    <div className="flex items-center justify-between text-xs mt-2 text-gray-500 dark:text-gray-400">
                      <span>RSI: {symbol.rsi_14?.toFixed(1) || 'N/A'}</span>
                      <span>Vol: {symbol.volume_ratio?.toFixed(1) || 'N/A'}x</span>
                      <span className={`${
                        symbol.market_sentiment === 'bullish' ? 'text-green-600 dark:text-green-400' :
                        symbol.market_sentiment === 'bearish' ? 'text-red-600 dark:text-red-400' :
                        'text-gray-600 dark:text-gray-400'
                      }`}>
                        <span className="hidden sm:inline">{symbol.market_sentiment?.toUpperCase() || 'NEUTRAL'}</span>
                        <span className="sm:hidden">{symbol.market_sentiment?.toUpperCase()[0] || 'N'}</span>
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Statistics */}
      <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Portfolio Strategy Insights
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {groupedBySignal.strong_buy?.length || 0} + {groupedBySignal.buy?.length || 0}
            </div>
            <div className="text-sm text-blue-600 dark:text-blue-400">
              Strong Buy & Buy Opportunities
            </div>
          </div>
          
          <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {groupedBySignal.hold?.length || 0}
            </div>
            <div className="text-sm text-yellow-600 dark:text-yellow-400">
              Hold Positions
            </div>
          </div>
          
          <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {groupedBySignal.wait?.length || 0} + {groupedBySignal.avoid?.length || 0}
            </div>
            <div className="text-sm text-red-600 dark:text-red-400">
              Wait & Avoid Signals
            </div>
          </div>
        </div>

        {/* Recommended Action */}
        <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-green-50 dark:from-blue-900/20 dark:to-green-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
          <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
            💡 Recommended Portfolio Action
          </h4>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {groupedBySignal.strong_buy?.length > 0 || groupedBySignal.buy?.length > 0 
              ? `Focus on ${groupedBySignal.strong_buy?.length || 0} strong buy and ${groupedBySignal.buy?.length || 0} buy opportunities. Consider increasing position sizes for strong buy signals.`
              : groupedBySignal.hold?.length > 0
              ? `Maintain current positions. ${groupedBySignal.hold.length} symbols are in hold territory.`
              : `Market conditions suggest waiting. ${groupedBySignal.wait?.length || 0} symbols should be monitored, ${groupedBySignal.avoid?.length || 0} should be avoided.`
            }
          </p>
        </div>
      </div>
    </div>
  );
};

export default DCAAnalysisSummary; 