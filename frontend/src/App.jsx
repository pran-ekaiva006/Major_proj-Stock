import { BrowserRouter, Routes, Route, Outlet } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import AnalysisPage from './pages/AnalysisPage';
import ModelInsightsPage from './pages/ModelInsightsPage';
import PortfolioPage from './pages/PortfolioPage';

const Layout = () => (
  <>
    <Navbar />
    <Outlet />
  </>
);

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="min-h-screen w-full bg-slate-100 dark:bg-gray-900 text-slate-800 dark:text-gray-200 font-sans transition-colors duration-300">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<Layout />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="/models" element={<ModelInsightsPage />} />
              <Route path="/portfolio" element={<PortfolioPage />} />
            </Route>
          </Routes>
          <Toaster position="top-right" toastOptions={{
            style: { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155' },
          }} />
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
