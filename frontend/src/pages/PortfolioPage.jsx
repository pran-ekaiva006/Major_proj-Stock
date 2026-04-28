import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Briefcase, Plus, Trash2, History, TrendingUp, Loader, LogIn } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import toast from 'react-hot-toast';

const PortfolioPage = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [watchlist, setWatchlist] = useState([]);
  const [history, setHistory] = useState([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) { setLoading(false); return; }
    Promise.all([
      api.get('/api/watchlist').catch(() => ({ data: [] })),
      api.get('/api/predictions/history').catch(() => ({ data: [] })),
    ]).then(([w, h]) => {
      setWatchlist(w.data);
      setHistory(h.data);
    }).finally(() => setLoading(false));
  }, [isAuthenticated]);

  const addToWatchlist = async (e) => {
    e.preventDefault();
    if (!newSymbol.trim()) return;
    try {
      await api.post('/api/watchlist', { symbol: newSymbol.toUpperCase() });
      setWatchlist(prev => [{ symbol: newSymbol.toUpperCase(), added_at: new Date().toISOString() }, ...prev]);
      setNewSymbol('');
      toast.success(`${newSymbol.toUpperCase()} added to watchlist`);
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed to add'); }
  };

  const removeFromWatchlist = async (sym) => {
    try {
      await api.delete(`/api/watchlist/${sym}`);
      setWatchlist(prev => prev.filter(w => w.symbol !== sym));
      toast.success(`${sym} removed`);
    } catch (e) { toast.error('Failed to remove'); }
  };

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-slate-500 dark:text-gray-500">
        <Briefcase size={48} className="mb-4" />
        <h2 className="text-xl font-semibold mb-2">Sign in to access your portfolio</h2>
        <p className="text-sm mb-4">Track your watchlist and prediction history.</p>
        <button onClick={() => navigate('/login')}
          className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition">
          <LogIn size={18} /> Sign In
        </button>
      </div>
    );
  }

  if (loading) return <div className="flex justify-center items-center h-[60vh]"><Loader className="animate-spin text-indigo-500" size={40} /></div>;

  return (
    <div className="max-w-6xl mx-auto p-6 lg:p-8">
      <h1 className="text-3xl font-bold text-slate-800 dark:text-gray-100 mb-2">Portfolio</h1>
      <p className="text-slate-500 dark:text-gray-400 mb-8">Your watchlist and prediction history.</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Watchlist */}
        <div className="bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800 rounded-xl p-6">
          <h3 className="font-semibold text-slate-800 dark:text-gray-200 mb-4 flex items-center gap-2">
            <TrendingUp size={18} /> Watchlist
          </h3>
          <form onSubmit={addToWatchlist} className="flex gap-2 mb-4">
            <input type="text" value={newSymbol} onChange={e => setNewSymbol(e.target.value)}
              placeholder="Add symbol..." className="flex-1 px-3 py-2 bg-slate-50 dark:bg-gray-800 border border-slate-200 dark:border-gray-700 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
            <button type="submit" className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition">
              <Plus size={18} />
            </button>
          </form>
          {watchlist.length === 0 ? (
            <p className="text-sm text-slate-400 dark:text-gray-600 text-center py-8">No stocks in watchlist yet.</p>
          ) : (
            <div className="space-y-2">
              {watchlist.map(w => (
                <motion.div key={w.symbol} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="flex items-center justify-between p-3 bg-slate-50 dark:bg-gray-800/50 rounded-lg">
                  <div>
                    <span className="font-semibold text-slate-800 dark:text-gray-200">{w.symbol}</span>
                    {w.added_at && <span className="text-xs text-slate-400 ml-2">{new Date(w.added_at).toLocaleDateString()}</span>}
                  </div>
                  <button onClick={() => removeFromWatchlist(w.symbol)} className="p-1.5 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition">
                    <Trash2 size={16} />
                  </button>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Prediction History */}
        <div className="bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800 rounded-xl p-6">
          <h3 className="font-semibold text-slate-800 dark:text-gray-200 mb-4 flex items-center gap-2">
            <History size={18} /> Prediction History
          </h3>
          {history.length === 0 ? (
            <p className="text-sm text-slate-400 dark:text-gray-600 text-center py-8">No predictions made yet.</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {history.map(h => (
                <div key={h.id} className="p-3 bg-slate-50 dark:bg-gray-800/50 rounded-lg text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{h.symbol}</span>
                    <span className="text-xs text-slate-400">{h.predicted_at ? new Date(h.predicted_at).toLocaleDateString() : ''}</span>
                  </div>
                  <div className="flex items-center gap-4 mt-1 text-slate-600 dark:text-gray-400">
                    <span>Predicted: <strong className="text-indigo-500">${h.predicted_close?.toFixed(2)}</strong></span>
                    {h.actual_close && <span>Actual: <strong>${h.actual_close.toFixed(2)}</strong></span>}
                    {h.model_used && <span className="text-xs capitalize">{h.model_used.replace(/_/g, ' ')}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PortfolioPage;
