import { motion } from 'framer-motion';

const Gauge = ({ label, value, min = 0, max = 100, unit = '', color = 'indigo' }) => {
  const pct = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
  return (
    <div className="text-center">
      <p className="text-xs text-slate-500 dark:text-gray-500 mb-1">{label}</p>
      <div className="relative w-full h-2 rounded-full bg-slate-200 dark:bg-gray-800">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8 }}
          className={`h-full rounded-full bg-${color}-500`}
        />
      </div>
      <p className="text-sm font-bold text-slate-700 dark:text-gray-300 mt-1">{value?.toFixed(1)}{unit}</p>
    </div>
  );
};

const TechnicalIndicators = ({ prices }) => {
  if (!prices?.length) return null;

  const latest = prices[0];
  const prev = prices[1] || latest;
  const close = latest.close;
  const volume = latest.volume;

  // Calculate simple indicators from available data
  const closes = prices.slice(0, 20).map(p => p.close);
  const sma5 = closes.slice(0, 5).reduce((a, b) => a + b, 0) / Math.min(5, closes.length);
  const sma20 = closes.reduce((a, b) => a + b, 0) / closes.length;

  // RSI approximation
  const changes = closes.slice(0, 14).map((c, i) => i > 0 ? c - closes[i - 1] : 0).slice(1);
  const gains = changes.filter(c => c > 0);
  const losses = changes.filter(c => c < 0).map(c => Math.abs(c));
  const avgGain = gains.length ? gains.reduce((a, b) => a + b, 0) / 14 : 0;
  const avgLoss = losses.length ? losses.reduce((a, b) => a + b, 0) / 14 : 0.001;
  const rs = avgGain / avgLoss;
  const rsi = 100 - (100 / (1 + rs));

  // Volatility
  const returns = closes.slice(0, 10).map((c, i) => i > 0 ? (c - closes[i - 1]) / closes[i - 1] : 0).slice(1);
  const meanRet = returns.reduce((a, b) => a + b, 0) / returns.length;
  const volatility = Math.sqrt(returns.reduce((a, r) => a + (r - meanRet) ** 2, 0) / returns.length) * 100;

  const priceToSMA = ((close / sma20) - 1) * 100;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800 rounded-xl p-6">
      <h3 className="font-semibold text-slate-800 dark:text-gray-200 mb-4">Technical Indicators</h3>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <Gauge label="RSI (14)" value={rsi} min={0} max={100}
          color={rsi > 70 ? 'red' : rsi < 30 ? 'emerald' : 'indigo'} />

        <Gauge label="Volatility" value={volatility} min={0} max={5} unit="%"
          color={volatility > 3 ? 'red' : volatility > 1.5 ? 'amber' : 'emerald'} />

        <div className="text-center">
          <p className="text-xs text-slate-500 dark:text-gray-500 mb-1">Price vs SMA20</p>
          <p className={`text-lg font-bold ${priceToSMA > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
            {priceToSMA > 0 ? '+' : ''}{priceToSMA.toFixed(2)}%
          </p>
          <p className="text-xs text-slate-500">{priceToSMA > 0 ? 'Above' : 'Below'} average</p>
        </div>

        <div className="text-center">
          <p className="text-xs text-slate-500 dark:text-gray-500 mb-1">SMA 5 / SMA 20</p>
          <p className={`text-lg font-bold ${sma5 > sma20 ? 'text-emerald-500' : 'text-red-500'}`}>
            {sma5 > sma20 ? '▲ Bullish' : '▼ Bearish'}
          </p>
          <p className="text-xs text-slate-500">Crossover signal</p>
        </div>
      </div>

      {/* RSI interpretation */}
      <div className="mt-4 pt-3 border-t border-slate-200 dark:border-gray-800">
        <p className="text-xs text-slate-500 dark:text-gray-500">
          <strong>Signal: </strong>
          {rsi > 70 ? '⚠️ RSI overbought — potential pullback' :
           rsi < 30 ? '🟢 RSI oversold — potential buying opportunity' :
           '➡️ RSI neutral — no strong signal'}
          {sma5 > sma20 ? ' | SMA crossover is bullish' : ' | SMA crossover is bearish'}
        </p>
      </div>
    </motion.div>
  );
};

export default TechnicalIndicators;
