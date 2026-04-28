import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, DollarSign, ArrowUp, ArrowDown, Briefcase, BrainCircuit, Loader, BarChart3, Building } from 'lucide-react';
import api from '../lib/api';
import StockChart from '../components/StockChart';
import PredictionCard from '../components/PredictionCard';
import SentimentPanel from '../components/SentimentPanel';
import TechnicalIndicators from '../components/TechnicalIndicators';

const WATCHLIST = ["AAPL", "MSFT", "GOOGL", "RELIANCE.NS", "TCS.NS", "TSLA", "^NSEI", "^GSPC"];

const StockLogo = ({ symbol, className }) => {
  const [err, setErr] = useState(false);
  if (!symbol || symbol.startsWith('^') || err) {
    return <div className={`flex items-center justify-center bg-slate-200 dark:bg-gray-700 rounded-full ${className}`}><Building className="text-slate-500 dark:text-gray-400" size="60%" /></div>;
  }
  return <img src={`https://api.twelvedata.com/logo/${symbol.split('.')[0]}.png`} alt="" className={className} onError={() => setErr(true)} />;
};

const InfoCard = ({ title, value, icon: Icon, color = 'slate', change, changePercent }) => (
  <div className="bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800 rounded-xl p-5">
    <div className="flex items-center justify-between mb-2">
      <span className="text-slate-500 dark:text-gray-400 text-sm font-medium">{title}</span>
      <Icon className={`text-${color}-500`} size={20} />
    </div>
    <div className="text-3xl font-bold text-slate-800 dark:text-gray-100">{value}</div>
    {change != null && (
      <div className={`text-sm mt-1 font-semibold flex items-center gap-1 ${change >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
        {change >= 0 ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
        {Math.abs(change).toFixed(2)} ({changePercent?.toFixed(2)}%)
      </div>
    )}
  </div>
);

const DashboardPage = () => {
  const [symbol, setSymbol] = useState('');
  const [active, setActive] = useState('MSFT');
  const [stockData, setStockData] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const search = async (sym) => {
    if (!sym?.trim()) return;
    setLoading(true); setError(''); setPrediction(null);
    const upper = sym.toUpperCase();
    setActive(upper);
    try {
      const { data } = await api.get(`/api/stocks/${upper}`);
      setStockData(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      setStockData(null);
    } finally { setLoading(false); }
  };

  useEffect(() => { search(active); }, []);

  const predict = async () => {
    setLoading(true); setError('');
    try {
      const { data } = await api.post('/api/predict', { symbol: active });
      setPrediction(data);
    } catch (e) { setError(e.response?.data?.detail || e.message); }
    finally { setLoading(false); }
  };

  const lastDaily = stockData?.prices?.[0];
  const price = lastDaily?.close ?? 0;
  const change = lastDaily ? (lastDaily.close - (stockData.prices[1]?.close ?? 0)) : 0;
  const changePct = price ? (change / (stockData?.prices[1]?.close ?? 1)) * 100 : 0;

  return (
    <div className="flex min-h-[calc(100vh-4rem)]">
      {/* Sidebar */}
      <aside className="hidden lg:flex w-64 flex-col border-r border-slate-200 dark:border-gray-800 bg-white/50 dark:bg-gray-950/30 p-4 shrink-0">
        <form onSubmit={e => { e.preventDefault(); search(symbol); }} className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input type="text" value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="Search symbol..."
            className="w-full pl-9 pr-3 py-2 bg-slate-100 dark:bg-gray-800 border border-slate-200 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-sm transition" />
        </form>
        <p className="text-xs font-semibold text-slate-500 dark:text-gray-500 mb-2 px-1">WATCHLIST</p>
        <div className="flex flex-col gap-1">
          {WATCHLIST.map(s => (
            <button key={s} onClick={() => search(s)}
              className={`flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-lg transition ${active === s ? 'bg-indigo-600/10 text-indigo-600 dark:text-indigo-400' : 'hover:bg-slate-100 dark:hover:bg-gray-800 text-slate-600 dark:text-gray-400'}`}>
              <StockLogo symbol={s} className="w-6 h-6 rounded-full" />
              <span>{s}</span>
            </button>
          ))}
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 p-6 lg:p-8 overflow-y-auto relative">
        <AnimatePresence>
          {loading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="absolute inset-0 bg-white/50 dark:bg-gray-900/50 flex items-center justify-center z-20 backdrop-blur-sm">
              <Loader className="animate-spin text-indigo-500" size={40} />
            </motion.div>
          )}
        </AnimatePresence>

        {error && !loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-6 text-sm">{error}</motion.div>
        )}

        {stockData ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            <header className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-4">
                <StockLogo symbol={stockData.symbol} className="w-12 h-12 rounded-full" />
                <div>
                  <h1 className="text-3xl font-bold text-slate-800 dark:text-gray-100">{stockData.symbol}</h1>
                  <p className="text-slate-500 dark:text-gray-400">{stockData.company_name}</p>
                </div>
              </div>
              {lastDaily?.date && (
                <div className="text-right text-sm text-slate-500 dark:text-gray-500">
                  <span className="font-medium">{new Date(lastDaily.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
                </div>
              )}
            </header>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <InfoCard title="Close Price" value={price ? `$${price.toFixed(2)}` : '--'} icon={DollarSign} change={change} changePercent={changePct} />
              <InfoCard title="Day High" value={lastDaily?.high ? `$${Number(lastDaily.high).toFixed(2)}` : '--'} icon={ArrowUp} color="emerald" />
              <InfoCard title="Day Low" value={lastDaily?.low ? `$${Number(lastDaily.low).toFixed(2)}` : '--'} icon={ArrowDown} color="red" />
              <InfoCard title="Volume" value={lastDaily?.volume ? `${(lastDaily.volume / 1e6).toFixed(2)}M` : '--'} icon={Briefcase} color="blue" />
            </div>

            <StockChart prices={stockData.prices} prediction={prediction?.predicted_next_day_close} />

            {!prediction ? (
              <motion.div whileHover={{ scale: 1.005 }} whileTap={{ scale: 0.995 }}>
                <button onClick={predict} disabled={loading}
                  className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3.5 rounded-xl font-semibold hover:from-indigo-700 hover:to-purple-700 transition disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20">
                  <BrainCircuit size={20} /> Predict Next Day's Close
                </button>
              </motion.div>
            ) : (
              <PredictionCard prediction={prediction} onClear={() => setPrediction(null)} />
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TechnicalIndicators prices={stockData.prices} />
              <SentimentPanel symbol={active} />
            </div>
          </motion.div>
        ) : (
          !loading && (
            <div className="flex flex-col items-center justify-center h-[60vh] text-slate-500 dark:text-gray-600">
              <BarChart3 size={48} className="mb-4" />
              <h2 className="text-xl font-semibold">No Data Available</h2>
              <p>Search for a stock symbol to get started.</p>
            </div>
          )
        )}
      </main>
    </div>
  );
};

export default DashboardPage;
