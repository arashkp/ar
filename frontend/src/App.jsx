import './App.css';
import { useState, useEffect } from 'react';
import DashboardPage from './pages/DashboardPage.jsx';
import AssetOverview from './pages/BackwardAnalysis.jsx';
import Navigation from './components/Navigation.jsx';
import LoginForm from './components/LoginForm.jsx';
import TelegramControl from './components/TelegramControl.jsx';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [apiKey, setApiKey] = useState('');

  useEffect(() => {
    // Check if API key exists in localStorage
    const storedApiKey = localStorage.getItem('apiKey');
    if (storedApiKey) {
      // Verify the stored API key
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      fetch(`${apiBaseUrl}/health`, {
        headers: {
          'X-API-Key': storedApiKey
        }
      })
      .then(response => {
        if (response.ok) {
          return response.json();
        } else {
          throw new Error('Invalid API key');
        }
      })
      .then(data => {
        // Check if the response contains the expected message
        if (data && data.message && data.message.includes('AR Trading API is running')) {
          setIsAuthenticated(true);
          setApiKey(storedApiKey);
        } else {
          throw new Error('Invalid API key');
        }
      })
      .catch(() => {
        localStorage.removeItem('apiKey');
      });
    }
  }, []);

  const handleLogin = (key) => {
    setIsAuthenticated(true);
    setApiKey(key);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setApiKey('');
    localStorage.removeItem('apiKey');
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage />;
      case 'asset-overview':
        return <AssetOverview />;
      case 'telegram':
        return <TelegramControl />;
      default:
        return <DashboardPage />;
    }
  };

  if (!isAuthenticated) {
    return <LoginForm onLogin={handleLogin} />;
  }

  return (
    <div className="w-full min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 transition-colors duration-200">
      <Navigation currentPage={currentPage} onPageChange={setCurrentPage} onLogout={handleLogout} />
      {renderPage()}
    </div>
  );
}

export default App;
