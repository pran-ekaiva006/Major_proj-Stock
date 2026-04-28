import { motion } from 'framer-motion';
import { Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react';

const PredictionCard = ({ prediction, onClear }) => {
  if (!prediction) return null;

  const predicted = prediction.predicted_next_day_close;
  const confidence = prediction.confidence;
  const modelUsed = prediction.model_used?.replace(/_/g, ' ') || 'ML Model';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800 rounded-xl p-6"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
            <Activity className="text-emerald-500" size={24} />
          </div>
          <div>
            <h3 className="font-bold text-xl text-slate-800 dark:text-gray-100">
              Predicted Next Close: <span className="text-emerald-500">${Number(predicted).toFixed(2)}</span>
            </h3>
            <p className="text-sm text-slate-500 dark:text-gray-400 mt-0.5">
              Model: <span className="capitalize font-medium">{modelUsed}</span>
              {confidence != null && (
                <span className="ml-3">
                  Confidence: <span className={`font-semibold ${confidence > 80 ? 'text-emerald-500' : confidence > 50 ? 'text-amber-500' : 'text-red-500'}`}>
                    {confidence}%
                  </span>
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Confidence Gauge */}
        {confidence != null && (
          <div className="hidden sm:flex flex-col items-center gap-1">
            <div className="w-24 h-2 rounded-full bg-slate-200 dark:bg-gray-800 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${confidence}%` }}
                transition={{ duration: 1, ease: 'easeOut' }}
                className={`h-full rounded-full ${confidence > 80 ? 'bg-emerald-500' : confidence > 50 ? 'bg-amber-500' : 'bg-red-500'}`}
              />
            </div>
            <span className="text-xs text-slate-500 dark:text-gray-500">R² confidence</span>
          </div>
        )}

        <button
          onClick={onClear}
          className="ml-4 bg-slate-200 dark:bg-gray-700 hover:bg-slate-300 dark:hover:bg-gray-600 text-sm font-semibold px-4 py-2 rounded-lg transition"
        >
          Clear
        </button>
      </div>

      {/* Model Metrics */}
      {prediction.metrics && (
        <div className="mt-4 pt-4 border-t border-slate-200 dark:border-gray-800 grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { label: 'R²', value: prediction.metrics.r2?.toFixed(4) },
            { label: 'MAE', value: prediction.metrics.mae ? `$${prediction.metrics.mae.toFixed(2)}` : null },
            { label: 'RMSE', value: prediction.metrics.rmse ? `$${prediction.metrics.rmse.toFixed(2)}` : null },
            { label: 'MAPE', value: prediction.metrics.mape ? `${prediction.metrics.mape.toFixed(1)}%` : null },
            { label: 'Dir. Accuracy', value: prediction.metrics.directional_accuracy ? `${prediction.metrics.directional_accuracy.toFixed(1)}%` : null },
          ].filter(m => m.value).map(({ label, value }) => (
            <div key={label} className="text-center">
              <p className="text-xs text-slate-500 dark:text-gray-500 mb-0.5">{label}</p>
              <p className="text-sm font-bold text-slate-700 dark:text-gray-300">{value}</p>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
};

export default PredictionCard;
