import React, { useState, useEffect } from 'react';
import axios from 'axios';

const AssetOverview = () => {
  const [assetData, setAssetData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentOrders, setCurrentOrders] = useState({});
  const [bitgetAvailable, setBitgetAvailable] = useState(false);

  // Check if Bitget API is available
  const checkBitgetAvailability = async () => {
    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const apiKey = localStorage.getItem('apiKey');
      const headers = apiKey ? { 'X-API-Key': apiKey } : {};
      
      const response = await axios.get(`${apiBaseUrl}/api/v1/bitget/balance`, { headers });
      return response.status === 200;
    } catch (error) {
      // If we get 503 (Service Unavailable), Bitget is not configured
      if (error.response?.status === 503) {
        return false;
      }
      // For other errors, assume Bitget might be available but having issues
      return true;
    }
  };

  const fetchAssetOverview = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const apiKey = localStorage.getItem('apiKey');
      const headers = apiKey ? { 'X-API-Key': apiKey } : {};
      
      // Check Bitget availability first
      const isBitgetAvailable = await checkBitgetAvailability();
      setBitgetAvailable(isBitgetAvailable);
      
      // Prepare API calls based on availability
      const apiCalls = [
        // Always call Bitunix
        axios.get(`${apiBaseUrl}/api/v1/spot-trades/backward-analysis`, { headers }),
        axios.get(`${apiBaseUrl}/api/v1/spot-trades/orders`, { headers })
      ];
      
      // Only add Bitget calls if available
      if (isBitgetAvailable) {
        apiCalls.push(
          axios.get(`${apiBaseUrl}/api/v1/bitget/backward-analysis?symbol=HYPE/USDT`, { headers }),
          axios.get(`${apiBaseUrl}/api/v1/bitget/orders`, { headers }),
          axios.get(`${apiBaseUrl}/api/v1/bitget/balance`, { headers })
        );
      }
      
      const responses = await Promise.allSettled(apiCalls);
      
      // Handle Bitunix data (always available)
      let bitunixData = null;
      let bitunixOrders = [];
      
      if (responses[0].status === 'fulfilled') {
        bitunixData = responses[0].value.data;
      } else {
        console.error('Bitunix error:', responses[0].reason);
      }
      
      if (responses[1].status === 'fulfilled') {
        bitunixOrders = responses[1].value.data;
      } else {
        console.error('Bitunix orders error:', responses[1].reason);
      }
      
      // Handle Bitget data (only if available)
      let bitgetData = null;
      let bitgetOrders = [];
      let bitgetBalance = null;
      
      if (isBitgetAvailable) {
        if (responses[2].status === 'fulfilled') {
          bitgetData = responses[2].value.data;
        } else {
          console.error('Bitget error:', responses[2].reason);
        }
        
        if (responses[3].status === 'fulfilled') {
          bitgetOrders = responses[3].value.data;
        } else {
          console.error('Bitget orders error:', responses[3].reason);
        }
        
        if (responses[4].status === 'fulfilled') {
          bitgetBalance = responses[4].value.data;
        } else {
          console.error('Bitget balance error:', responses[4].reason);
        }
      }

      // Combine the data
      let combinedData = { ...bitunixData };
      
      if (bitgetData && bitgetData.current_balance > 0) {
        // Convert Bitget HYPE data to match Bitunix asset format
        const hypeAsset = {
          symbol: 'HYPE (BGet)',
          current_balance: bitgetData.current_balance,
          current_price: bitgetData.current_price,
          average_entry_price: bitgetData.average_entry_price,
          total_buy_quantity: bitgetData.total_buy_amount,
          total_buy_value: bitgetData.total_buy_cost,
          unrealized_pnl: bitgetData.unrealized_pnl,
          unrealized_pnl_percentage: bitgetData.unrealized_pnl_percentage,
          number_of_orders: bitgetData.number_of_orders,
          relevant_orders: bitgetData.relevant_orders.map(trade => ({
            date: new Date(trade.timestamp).toISOString(),
            price: trade.price,
            quantity: trade.amount,
            value: trade.cost
          }))
        };

        // Add HYPE asset to the combined data
        if (combinedData.assets) {
          combinedData.assets.push(hypeAsset);
        } else {
          combinedData.assets = [hypeAsset];
        }
      }

      // Organize current orders by symbol
      const ordersBySymbol = {};
      
             // Process Bitunix orders
       bitunixOrders.forEach(order => {
         // Store orders by both base symbol and full symbol for flexible matching
         const baseSymbol = order.symbol.split('/')[0];
         const fullSymbol = order.symbol;
         
         // Store under base symbol (e.g., "BTC")
         if (!ordersBySymbol[baseSymbol]) {
           ordersBySymbol[baseSymbol] = [];
         }
         ordersBySymbol[baseSymbol].push({
           ...order,
           exchange: 'Bitunix'
         });
         
         // Also store under full symbol (e.g., "BTC/USDT")
         if (!ordersBySymbol[fullSymbol]) {
           ordersBySymbol[fullSymbol] = [];
         }
         ordersBySymbol[fullSymbol].push({
           ...order,
           exchange: 'Bitunix'
         });
       });

       // Process Bitget orders
       bitgetOrders.forEach(order => {
         // Store orders by both base symbol and full symbol for flexible matching
         const baseSymbol = order.symbol.split('/')[0];
         const fullSymbol = order.symbol;
         
         // Store under base symbol (e.g., "HYPE")
         if (!ordersBySymbol[baseSymbol]) {
           ordersBySymbol[baseSymbol] = [];
         }
         ordersBySymbol[baseSymbol].push({
           ...order,
           exchange: 'Bitget'
         });
         
         // Also store under full symbol (e.g., "HYPE/USDT")
         if (!ordersBySymbol[fullSymbol]) {
           ordersBySymbol[fullSymbol] = [];
         }
         ordersBySymbol[fullSymbol].push({
           ...order,
           exchange: 'Bitget'
         });
       });

       console.log('Current orders by symbol:', ordersBySymbol);
       setCurrentOrders(ordersBySymbol);
       setAssetData(combinedData);
       // Store Bitget balance for USDT calculation
       if (bitgetBalance) {
         // Add Bitget USDT balance to the combined data
         if (combinedData.assets) {
           const existingUsdt = combinedData.assets.find(asset => asset.symbol === 'USDT');
           if (existingUsdt) {
             existingUsdt.current_balance += bitgetBalance.USDT || 0;
           } else {
             combinedData.assets.push({
               symbol: 'USDT',
               current_balance: bitgetBalance.USDT || 0,
               current_price: 1,
               average_entry_price: 1,
               total_buy_quantity: bitgetBalance.USDT || 0,
               total_buy_value: bitgetBalance.USDT || 0,
               unrealized_pnl: 0,
               unrealized_pnl_percentage: 0,
               number_of_orders: 0,
               relevant_orders: []
             });
           }
         }
       }
     } catch (error) {
       console.error('Error fetching asset overview:', error);
       setError('Failed to fetch asset overview');
     } finally {
       setLoading(false);
     }
   };

   useEffect(() => {
     fetchAssetOverview();
   }, []);

  const formatDate = (dateString) => {
    if (!dateString || dateString === '') return 'N/A';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'Invalid Date';
      // Use 24-hour format and compact date format
      return date.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      }) + ' ' + date.toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
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

  const formatOrderStatus = (status) => {
    switch (status?.toLowerCase()) {
      case 'open':
      case 'pending':
        return 'Open';
      case 'filled':
      case 'closed':
        return 'Filled';
      case 'cancelled':
      case 'canceled':
        return 'Cancelled';
      case 'partially_filled':
        return 'Partial';
      default:
        return status || 'Unknown';
    }
  };

  const getOrderStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'open':
      case 'pending':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'filled':
      case 'closed':
        return 'text-green-600 dark:text-green-400';
      case 'cancelled':
      case 'canceled':
        return 'text-red-600 dark:text-red-400';
      case 'partially_filled':
        return 'text-orange-600 dark:text-orange-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getBitunixUsdtBalance = () => {
    if (!assetData || !assetData.assets) return 0;
    // Find USDT balance from Bitunix assets only
    const usdtAsset = assetData.assets.find(asset => asset.symbol === 'USDT');
    return usdtAsset ? usdtAsset.current_balance : 0;
  };

     const getBitgetUsdtBalance = () => {
     try {
       const bitgetBalanceStr = localStorage.getItem('bitgetBalance');
       if (bitgetBalanceStr) {
         const bitgetBalance = JSON.parse(bitgetBalanceStr);
         // Get USDT free balance (available for trading)
         if (bitgetBalance.USDT && bitgetBalance.USDT.free !== undefined) {
           return bitgetBalance.USDT.free;
         }
       }
     } catch (error) {
       console.error('Error getting Bitget USDT balance:', error);
     }
     return 0;
   };

  const calculateBitunixTotalCost = () => {
    if (!assetData || !assetData.assets) return 0;
    const cryptoCost = assetData.assets
      .filter(asset => asset.symbol !== 'USDT' && !asset.symbol.includes('(BGet)') && asset.total_buy_value !== undefined)
      .reduce((total, asset) => total + (asset.total_buy_value || 0), 0);
    return cryptoCost;
  };

  const calculateBitunixTotalCurrentValue = () => {
    if (!assetData || !assetData.assets) return 0;
    const cryptoValue = assetData.assets
      .filter(asset => asset.symbol !== 'USDT' && !asset.symbol.includes('(BGet)') && asset.current_balance !== undefined && asset.current_price !== undefined)
      .reduce((total, asset) => {
        const currentValue = (asset.current_balance || 0) * (asset.current_price || 0);
        return total + currentValue;
      }, 0);
    return cryptoValue;
  };

  const calculateBitgetTotalCost = () => {
    if (!assetData || !assetData.assets) return 0;
    const cryptoCost = assetData.assets
      .filter(asset => asset.symbol.includes('(BGet)') && asset.total_buy_value !== undefined)
      .reduce((total, asset) => total + (asset.total_buy_value || 0), 0);
    return cryptoCost;
  };

  const calculateBitgetTotalCurrentValue = () => {
    if (!assetData || !assetData.assets) return 0;
    const cryptoValue = assetData.assets
      .filter(asset => asset.symbol.includes('(BGet)') && asset.current_balance !== undefined && asset.current_price !== undefined)
      .reduce((total, asset) => {
        const currentValue = (asset.current_balance || 0) * (asset.current_price || 0);
        return total + currentValue;
      }, 0);
    return cryptoValue;
  };

  if (loading) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Asset Overview</h2>
          <p className="text-gray-600 dark:text-gray-400">Loading asset overview data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
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

  if (!assetData || !assetData.assets) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Asset Overview</h2>
          <p className="text-gray-600 dark:text-gray-400">No asset data available</p>
        </div>
      </div>
    );
  }

  const bitunixUsdtBalance = getBitunixUsdtBalance();
  const bitgetUsdtBalance = getBitgetUsdtBalance();
  
  const bitunixTotalCost = calculateBitunixTotalCost();
  const bitunixTotalCurrentValue = calculateBitunixTotalCurrentValue();
  const bitunixTotalPnL = bitunixTotalCurrentValue - bitunixTotalCost;
  const bitunixTotalPnLPercentage = bitunixTotalCost > 0 ? (bitunixTotalPnL / bitunixTotalCost) * 100 : 0;
  
  const bitgetTotalCost = calculateBitgetTotalCost();
  const bitgetTotalCurrentValue = calculateBitgetTotalCurrentValue();
  const bitgetTotalPnL = bitgetTotalCurrentValue - bitgetTotalCost;
  const bitgetTotalPnLPercentage = bitgetTotalCost > 0 ? (bitgetTotalPnL / bitgetTotalCost) * 100 : 0;
  
  return (
    <div className="w-full h-full p-2">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-white mb-1">Asset Overview</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Balance-relevant orders and calculations for all assets
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-500">
          Last updated: {assetData.timestamp ? formatDate(assetData.timestamp) : 'N/A'}
        </p>
        {!bitgetAvailable && (
          <div className="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
            <p className="text-xs text-yellow-700 dark:text-yellow-300">
              ⚠️ Bitget API not configured. Only Bitunix data is displayed.
            </p>
          </div>
        )}
      </div>

             {/* Portfolio Summary - Split into Bitunix and Bitget side by side */}
       <div className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
         {/* Bitunix Summary */}
         <div className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow-md">
           <h2 className="text-lg font-bold text-gray-800 dark:text-white mb-3 flex items-center">
             <span className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded text-xs mr-2">
               Bitunix
             </span>
             Portfolio Summary
           </h2>
           <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
             <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
               <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">USDT Balance</div>
               <div className="text-xl font-bold text-gray-900 dark:text-white">${formatValue(bitunixUsdtBalance)}</div>
               <div className="text-xs text-gray-500 dark:text-gray-500">Available USDT</div>
             </div>
             <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
               <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">Total Cost</div>
               <div className="text-xl font-bold text-gray-900 dark:text-white">${formatValue(bitunixTotalCost)}</div>
               <div className="text-xs text-gray-500 dark:text-gray-500">Crypto invested</div>
               <div className="text-xs text-gray-400 dark:text-gray-400 mt-1">
                 + ${formatValue(bitunixUsdtBalance)} USDT = ${formatValue(bitunixTotalCost + bitunixUsdtBalance)}
               </div>
             </div>
             <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
               <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">Current Value</div>
               <div className="text-xl font-bold text-gray-900 dark:text-white">${formatValue(bitunixTotalCurrentValue)}</div>
               <div className="text-xs text-gray-500 dark:text-gray-500">Total crypto value now</div>
               <div className="text-xs text-gray-400 dark:text-gray-400 mt-1">
                 + ${formatValue(bitunixUsdtBalance)} USDT = ${formatValue(bitunixTotalCurrentValue + bitunixUsdtBalance)}
               </div>
             </div>
             <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
               <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">Total P&L</div>
               <div className={`text-xl font-bold ${bitunixTotalPnL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                 ${formatValue(bitunixTotalPnL)} ({bitunixTotalPnLPercentage.toFixed(2)}%)
               </div>
               <div className="text-xs text-gray-500 dark:text-gray-500">Overall profit/loss</div>
             </div>
           </div>
         </div>

         {/* Bitget Summary */}
         <div className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow-md">
           <h2 className="text-lg font-bold text-gray-800 dark:text-white mb-3 flex items-center">
             <span className="bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 px-2 py-1 rounded text-xs mr-2">
               Bitget
             </span>
             Portfolio Summary
           </h2>
           {bitgetAvailable ? (
             <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
               <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                 <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">USDT Balance</div>
                 <div className="text-xl font-bold text-gray-900 dark:text-white">${formatValue(bitgetUsdtBalance)}</div>
                 <div className="text-xs text-gray-500 dark:text-gray-500">Available USDT</div>
               </div>
               <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                 <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">Total Cost</div>
                 <div className="text-xl font-bold text-gray-900 dark:text-white">${formatValue(bitgetTotalCost)}</div>
                 <div className="text-xs text-gray-500 dark:text-gray-500">Crypto invested</div>
                 <div className="text-xs text-gray-400 dark:text-gray-400 mt-1">
                   + ${formatValue(bitgetUsdtBalance)} USDT = ${formatValue(bitgetTotalCost + bitgetUsdtBalance)}
                 </div>
               </div>
               <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                 <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">Current Value</div>
                 <div className="text-xl font-bold text-gray-900 dark:text-white">${formatValue(bitgetTotalCurrentValue)}</div>
                 <div className="text-xs text-gray-500 dark:text-gray-500">Total crypto value now</div>
                 <div className="text-xs text-gray-400 dark:text-gray-400 mt-1">
                   + ${formatValue(bitgetUsdtBalance)} USDT = ${formatValue(bitgetTotalCurrentValue + bitgetUsdtBalance)}
                 </div>
               </div>
               <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                 <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">Total P&L</div>
                 <div className={`text-xl font-bold ${bitgetTotalPnL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                   ${formatValue(bitgetTotalPnL)} ({bitgetTotalPnLPercentage.toFixed(2)}%)
                 </div>
                 <div className="text-xs text-gray-500 dark:text-gray-500">Overall profit/loss</div>
               </div>
             </div>
           ) : (
             <div className="text-center p-6 bg-gray-50 dark:bg-gray-700 rounded-lg">
               <div className="text-sm text-gray-500 dark:text-gray-400">
                 Bitget API not configured
               </div>
               <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                 Set BITGET_API_KEY, BITGET_API_SECRET, and BITGET_PASSPHRASE environment variables
               </div>
             </div>
           )}
         </div>
       </div>

             {/* Assets Grid - Full width, 5 columns on extra large screens, 2 on large, 1 on mobile */}
       <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-5 gap-3 w-full">
        {assetData.assets
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
                         ${formatValue(asset.unrealized_pnl || 0)} ({(asset.unrealized_pnl_percentage || 0).toFixed(2)}%)
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

                                 {/* Current Orders Table */}
                 {(currentOrders[asset.symbol] || 
                   (asset.symbol === 'HYPE (BGet)' && currentOrders['HYPE']) ||
                   (asset.symbol.includes('(BGet)') && currentOrders[asset.symbol.replace(' (BGet)', '')]) ||
                   currentOrders[asset.symbol.replace('/USDT', '')] ||
                   currentOrders[asset.symbol.replace('/USDT', '') + '/USDT']
                  ) && (currentOrders[asset.symbol] || 
                        (asset.symbol === 'HYPE (BGet)' && currentOrders['HYPE']) ||
                        (asset.symbol.includes('(BGet)') && currentOrders[asset.symbol.replace(' (BGet)', '')]) ||
                        currentOrders[asset.symbol.replace('/USDT', '')] ||
                        currentOrders[asset.symbol.replace('/USDT', '') + '/USDT']
                       ).length > 0 && (
                                        <div className="mb-3 w-full">
                       <h3 className="text-sm font-semibold mb-1 text-gray-800 dark:text-white">
                         Current Orders ({(currentOrders[asset.symbol] || 
                           (asset.symbol === 'HYPE (BGet)' && currentOrders['HYPE']) ||
                           (asset.symbol.includes('(BGet)') && currentOrders[asset.symbol.replace(' (BGet)', '')]) ||
                           currentOrders[asset.symbol.replace('/USDT', '')] ||
                           currentOrders[asset.symbol.replace('/USDT', '') + '/USDT']
                          ).length})
                       </h3>
                       <div className="w-full">
                         <table className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
                           <thead className="bg-gray-50 dark:bg-gray-700">
                             <tr>
                               <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                 Side
                               </th>
                               <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                 Type
                               </th>
                               <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                 Price
                               </th>
                               <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                 Qty
                               </th>
                               <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                 Filled
                               </th>
                               <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                 Status
                               </th>
                             </tr>
                           </thead>
                           <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                                          {(currentOrders[asset.symbol] || 
                               (asset.symbol === 'HYPE (BGet)' && currentOrders['HYPE']) ||
                               (asset.symbol.includes('(BGet)') && currentOrders[asset.symbol.replace(' (BGet)', '')]) ||
                               currentOrders[asset.symbol.replace('/USDT', '')] ||
                               currentOrders[asset.symbol.replace('/USDT', '') + '/USDT']
                              ).map((order, orderIndex) => (
                               <tr key={orderIndex} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                 <td className={`px-2 py-1 text-xs font-mono ${order.side?.toLowerCase() === 'buy' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                   {order.side?.toUpperCase() || 'N/A'}
                                 </td>
                               <td className="px-2 py-1 text-xs text-gray-900 dark:text-white font-mono">
                                 {order.order_type || order.type || 'N/A'}
                               </td>
                               <td className="px-2 py-1 text-xs text-gray-900 dark:text-white font-mono">
                                 ${formatPrice(order.price || 0)}
                               </td>
                               <td className="px-2 py-1 text-xs text-gray-900 dark:text-white font-mono">
                                 {formatQuantity(order.quantity || order.amount || 0)}
                               </td>
                               <td className="px-2 py-1 text-xs text-gray-900 dark:text-white font-mono">
                                 {formatQuantity(order.filled_quantity || 0)}
                               </td>
                               <td className={`px-2 py-1 text-xs font-mono ${getOrderStatusColor(order.status)}`}>
                                 {formatOrderStatus(order.status)}
                               </td>
                             </tr>
                           ))}
                         </tbody>
                       </table>
                     </div>
                   </div>
                 )}

                 {/* History Orders Table - Show ALL orders */}
                 <div className="mb-3 w-full">
                   <h3 className="text-sm font-semibold mb-1 text-gray-800 dark:text-white">
                     History Orders ({asset.number_of_orders || 0})
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