import React, { useState } from 'react';

const LLMPromptGenerator = ({ selectedSymbol, onClose }) => {
  const [promptType, setPromptType] = useState('comprehensive');
  const [generatedPrompt, setGeneratedPrompt] = useState('');

  const generatePrompt = () => {
    if (!selectedSymbol) return;

    let prompt = '';

    if (promptType === 'comprehensive') {
      prompt = generateComprehensivePrompt(selectedSymbol);
    } else if (promptType === 'quick') {
      prompt = generateQuickPrompt(selectedSymbol);
    } else if (promptType === 'technical') {
      prompt = generateTechnicalPrompt(selectedSymbol);
    }

    setGeneratedPrompt(prompt);
  };

  const generateComprehensivePrompt = (symbolData) => {
    const {
      symbol,
      current_price,
      dca_signal,
      dca_confidence,
      dca_amount_multiplier,
      dca_reasoning = [],
      market_sentiment,
      rsi_14,
      volume_ratio,
      volume_ratio_avg,
      vol_price_ratio,
      volume_status,
      ema_21,
      sma_30,
      atr_14,
      support_levels = [],
      resistance_levels = []
    } = symbolData;

    return `# DCA Strategy Analysis - ${symbol}

## Current Market Conditions
- **Symbol**: ${symbol}
- **Current Price**: $${current_price?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
- **Market Sentiment**: ${market_sentiment?.toUpperCase() || 'NEUTRAL'}
- **DCA Signal**: ${dca_signal?.replace('_', ' ').toUpperCase() || 'HOLD'}
- **Confidence Level**: ${dca_confidence?.toFixed(1) || '50.0'}%
- **Recommended Amount Multiplier**: ${dca_amount_multiplier?.toFixed(2) || '1.00'}x

## Technical Analysis
- **RSI (14)**: ${rsi_14?.toFixed(1) || 'N/A'} ${rsi_14 < 30 ? '(Oversold)' : rsi_14 > 70 ? '(Overbought)' : '(Neutral)'}
- **Volume Status**: ${volume_status?.toUpperCase() || 'N/A'} (${volume_ratio?.toFixed(2) || 'N/A'}x average)
- **Volume Trend**: ${volume_ratio_avg?.toFixed(2) || 'N/A'}x (${volume_ratio_avg > 1.3 ? 'Increasing' : volume_ratio_avg < 0.7 ? 'Decreasing' : 'Stable'})
- **Volume-Price Ratio**: ${vol_price_ratio?.toFixed(3) || 'N/A'} ${vol_price_ratio > 1.0 ? '(Volume confirms price)' : vol_price_ratio < 0.3 ? '(Price moving without volume)' : '(Normal correlation)'}
- **EMA21**: $${ema_21?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) || 'N/A'} ${current_price > ema_21 ? '(Price above EMA21)' : current_price < ema_21 ? '(Price below EMA21)' : '(Price at EMA21)'}
- **SMA30**: $${sma_30?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) || 'N/A'} ${current_price > sma_30 ? '(Price above SMA30)' : current_price < sma_30 ? '(Price below SMA30)' : '(Price at SMA30)'}
- **ATR (14)**: ${atr_14?.toFixed(4) || 'N/A'} ${atr_14 && (atr_14/current_price)*100 > 5 ? '(High volatility)' : atr_14 && (atr_14/current_price)*100 < 1 ? '(Low volatility)' : '(Normal volatility)'}

## Key Price Levels
**Support Levels:**
${support_levels.slice(0, 3).map((level, i) => {
  const distance = ((current_price - level.level) / current_price) * 100;
  return `- Level ${i + 1}: $${level.level.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })} (Strength: ${level.strength}, Distance: ${distance.toFixed(1)}%)`;
}).join('\n')}

**Resistance Levels:**
${resistance_levels.slice(0, 3).map((level, i) => {
  const distance = ((level.level - current_price) / current_price) * 100;
  return `- Level ${i + 1}: $${level.level.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })} (Strength: ${level.strength}, Distance: ${distance.toFixed(1)}%)`;
}).join('\n')}

## Analysis Reasoning
${dca_reasoning.length > 0 ? dca_reasoning.map(reason => `- ${reason}`).join('\n') : '- No specific signals detected'}

## DCA Strategy Questions

Based on this market analysis for ${symbol}, please provide specific, actionable advice for my Dollar Cost Averaging strategy:

1. **Entry Decision**: Should I execute my DCA now, wait for a better price, or avoid this symbol entirely? What's your reasoning?

2. **Position Sizing**: The analysis suggests a ${dca_amount_multiplier?.toFixed(2) || '1.00'}x multiplier. How should I adjust my normal DCA amount? Should I go larger, smaller, or stick to my usual amount?

3. **Entry Price Range**: What's the optimal price range for this DCA entry? Should I use a limit order, and if so, at what price?

4. **Risk Management**: What stop-loss or take-profit levels should I consider? How should I manage risk given the current market conditions?

5. **Timing Strategy**: When is the best time to place this order? Should I wait for specific conditions or enter immediately?

6. **Market Context**: How does this fit into the broader market trend? What external factors should I consider?

7. **Alternative Strategies**: If this isn't the right time to DCA, what other strategies should I consider (e.g., waiting for support, scaling in, etc.)?

Please provide specific, actionable recommendations with clear reasoning for each decision point.`;
  };

  const generateQuickPrompt = (symbolData) => {
    const { symbol, dca_signal, dca_confidence, dca_reasoning = [] } = symbolData;

    return `# Quick DCA Decision - ${symbol}

**Signal**: ${dca_signal?.replace('_', ' ').toUpperCase() || 'HOLD'}
**Confidence**: ${dca_confidence?.toFixed(1) || '50.0'}%

**Key Points:**
${dca_reasoning.slice(0, 3).map(reason => `- ${reason}`).join('\n')}

**Quick Decision Needed:**
Should I DCA ${symbol} now? Yes/No/Wait? Why?

**Recommended Action:**`;
  };

  const generateTechnicalPrompt = (symbolData) => {
    const {
      symbol,
      current_price,
      rsi_14,
      volume_ratio,
      volume_ratio_avg,
      vol_price_ratio,
      volume_status,
      ema_21,
      sma_30,
      atr_14,
      support_levels = [],
      resistance_levels = []
    } = symbolData;

    return `# Technical Analysis for ${symbol}

**Current Price**: $${current_price?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}

**Technical Indicators:**
- RSI (14): ${rsi_14?.toFixed(1) || 'N/A'}
- Volume Status: ${volume_status?.toUpperCase() || 'N/A'} (${volume_ratio?.toFixed(2) || 'N/A'}x)
- Volume Trend: ${volume_ratio_avg?.toFixed(2) || 'N/A'}x
- Volume-Price Ratio: ${vol_price_ratio?.toFixed(3) || 'N/A'}
- EMA21: $${ema_21?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) || 'N/A'}
- SMA30: $${sma_30?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) || 'N/A'}
- ATR (14): ${atr_14?.toFixed(4) || 'N/A'}

**Key Levels:**
Support: ${support_levels.slice(0, 2).map(l => `$${l.level.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`).join(', ')}
Resistance: ${resistance_levels.slice(0, 2).map(l => `$${l.level.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`).join(', ')}

**Technical Analysis Request:**
Based on these technical indicators, what's your assessment of ${symbol}? Should I buy, sell, or hold? What are the key levels to watch?`;
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedPrompt);
    // You could add a toast notification here
  };

  if (!selectedSymbol) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              LLM Prompt Generator - {selectedSymbol.symbol}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Generate prompts for ChatGPT, Grok, or other LLMs
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Prompt Type Selection */}
          <div className="flex space-x-4">
            <label className="flex items-center">
              <input
                type="radio"
                value="comprehensive"
                checked={promptType === 'comprehensive'}
                onChange={(e) => setPromptType(e.target.value)}
                className="mr-2"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Comprehensive</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="quick"
                checked={promptType === 'quick'}
                onChange={(e) => setPromptType(e.target.value)}
                className="mr-2"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Quick Decision</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="technical"
                checked={promptType === 'technical'}
                onChange={(e) => setPromptType(e.target.value)}
                className="mr-2"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Technical Only</span>
            </label>
          </div>

          {/* Generate Button */}
          <button
            onClick={generatePrompt}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Generate Prompt
          </button>

          {/* Generated Prompt */}
          {generatedPrompt && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Generated Prompt</h3>
                <button
                  onClick={copyToClipboard}
                  className="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700 transition-colors"
                >
                  Copy to Clipboard
                </button>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <pre className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 font-mono overflow-auto max-h-96">
                  {generatedPrompt}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LLMPromptGenerator; 