'use client';
import Link from 'next/link';
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

const StockAnalysis = () => {
  const [ticker, setTicker] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchStockData = async () => {
  if (!ticker) return;

  setLoading(true);
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

    // Process historical data to format dates
    const formattedHistoricalData = historicalDataRaw.map((item) => ({
      ...item,
      date: new Date(item.time).toLocaleDateString(), // Convert time to readable date
    }));

    setAnalysis(analysisData);
    setHistoricalData(formattedHistoricalData);
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
};




  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col space-y-4">
        <Link
          href="/"
          className="text-blue-500 hover:text-blue-600"
        >
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
            onClick={fetchStockData}
            disabled={loading || !ticker}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400"
          >
            {loading ? 'Loading...' : 'Analyze Stock'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {analysis && (
  <div className="bg-white rounded-lg shadow-lg p-6">
    <h2 className="text-xl font-bold mb-4">Stock Analysis - {ticker}</h2>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {Object.entries(analysis).map(([key, value]) => (
        <div key={key} className="p-4 border rounded-lg">
          <div className="font-medium text-gray-600">{key.replace(/_/g, ' ').toUpperCase()}</div>
          <div className="text-2xl">
            {typeof value === 'number' ? value.toFixed(2) : value.toString()}
          </div>
        </div>
      ))}
    </div>
  </div>
)}


      {historicalData.length > 0 && (
  <div className="bg-white rounded-lg shadow-lg p-6">
    <h2 className="text-xl font-bold mb-4">Historical Price Data - {ticker}</h2>
    <div className="w-full h-[400px]">
      <LineChart
        width={800}
        height={400}
        data={historicalData}
        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="close_price" stroke="#8884d8" name="Close Price" />
        <Line
          type="monotone"
          dataKey="volume_weighted_average"
          stroke="#82ca9d"
          name="VWAP"
        />
      </LineChart>
    </div>
  </div>
)}

    </div>
  );
};

export default StockAnalysis;