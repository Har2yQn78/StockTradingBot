import Link from 'next/link';
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

const StockAnalysis = () => {
  const [ticker, setTicker] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [forecastData, setForecastData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingHistorical, setLoadingHistorical] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [forecasting, setForecasting] = useState(false);

  const syncStockData = async () => {
    if (!ticker) return;

    setSyncing(true);
    setError('');

    try {
      const syncRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/market/sync/${ticker}/?force=true`
      );

      if (!syncRes.ok) {
        const errorMessage = await syncRes.text();
        throw new Error(`Sync Error ${syncRes.status}: ${errorMessage}`);
      }

      const syncData = await syncRes.json();

      // Automatically fetch data after successful sync
      await fetchStockData();
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  };

  const fetchStockData = async () => {
    if (!ticker) return;

    setLoading(true);
    setLoadingHistorical(true);
    setError('');

    try {
      // Fetch analysis data
      const analysisRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/market/analyze/${ticker}/`
      );
      if (!analysisRes.ok) {
        const errorMessage = await analysisRes.text();
        throw new Error(`Error ${analysisRes.status}: ${errorMessage}`);
      }
      const analysisData = await analysisRes.json();

      // Fetch historical data
      const historicalRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/market/historical/${ticker}/`
      );
      if (!historicalRes.ok) {
        const errorMessage = await historicalRes.text();
        throw new Error(`Error ${historicalRes.status}: ${errorMessage}`);
      }
      const historicalDataRaw = await historicalRes.json();

      const formattedHistoricalData = historicalDataRaw.map((item) => ({
        ...item,
        date: new Date(item.time).toLocaleDateString(),
      }));

      setAnalysis(analysisData);
      setHistoricalData(formattedHistoricalData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setLoadingHistorical(false);
    }
  };

  const fetchForecastData = async () => {
    if (!ticker) return;

    setForecasting(true);
    setError('');

    try {
      const forecastRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/market/forecast/${ticker}/`
      );

      if (!forecastRes.ok) {
        const errorMessage = await forecastRes.text();
        throw new Error(`Forecast Error ${forecastRes.status}: ${errorMessage}`);
      }

      const forecastData = await forecastRes.json();
      setForecastData(forecastData);
    } catch (err) {
      setError(err.message);
    } finally {
      setForecasting(false);
    }
  };

  // Reset states when ticker changes
  useEffect(() => {
    setAnalysis(null);
    setHistoricalData([]);
    setForecastData(null);
    setError('');
  }, [ticker]);

  // Helper function to render analysis data in a table
  const renderAnalysisTable = (analysis) => {
    return (
      <table className="min-w-full bg-white border rounded-lg overflow-hidden">
        <thead>
          <tr className="bg-gray-100">
            <th className="px-4 py-2 text-left">Metric</th>
            <th className="px-4 py-2 text-left">Value</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(analysis).map(([key, value]) => (
            <React.Fragment key={key}>
              {typeof value === 'object' && !Array.isArray(value) ? (
                // Render nested object (e.g., MACD, BOLLINGER)
                Object.entries(value).map(([subKey, subValue]) => (
                  <tr key={subKey} className="border-t">
                    <td className="px-4 py-2 text-gray-600">
                      {key.replace(/_/g, ' ').toUpperCase()} - {subKey.replace(/_/g, ' ').toUpperCase()}
                    </td>
                    <td className="px-4 py-2">
                      {typeof subValue === 'number' ? subValue.toFixed(2) : subValue.toString()}
                    </td>
                  </tr>
                ))
              ) : (
                // Render top-level properties (e.g., SCORE, TICKER)
                <tr key={key} className="border-t">
                  <td className="px-4 py-2 text-gray-600">
                    {key.replace(/_/g, ' ').toUpperCase()}
                  </td>
                  <td className="px-4 py-2">
                    {typeof value === 'number' ? value.toFixed(2) : value.toString()}
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    );
  };

  // Combine historical and forecast data for the chart
  const combinedChartData = [
    ...historicalData,
    ...(forecastData?.forecast_data?.map(item => ({
      date: item.date,
      adjusted_price: item.adjusted_price, // Only adjusted_price is used in the chart
    })) || [])
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col space-y-4">
        <Link href="/" className="text-blue-500 hover:text-blue-600">
          ← Back to Home
        </Link>

        <div className="flex gap-4 items-center">
          <input
            type="text"
            placeholder="Enter stock ticker (e.g., AAPL)"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={syncStockData}
            disabled={syncing || !ticker}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-400"
          >
            {syncing ? 'Syncing...' : 'Sync Data'}
          </button>
          <button
            onClick={fetchStockData}
            disabled={loading || !ticker}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400"
          >
            {loading ? 'Loading...' : 'Analyze Stock'}
          </button>
          <button
            onClick={fetchForecastData}
            disabled={forecasting || !ticker || historicalData.length === 0}
            className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:bg-gray-400"
          >
            {forecasting ? 'Forecasting...' : 'Forecast Stock'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {loadingHistorical && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg">
          Loading historical data for {ticker}...
        </div>
      )}

      {analysis && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold mb-4">Stock Analysis - {ticker}</h2>
          {renderAnalysisTable(analysis)}
        </div>
      )}

      {(historicalData.length > 0 || forecastData) && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold mb-4">
            Stock Price History and Forecast - {ticker}
          </h2>
          <div className="w-full h-[70vh]"> {/* Use viewport height for responsiveness */}
            <LineChart
                width={window.innerWidth * 0.9}
                height={window.innerHeight * 0.7}
                data={combinedChartData}
                margin={{top: 20, right: 30, left: 20, bottom: 20}}
            >
              <CartesianGrid strokeDasharray="3 3"/>
              <XAxis dataKey="date"/>
              <YAxis/>
              <Tooltip/>
              <Legend/>
              <Line
                  type="monotone"
                  dataKey="close_price"
                  stroke="#8884d8"
                  name="Historical Price"
                  strokeWidth={2}
              />
              <Line
                  type="monotone"
                  dataKey="volume_weighted_average"
                  stroke="#82ca9d"
                  name="VWAP"
              />
              {forecastData && (
                  <Line
                      type="monotone"
                      dataKey="adjusted_price"
                      stroke="#ff0000"
                      name="Adjusted Price"
                      strokeDasharray="3 3"
                      strokeWidth={2}
                  />
              )}
            </LineChart>
          </div>

          {forecastData && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <h3 className="text-lg font-semibold mb-2">Forecast Data</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full bg-white">
                    <thead>
                    <tr>
                      <th className="px-4 py-2 border">Date</th>
                      <th className="px-4 py-2 border">Predicted Price</th>
                      <th className="px-4 py-2 border">Adjusted Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecastData.forecast_data.map((item, index) => (
                      <tr key={index}>
                        <td className="px-4 py-2 border">{item.date}</td>
                        <td className="px-4 py-2 border">${item.predicted_price.toFixed(2)}</td>
                        <td className="px-4 py-2 border">${item.adjusted_price.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {forecastData && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">Forecast Metrics</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-3 bg-white rounded-lg shadow">
                  <div className="text-gray-600">Mean Absolute Error</div>
                  <div className="text-xl font-semibold">
                    ${forecastData.metrics.mean_absolute_error.toFixed(2)}
                  </div>
                </div>
                <div className="p-3 bg-white rounded-lg shadow">
                  <div className="text-gray-600">Forecast Start</div>
                  <div className="text-xl font-semibold">
                    {forecastData.metrics.forecast_start_date}
                  </div>
                </div>
                <div className="p-3 bg-white rounded-lg shadow">
                  <div className="text-gray-600">Forecast End</div>
                  <div className="text-xl font-semibold">
                    {forecastData.metrics.forecast_end_date}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default StockAnalysis;