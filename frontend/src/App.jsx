import './App.css';
import { useState } from 'react';
import DashboardPage from './pages/DashboardPage.jsx';
import AssetOverview from './pages/BackwardAnalysis.jsx';
import Navigation from './components/Navigation.jsx';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage />;
      case 'asset-overview':
        return <AssetOverview />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <div className="w-full min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 transition-colors duration-200">
      <Navigation currentPage={currentPage} onPageChange={setCurrentPage} />
      {renderPage()}
    </div>
  );
}

export default App;
