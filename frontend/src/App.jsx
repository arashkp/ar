import './App.css';
import DashboardPage from './pages/DashboardPage.jsx';
import ThemeToggleButton from './components/ThemeToggleButton'; // Import ThemeToggleButton

function App() {
  return (
    <div className="App bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 min-h-screen transition-colors duration-200">
      <ThemeToggleButton />
      <DashboardPage />
    </div>
  );
}

export default App;
