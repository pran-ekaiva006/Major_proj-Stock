import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BrainCircuit, Trophy, BarChart3, Loader } from 'lucide-react';
import api from '../lib/api';

const MetricBadge = ({ label, value, unit = '', best = false }) => (
  <div className={`text-center p-4 rounded-xl border ${best ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-slate-200 dark:border-gray-800 bg-white dark:bg-gray-950/50'}`}>
    <p className="text-xs text-slate-500 dark:text-gray-500 mb-1">{label}</p>
    <p className={`text-xl font-bold ${best ? 'text-emerald-500' : 'text-slate-800 dark:text-gray-200'}`}>{value}{unit}</p>
  </div>
);

const ModelInsightsPage = () => {
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/model-info')
      .then(res => setMeta(res.data))
      .catch(() => setMeta(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center h-[60vh]"><Loader className="animate-spin text-indigo-500" size={40} /></div>;
  }

  if (!meta) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-slate-500">
        <BrainCircuit size={48} className="mb-4" />
        <h2 className="text-xl font-semibold">No Model Data Available</h2>
        <p className="text-sm mt-2">Run <code className="bg-slate-200 dark:bg-gray-800 px-2 py-1 rounded">python ml_model/train.py</code> first.</p>
      </div>
    );
  }

  const results = meta.results || [];
  const bestModel = meta.best_model?.replace(/_/g, ' ') || 'Unknown';

  return (
    <div className="max-w-6xl mx-auto p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800 dark:text-gray-100 mb-2">Model Insights</h1>
        <p className="text-slate-500 dark:text-gray-400">Compare ML models trained on historical stock data with technical indicators.</p>
      </div>

      {/* Best Model Banner */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-indigo-600/10 to-purple-600/10 border border-indigo-500/20 rounded-xl p-6 mb-8">
        <div className="flex items-center gap-4">
          <Trophy className="text-amber-500" size={32} />
          <div>
            <p className="text-sm text-slate-500 dark:text-gray-400">Best Performing Model</p>
            <h2 className="text-2xl font-bold text-slate-800 dark:text-gray-100 capitalize">{bestModel}</h2>
            <p className="text-sm text-slate-500 dark:text-gray-400 mt-1">
              R² = {meta.best_r2?.toFixed(4)} | Trained on {meta.train_samples?.toLocaleString()} samples | Tested on {meta.test_samples?.toLocaleString()} samples
            </p>
          </div>
        </div>
      </motion.div>

      {/* Training Config */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricBadge label="Training Samples" value={meta.train_samples?.toLocaleString()} />
        <MetricBadge label="Test Samples" value={meta.test_samples?.toLocaleString()} />
        <MetricBadge label="Features Used" value={meta.feature_columns?.length || 0} />
        <MetricBadge label="LSTM Sequence Length" value={meta.sequence_length || 60} />
      </div>

      {/* Comparison Table */}
      <div className="bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800 rounded-xl p-6 mb-8">
        <h3 className="font-semibold text-slate-800 dark:text-gray-200 mb-4 flex items-center gap-2">
          <BarChart3 size={18} /> Model Comparison
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-gray-800">
                <th className="text-left py-3 px-4 text-slate-500 dark:text-gray-500">Model</th>
                <th className="text-right py-3 px-4 text-slate-500 dark:text-gray-500">R²</th>
                <th className="text-right py-3 px-4 text-slate-500 dark:text-gray-500">MAE</th>
                <th className="text-right py-3 px-4 text-slate-500 dark:text-gray-500">RMSE</th>
                <th className="text-right py-3 px-4 text-slate-500 dark:text-gray-500">MAPE %</th>
                <th className="text-right py-3 px-4 text-slate-500 dark:text-gray-500">Dir. Accuracy %</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => {
                const isBest = r.Model?.toLowerCase().replace(/\s/g, '_') === meta.best_model;
                return (
                  <tr key={i} className={`border-b border-slate-100 dark:border-gray-800/50 transition ${isBest ? 'bg-emerald-500/5' : 'hover:bg-slate-50 dark:hover:bg-gray-800/30'}`}>
                    <td className="py-3 px-4 font-semibold text-slate-800 dark:text-gray-200 flex items-center gap-2">
                      {isBest && <Trophy size={14} className="text-amber-500" />}
                      {r.Model}
                    </td>
                    <td className="py-3 px-4 text-right font-mono">{r['R²']?.toFixed(4)}</td>
                    <td className="py-3 px-4 text-right font-mono">${r.MAE?.toFixed(4)}</td>
                    <td className="py-3 px-4 text-right font-mono">${r.RMSE?.toFixed(4)}</td>
                    <td className="py-3 px-4 text-right font-mono">{r['MAPE (%)']?.toFixed(2)}%</td>
                    <td className="py-3 px-4 text-right font-mono">{r['Directional Accuracy (%)']?.toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Feature List */}
      {meta.feature_columns && (
        <div className="bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800 rounded-xl p-6">
          <h3 className="font-semibold text-slate-800 dark:text-gray-200 mb-4">Feature Columns ({meta.feature_columns.length})</h3>
          <div className="flex flex-wrap gap-2">
            {meta.feature_columns.map(f => (
              <span key={f} className="px-3 py-1 bg-slate-100 dark:bg-gray-800 text-slate-700 dark:text-gray-300 text-xs font-mono rounded-lg">{f}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelInsightsPage;
