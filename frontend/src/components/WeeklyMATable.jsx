import React from 'react';

const precisionBySymbol = {
  'BTC/USDT': 0,
  'ETH/USDT': 1,
  'SUI/USDT': 3,
  'DOGE/USDT': 4,
  'HBAR/USDT': 4,
  'HYPE/USDT': 2,
  'BONK/USDT': 7,
};

const getDigits = (symbol) => (symbol && precisionBySymbol[symbol] !== undefined
  ? precisionBySymbol[symbol]
  : 2);

const formatNum = (val, digits = 2) => {
  if (val === null || val === undefined || Number.isNaN(Number(val))) return 'N/A';
  const n = Number(val);
  return n.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
};

const WeeklyMATable = ({ marketData }) => {
  if (!Array.isArray(marketData) || marketData.length === 0) return null;

  // Columns = symbols sorted by current price (desc), limit to 5
  const symbols = [...marketData]
    .filter((s) => s && s.symbol && s.current_price != null)
    .sort((a, b) => (b.current_price || 0) - (a.current_price || 0));

  const metrics = [
    { key: 'w_sma_20', label: '20W', type: 'ma' },
    { key: 'current_price', label: 'CP', type: 'price' },
    { key: 'w_ema_21', label: '21W', type: 'ma' },
    { key: 'w_sma_50', label: '50W', type: 'ma' },
  ];

  const aboveColor = 'text-green-600 dark:text-green-400';
  const belowColor = 'text-red-600 dark:text-red-400';
  const neutralColor = 'text-gray-600 dark:text-gray-400';

  const metricColor = (metricType, price, value) => {
    if (metricType !== 'ma') return 'text-gray-900 dark:text-gray-100';
    if (value == null) return neutralColor;
    if (price == null) return neutralColor;
    return price > value ? aboveColor : belowColor;
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
          Weekly Moving Averages
        </h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Columns: Symbols (sorted by price) • Rows: Current Price, 20W SMA, 21W EMA, 50W SMA
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              {symbols.map((s) => (
                <th key={s.symbol} className="px-3 py-2 text-center font-semibold text-gray-700 dark:text-gray-200">
                  {s.symbol}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {symbols.map((s) => {
                const digits = getDigits(s.symbol);
                const price = s.current_price;
                const orderedMetrics = metrics
                  .map((metric) => ({
                    ...metric,
                    value: metric.key === 'current_price' ? s.current_price : s[metric.key],
                  }))
                  .sort((a, b) => {
                    const aValue = Number.isFinite(a.value) ? a.value : Number(a.value);
                    const bValue = Number.isFinite(b.value) ? b.value : Number(b.value);
                    const aComparable = Number.isFinite(aValue) ? aValue : Number.NEGATIVE_INFINITY;
                    const bComparable = Number.isFinite(bValue) ? bValue : Number.NEGATIVE_INFINITY;
                    return bComparable - aComparable;
                  });

                return (
                  <td key={s.symbol} className="px-3 py-4 align-top">
                    <div className="flex flex-col gap-2">
                      {orderedMetrics.map((metric) => (
                        <div
                          key={`${s.symbol}-${metric.key}`}
                          className="text-center text-sm sm:text-base text-gray-600 dark:text-gray-300"
                        >
                          <span className="uppercase tracking-wide text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                            {metric.label}:
                          </span>{' '}
                          <span
                            className={`font-mono text-base sm:text-lg ${metricColor(metric.type, price, metric.value)}`}
                          >
                            {formatNum(metric.value, digits)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
        MAs stay green when current price is above them, and red when below.
      </p>
    </div>
  );
};

export default WeeklyMATable;
