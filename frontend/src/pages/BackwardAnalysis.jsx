import React, { useState, useEffect } from 'react';
import axios from 'axios';

const AssetOverview = () => {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAssetOverview();
  }, []);

  const fetchAssetOverview = async () => {
    try {
      setLoading(true);
      const response = await axios.get('http://localhost:8000/api/v1/spot-trades/backward-analysis');
      setAnalysisData(response.data);
      setError(null);
    } catch (err) {
      setError(`Failed to fetch asset overview data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString || dateString === '') return 'N/A';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'Invalid Date';
      return date.toLocaleString();
    } catch {
      return 'Invalid Date';
    }
  };

  const formatNumber = (num, decimals = 8) => {
    if (num === null || num === undefined || isNaN(num)) return '0';
    if (num === 0) return '0';
    if (Math.abs(num) < 0.000001) return num.toExponential(4);
    return num.toFixed(decimals).replace(/\.?0+$/, '');
  };

  const formatPrice = (price) => {
    if (price === null || price === undefined || isNaN(price)) return '0';
    // Convert scientific notation to decimal for better readability
    if (price < 0.0001) {
      // Convert to decimal format instead of scientific notation
      return price.toFixed(8).replace(/\.?0+$/, '');
    }
    return price.toFixed(8).replace(/\.?0+$/, '');
  };

  const formatAvgPrice = (price) => {
    if (price === null || price === undefined || isNaN(price)) return '0';
    // Limit to 4 non-zero digits for average entry price
    if (price < 0.0001) {
      return price.toFixed(8).replace(/\.?0+$/, '');
    }
    // For larger numbers, limit to 4 significant digits
    const str = price.toString();
    if (str.includes('.')) {
      const parts = str.split('.');
      const whole = parts[0];
      const decimal = parts[1];
      
      if (whole !== '0') {
        // For numbers >= 1, limit to 4 total digits
        const totalDigits = whole.length + Math.min(decimal.length, 4 - whole.length);
        return price.toFixed(Math.max(0, 4 - whole.length)).replace(/\.?0+$/, '');
      } else {
        // For numbers < 1, show up to 4 non-zero digits
        let nonZeroCount = 0;
        let result = '0.';
        for (let i = 0; i < decimal.length && nonZeroCount < 4; i++) {
          if (decimal[i] !== '0' || nonZeroCount > 0) {
            result += decimal[i];
            nonZeroCount++;
          } else {
            result += '0';
          }
        }
        return result;
      }
    }
    return price.toFixed(4).replace(/\.?0+$/, '');
  };

  const formatQuantity = (quantity) => {
    if (quantity === null || quantity === undefined || isNaN(quantity)) return '0';
    if (quantity > 1000000) return quantity.toLocaleString('en-US');
    return formatNumber(quantity, 8);
  };

  const formatValue = (value) => {
    if (value === null || value === undefined || isNaN(value)) return '0.00';
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const getUsdtBalance = () => {
    if (!analysisData || !analysisData.assets) return 0;
    // Find USDT balance from assets
    const usdtAsset = analysisData.assets.find(asset => asset.symbol === 'USDT');
    return usdtAsset ? usdtAsset.current_balance : 0;
  };

  const calculateTotalCost = () => {
    if (!analysisData || !analysisData.assets) return 0;
    const cryptoCost = analysisData.assets
      .filter(asset => asset.symbol !== 'USDT' && asset.total_buy_value !== undefined)
      .reduce((total, asset) => total + (asset.total_buy_value || 0), 0);
    return cryptoCost; // Only crypto cost
  };

  const calculateTotalCurrentValue = () => {
    if (!analysisData || !analysisData.assets) return 0;
    const cryptoValue = analysisData.assets
      .filter(asset => asset.symbol !== 'USDT' && asset.current_balance !== undefined && asset.current_price !== undefined)
      .reduce((total, asset) => {
        const currentValue = (asset.current_balance || 0) * (asset.current_price || 0);
        return total + currentValue;
      }, 0);
    return cryptoValue; // Only crypto value
  };

  if (loading) {
    return (
      <div className="w-full h-full p-4">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Asset Overview</h2>
          <p className="text-gray-600 dark:text-gray-400">Loading asset overview data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full p-4">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Asset Overview (BitUnix)</h2>
          <p className="text-red-500 dark:text-red-400">{error}</p>
          <button 
            onClick={fetchAssetOverview}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!analysisData || !analysisData.assets) {
    return (
      <div className="w-full h-full p-4">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Asset Overview</h2>
          <p className="text-gray-600 dark:text-gray-400">No asset data available</p>
        </div>
      </div>
    );
  }

  const totalCost = calculateTotalCost();
  const totalCurrentValue = calculateTotalCurrentValue();
  const totalPnL = totalCurrentValue - totalCost;
  const totalPnLPercentage = totalCost > 0 ? (totalPnL / totalCost) * 100 : 0;
  const usdtBalance = getUsdtBalance();
  
  return (
    <div className="w-full h-full p-2">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-white mb-1">Asset Overview</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Balance-relevant orders and calculations for all assets
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-500">
          Last updated: {analysisData.timestamp ? formatDate(analysisData.timestamp) : 'N/A'}
        </p>
      </div>

      {/* Total USDT Balance Info */}
      <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <h2 className="text-lg font-bold text-gray-800 dark:text-white mb-3">Portfolio Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">USDT Balance</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">${formatValue(usdtBalance)}</div>
            <div className="text-xs text-gray-500 dark:text-gray-500">Available USDT</div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">Total Cost</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">${formatValue(totalCost)}</div>
            <div className="text-xs text-gray-500 dark:text-gray-500">Crypto invested</div>
            <div className="text-xs text-gray-400 dark:text-gray-400 mt-1">
              + ${formatValue(usdtBalance)} USDT = ${formatValue(totalCost + usdtBalance)}
            </div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">Current Value</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">${formatValue(totalCurrentValue)}</div>
            <div className="text-xs text-gray-500 dark:text-gray-500">Total crypto value now</div>
            <div className="text-xs text-gray-400 dark:text-gray-400 mt-1">
              + ${formatValue(usdtBalance)} USDT = ${formatValue(totalCurrentValue + usdtBalance)}
            </div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">Total P&L</div>
            <div className={`text-xl font-bold ${totalPnL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              ${formatValue(totalPnL)} ({totalPnLPercentage.toFixed(2)}%)
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-500">Overall profit/loss</div>
          </div>
        </div>
      </div>

      {/* Assets Grid - Full width, 4 columns on extra large screens, 2 on large, 1 on mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-3 w-full">
        {analysisData.assets
          .filter(asset => asset.symbol !== 'USDT' && asset) // Exclude USDT from asset tables and ensure asset exists
          .map((asset, index) => {
          try {
            const currentValue = (asset.current_balance || 0) * (asset.current_price || 0);
            const costValue = asset.total_buy_value || 0;
            const assetPnL = currentValue - costValue;
            const assetPnLPercentage = costValue > 0 ? (assetPnL / costValue) * 100 : 0;
            
            return (
                             <div key={index} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 w-full">
                {/* Asset Header */}
                <div className="mb-3 w-full">
                  <h2 className="text-lg font-bold text-gray-800 dark:text-white mb-2">
                    {asset.symbol || 'Unknown'}
                  </h2>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="font-semibold text-gray-600 dark:text-gray-400">Balance:</span>
                      <br />
                      <span className="text-sm font-bold text-gray-900 dark:text-white">{formatQuantity(asset.current_balance || 0)}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-600 dark:text-gray-400">Avg Entry:</span>
                      <br />
                      <span className="text-sm font-bold text-gray-900 dark:text-white">${formatAvgPrice(asset.average_entry_price || 0)}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-600 dark:text-gray-400">Current:</span>
                      <br />
                      <span className="text-sm font-bold text-gray-900 dark:text-white">${formatPrice(asset.current_price || 0)}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-600 dark:text-gray-400">PnL:</span>
                      <br />
                      <span className={`text-sm font-bold ${(asset.unrealized_pnl || 0) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        ${formatValue(asset.unrealized_pnl || 0)} ({(asset.unrealized_pnl_percentage || 0)}%)
                      </span>
                    </div>
                  </div>
                </div>

                {/* PnL Summary - Compact */}
                <div className="mb-3 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <h3 className="text-sm font-semibold mb-1 text-gray-800 dark:text-white">Summary</h3>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="font-semibold text-gray-600 dark:text-gray-400">Buy Qty:</span>
                      <br />
                      <span className="text-xs font-bold text-gray-900 dark:text-white">{formatQuantity(asset.total_buy_quantity || 0)}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-600 dark:text-gray-400">Cost Value:</span>
                      <br />
                      <span className="text-xs font-bold text-gray-900 dark:text-white">${formatValue(costValue)}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-600 dark:text-gray-400">Orders:</span>
                      <br />
                      <span className="text-xs font-bold text-gray-900 dark:text-white">{asset.number_of_orders || 0} buy orders</span>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-600 dark:text-gray-400">Current Value:</span>
                      <br />
                      <span className={`text-xs font-bold ${currentValue >= costValue ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        ${formatValue(currentValue)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Relevant Orders Table - Show ALL orders */}
                <div className="mb-3 w-full">
                  <h3 className="text-sm font-semibold mb-1 text-gray-800 dark:text-white">
                    Orders ({asset.number_of_orders || 0})
                  </h3>
                  <div className="w-full">
                    <table className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
                      <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                          <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Date
                          </th>
                          <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Price
                          </th>
                          <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Qty
                          </th>
                          <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Value
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                        {(asset.relevant_orders || []).map((order, orderIndex) => (
                          <tr key={orderIndex} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                            <td className="px-2 py-1 text-xs text-gray-900 dark:text-white">
                              {formatDate(order.date || '')}
                            </td>
                            <td className="px-2 py-1 text-xs text-gray-900 dark:text-white font-mono">
                              ${formatPrice(order.price || 0)}
                            </td>
                            <td className="px-2 py-1 text-xs text-gray-900 dark:text-white font-mono">
                              {formatQuantity(order.quantity || 0)}
                            </td>
                            <td className="px-2 py-1 text-xs text-gray-900 dark:text-white font-mono">
                              ${formatValue(order.value || 0)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            );
          } catch (error) {
            return (
              <div key={index} className="bg-red-50 dark:bg-red-900 rounded-lg shadow-md p-3 w-full">
                <h2 className="text-lg font-bold text-red-800 dark:text-red-200 mb-2">
                  Error rendering {asset?.symbol || 'Unknown'} asset
                </h2>
                <p className="text-sm text-red-600 dark:text-red-400">
                  Unable to display asset data
                </p>
              </div>
            );
          }
        })}
      </div>

      {/* Refresh Button */}
      <div className="text-center mt-4">
        <button 
          onClick={fetchAssetOverview}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 transition-colors text-sm"
        >
          Refresh Overview
        </button>
      </div>
    </div>
  );
};

export default AssetOverview; 