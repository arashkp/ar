import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TelegramControl = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [intervalHours, setIntervalHours] = useState(3);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const apiKey = localStorage.getItem('apiKey');
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      
      const response = await axios.get(`${apiBaseUrl}/telegram/status`, {
        headers: {
          'X-API-Key': apiKey
        }
      });
      
      setStatus(response.data.data);
    } catch (error) {
      console.error('Error fetching telegram status:', error);
    }
  };

  const sendTestMessage = async () => {
    setLoading(true);
    try {
      const apiKey = localStorage.getItem('apiKey');
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      
      const payload = message ? { message } : {};
      
      await axios.post(`${apiBaseUrl}/telegram/test`, payload, {
        headers: {
          'X-API-Key': apiKey
        }
      });
      
      alert('Test message sent successfully!');
      setMessage('');
    } catch (error) {
      alert('Error sending test message: ' + error.response?.data?.detail || error.message);
    } finally {
      setLoading(false);
    }
  };

  const sendMarketReport = async () => {
    setLoading(true);
    try {
      const apiKey = localStorage.getItem('apiKey');
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      
      await axios.post(`${apiBaseUrl}/telegram/report`, {}, {
        headers: {
          'X-API-Key': apiKey
        }
      });
      
      alert('Market report sent successfully!');
    } catch (error) {
      alert('Error sending market report: ' + error.response?.data?.detail || error.message);
    } finally {
      setLoading(false);
    }
  };

  const controlScheduler = async (action) => {
    setLoading(true);
    try {
      const apiKey = localStorage.getItem('apiKey');
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      
      await axios.post(`${apiBaseUrl}/telegram/scheduler`, {
        action,
        interval_hours: intervalHours
      }, {
        headers: {
          'X-API-Key': apiKey
        }
      });
      
      alert(`Scheduler ${action}ed successfully!`);
      fetchStatus(); // Refresh status
    } catch (error) {
      alert(`Error ${action}ing scheduler: ` + error.response?.data?.detail || error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
        🤖 Telegram Bot Control
      </h2>
      
      {/* Status */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Bot Status
        </h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex items-center">
            <span className="text-gray-600 dark:text-gray-400">Bot Configured:</span>
            <span className={`ml-2 px-2 py-1 rounded text-xs ${
              status?.bot_configured 
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
            }`}>
              {status?.bot_configured ? '✅ Yes' : '❌ No'}
            </span>
          </div>
          <div className="flex items-center">
            <span className="text-gray-600 dark:text-gray-400">Scheduler:</span>
            <span className={`ml-2 px-2 py-1 rounded text-xs ${
              status?.scheduler_running 
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
            }`}>
              {status?.scheduler_running ? '🟢 Running' : '⚪ Stopped'}
            </span>
          </div>
        </div>
      </div>

      {/* Test Message */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Test Message
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Custom message (optional)"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
          <button
            onClick={sendTestMessage}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Sending...' : 'Send Test'}
          </button>
        </div>
      </div>

      {/* Market Report */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Market Report
        </h3>
        <button
          onClick={sendMarketReport}
          disabled={loading}
          className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? 'Sending...' : 'Send Report'}
        </button>
      </div>

      {/* Scheduler Control */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Scheduled Reports
        </h3>
        <div className="flex items-center gap-4 mb-4">
          <label className="text-gray-600 dark:text-gray-400">
            Interval (hours):
          </label>
          <input
            type="number"
            min="1"
            max="24"
            value={intervalHours}
            onChange={(e) => setIntervalHours(parseInt(e.target.value))}
            className="w-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => controlScheduler('start')}
            disabled={loading || status?.scheduler_running}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
          >
            Start Scheduler
          </button>
          <button
            onClick={() => controlScheduler('stop')}
            disabled={loading || !status?.scheduler_running}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
          >
            Stop Scheduler
          </button>
        </div>
      </div>
    </div>
  );
};

export default TelegramControl; 