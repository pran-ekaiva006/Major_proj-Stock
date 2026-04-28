import { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white/90 dark:bg-gray-950/90 backdrop-blur-sm border border-slate-300 dark:border-gray-700 rounded-lg p-3 text-sm shadow-xl">
      <p className="text-slate-500 dark:text-gray-400 mb-1">
        {new Date(label).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
      </p>
      {d.price != null && <p className="text-indigo-600 dark:text-indigo-300 font-semibold">Price: ${d.price.toFixed(2)}</p>}
      {d.prediction != null && <p className="text-emerald-600 dark:text-emerald-400 font-semibold">Predicted: ${d.prediction.toFixed(2)}</p>}
      {d.sma_20 != null && <p className="text-amber-500 text-xs">SMA 20: ${d.sma_20.toFixed(2)}</p>}
    </div>
  );
};

const StockChart = ({ prices, prediction, showSMA = false, height = 400 }) => {
  const chartData = useMemo(() => {
    const data = (prices || []).slice(0, 90).reverse().map((p) => ({
      date: new Date(p.date),
      price: p.close,
      sma_20: showSMA ? p.sma_20 : undefined,
    }));

    if (prediction && data.length > 0) {
      const lastDate = data[data.length - 1].date;
      const nextDay = new Date(lastDate);
      nextDay.setDate(lastDate.getDate() + 1);
      return [...data, { date: nextDay, prediction: prediction }];
    }
    return data;
  }, [prices, prediction, showSMA]);

  if (!chartData.length) return <div className="flex items-center justify-center h-64 text-slate-500">No chart data</div>;

  return (
    <div className="bg-white dark:bg-gray-950/50 border border-slate-200 dark:border-gray-800 rounded-xl p-6" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
          <defs>
            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#818CF8" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#818CF8" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorPrediction" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#34D399" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#34D399" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(128,128,128,0.1)" />
          <XAxis
            dataKey="date"
            stroke="#64748B"
            fontSize={12}
            tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          />
          <YAxis
            stroke="#64748B"
            fontSize={12}
            domain={['dataMin - (dataMax-dataMin)*0.1', 'dataMax + (dataMax-dataMin)*0.1']}
            tickFormatter={(v) => `$${v.toFixed(0)}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area type="monotone" dataKey="price" stroke="#818CF8" fill="url(#colorPrice)" strokeWidth={2} />
          {prediction && (
            <Area type="monotone" dataKey="prediction" stroke="#34D399" strokeDasharray="5 5" fill="url(#colorPrediction)" />
          )}
          {showSMA && (
            <Area type="monotone" dataKey="sma_20" stroke="#F59E0B" fill="none" strokeWidth={1.5} strokeDasharray="3 3" />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default StockChart;
