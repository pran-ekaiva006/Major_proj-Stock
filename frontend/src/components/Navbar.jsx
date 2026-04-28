import { NavLink, useNavigate } from 'react-router-dom';
import { TrendingUp, LayoutDashboard, LineChart, BrainCircuit, Briefcase, LogIn, LogOut, Sun, Moon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useState, useEffect } from 'react';

const useTheme = () => {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
    localStorage.setItem('theme', theme);
  }, [theme]);
  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    if (document.startViewTransition) document.startViewTransition(() => setTheme(next));
    else setTheme(next);
  };
  return [theme, toggle];
};

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/analysis', icon: LineChart, label: 'Analysis' },
  { to: '/models', icon: BrainCircuit, label: 'Model Insights' },
  { to: '/portfolio', icon: Briefcase, label: 'Portfolio' },
];

const Navbar = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const [theme, toggleTheme] = useTheme();
  const navigate = useNavigate();

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-slate-200 dark:border-gray-800 bg-white/80 dark:bg-gray-950/80 backdrop-blur-xl">
      <div className="max-w-[1440px] mx-auto flex items-center justify-between h-16 px-6">
        {/* Logo */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
          <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/25">
            <TrendingUp className="text-white" size={20} />
          </div>
          <span className="text-lg font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            AlphaPredict
          </span>
        </div>

        {/* Nav Links */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-indigo-600/10 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-400'
                    : 'text-slate-600 dark:text-gray-400 hover:bg-slate-100 dark:hover:bg-gray-800 hover:text-slate-900 dark:hover:text-gray-200'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </div>

        {/* Right Side */}
        <div className="flex items-center gap-3">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-gray-800 transition"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={18} className="text-yellow-400" /> : <Moon size={18} className="text-slate-600" />}
          </button>

          {isAuthenticated ? (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold">
                {user?.username?.[0]?.toUpperCase() || 'U'}
              </div>
              <span className="hidden sm:block text-sm font-medium text-slate-700 dark:text-gray-300">
                {user?.username}
              </span>
              <button
                onClick={logout}
                className="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500 transition"
                title="Logout"
              >
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => navigate('/login')}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition shadow-lg shadow-indigo-600/25"
            >
              <LogIn size={16} />
              Sign In
            </button>
          )}
        </div>
      </div>

      {/* Mobile Nav */}
      <div className="md:hidden flex items-center gap-1 px-4 pb-2 overflow-x-auto">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                isActive
                  ? 'bg-indigo-600/10 text-indigo-600 dark:text-indigo-400'
                  : 'text-slate-500 dark:text-gray-500'
              }`
            }
          >
            <Icon size={14} />
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
};

export default Navbar;
