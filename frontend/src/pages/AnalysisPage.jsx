import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, LineChart, BarChart3 } from 'lucide-react';
import api from '../lib/api';
import StockChart from '../components/StockChart';
import TechnicalIndicators from '../components/TechnicalIndicators';
import SentimentPanel from '../components/SentimentPanel';

const AnalysisPage = () => {
  const [symbol, setSymbol] = useState('');
  const [active, setActive] = useState('');
  const [stockData, setStockData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const search = async (sym) => {
    if (!sym?.trim()) return;
    setLoading(true); setError('');
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

  return (
    <div className="max-w-6xl mx-auto p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800 dark:text-gray-100 mb-2">Stock Analysis</h1>
        <p className="text-slate-500 dark:text-gray-400">Deep dive into technical indicators and sentiment for any stock.</p>
      </div>

      <form onSubmit={e => { e.preventDefault(); search(symbol); }} className="relative max-w-lg mb-8">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
        <input type="text" value={symbol} onChange={e => setSymbol(e.target.value)}
          placeholder="Enter stock symbol (e.g. AAPL, RELIANCE.NS)"
          className="w-full pl-12 pr-4 py-3 bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none transition" />
      </form>

      {error && <div className="bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-6 text-sm">{error}</div>}

      {loading && <div className="flex justify-center py-20"><div className="animate-spin w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full" /></div>}

      {stockData && !loading && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
          <div className="flex items-center gap-3 mb-2">
            <LineChart className="text-indigo-500" size={24} />
            <h2 className="text-2xl font-bold text-slate-800 dark:text-gray-100">{stockData.symbol} — {stockData.company_name}</h2>
          </div>

          <StockChart prices={stockData.prices} height={450} showSMA />
          <TechnicalIndicators prices={stockData.prices} />
          <SentimentPanel symbol={active} />

          {/* Price History Table */}
          <div className="bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800 rounded-xl p-6">
            <h3 className="font-semibold text-slate-800 dark:text-gray-200 mb-4">Recent Price History</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-gray-800 text-slate-500 dark:text-gray-500">
                    <th className="text-left py-2 px-3">Date</th>
                    <th className="text-right py-2 px-3">Open</th>
                    <th className="text-right py-2 px-3">High</th>
                    <th className="text-right py-2 px-3">Low</th>
                    <th className="text-right py-2 px-3">Close</th>
                    <th className="text-right py-2 px-3">Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {stockData.prices.slice(0, 15).map((p, i) => (
                    <tr key={i} className="border-b border-slate-100 dark:border-gray-800/50 hover:bg-slate-50 dark:hover:bg-gray-800/30 transition">
                      <td className="py-2 px-3 text-slate-700 dark:text-gray-300">{new Date(p.date).toLocaleDateString()}</td>
                      <td className="py-2 px-3 text-right">${Number(p.open).toFixed(2)}</td>
                      <td className="py-2 px-3 text-right text-emerald-600">${Number(p.high).toFixed(2)}</td>
                      <td className="py-2 px-3 text-right text-red-500">${Number(p.low).toFixed(2)}</td>
                      <td className="py-2 px-3 text-right font-semibold">${Number(p.close).toFixed(2)}</td>
                      <td className="py-2 px-3 text-right text-slate-500">{(p.volume / 1e6).toFixed(2)}M</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      )}

      {!stockData && !loading && !error && (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400 dark:text-gray-600">
          <BarChart3 size={48} className="mb-4" />
          <p className="text-lg font-medium">Search for a stock to begin analysis</p>
        </div>
      )}
    </div>
  );
};

export default AnalysisPage;
