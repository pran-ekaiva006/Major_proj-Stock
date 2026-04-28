import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Newspaper, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import api from '../lib/api';

const SentimentPanel = ({ symbol }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    api.get(`/api/sentiment/${symbol}`)
      .then(res => setData(res.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [symbol]);

  if (loading) return <div className="animate-pulse h-48 bg-slate-200 dark:bg-gray-800 rounded-xl" />;
  if (!data || !data.headlines?.length) return null;

  const Icon = data.overall_category === 'bullish' ? TrendingUp : data.overall_category === 'bearish' ? TrendingDown : Minus;
  const color = data.overall_category === 'bullish' ? 'emerald' : data.overall_category === 'bearish' ? 'red' : 'amber';

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Newspaper size={18} className="text-slate-500" />
          <h3 className="font-semibold text-slate-800 dark:text-gray-200">News Sentiment</h3>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full bg-${color}-500/10`}>
          <Icon size={14} className={`text-${color}-500`} />
          <span className={`text-sm font-bold text-${color}-500 capitalize`}>{data.overall_category}</span>
          <span className={`text-xs text-${color}-500/70`}>({data.overall_score > 0 ? '+' : ''}{data.overall_score.toFixed(2)})</span>
        </div>
      </div>

      {/* Sentiment Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-slate-500 dark:text-gray-500 mb-1">
          <span>Bearish</span><span>Neutral</span><span>Bullish</span>
        </div>
        <div className="h-2 rounded-full bg-gradient-to-r from-red-500 via-amber-400 to-emerald-500 relative">
          <motion.div
            initial={{ left: '50%' }}
            animate={{ left: `${((data.overall_score + 1) / 2) * 100}%` }}
            transition={{ duration: 0.8 }}
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-white dark:bg-gray-900 border-2 border-slate-400 dark:border-gray-500 shadow"
          />
        </div>
      </div>

      {/* Headlines */}
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {data.headlines.slice(0, 6).map((h, i) => {
          const s = h.sentiment;
          const hColor = s.category === 'bullish' ? 'text-emerald-500' : s.category === 'bearish' ? 'text-red-500' : 'text-amber-500';
          return (
            <a key={i} href={h.url} target="_blank" rel="noopener noreferrer"
              className="block p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-gray-800/50 transition group">
              <div className="flex items-start gap-2">
                <span className={`text-xs font-mono font-bold mt-0.5 ${hColor}`}>
                  {s.compound > 0 ? '+' : ''}{s.compound.toFixed(2)}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-700 dark:text-gray-300 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 truncate">
                    {h.title}
                  </p>
                  <p className="text-xs text-slate-400 dark:text-gray-600">{h.source}</p>
                </div>
              </div>
            </a>
          );
        })}
      </div>
    </motion.div>
  );
};

export default SentimentPanel;
