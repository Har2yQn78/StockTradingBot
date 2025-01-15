import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/router';
import axios from 'axios';
const HighchartsReact = dynamic(() => import('highcharts-react-official'), { ssr: false });
const Highcharts = dynamic(() => import('highcharts/highstock'), { ssr: false });

const StockAnalysis = () => {
    const router = useRouter();
    const { ticker } = router.query;
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [stockData, setStockData] = useState([]);

    useEffect(() => {
        if (ticker) {
            axios.get(`http://127.0.0.1:8000/api/market/analyze/${ticker}/`)
                .then(response => {
                    setAnalysis(response.data);
                    setLoading(false);
                })
                .catch(error => {
                    console.error("Analysis API Error:", error);
                    setError(error.response?.data?.error || "Failed to fetch analysis data.");
                    setLoading(false);
                });

            axios.get(`http://127.0.0.1:8000/api/market/historical/${ticker}/`)
                .then(response => {
                    setStockData(response.data.map(item => [
                        new Date(item.time).getTime(),  // x: timestamp
                        item.open_price,               // y: open
                        item.high_price,               // high
                        item.low_price,                // low
                        item.close_price               // close
                    ]));
                })
                .catch(error => {
                    console.error("Historical Data API Error:", error);
                });
        }
    }, [ticker]);

    if (loading) {
        return <div className="p-4">Loading...</div>;
    }

    if (error) {
        return <div className="p-4 text-red-500">Error: {error}</div>;
    }

    const chartOptions = {
        rangeSelector: {
            selected: 1,
        },
        title: {
            text: `Stock Price: ${ticker}`,
        },
        series: [
            {
                type: 'candlestick',
                name: 'Stock Price',
                data: stockData,
            },
        ],
    };

    return (
        <div className="p-4">
            <h1 className="text-2xl font-bold mb-4">Stock Analysis for {ticker}</h1>
            <div className="bg-white p-6 rounded-lg shadow-md">
                <h2 className="text-xl font-semibold mb-4">Recommendation</h2>
                <p className={`text-lg font-bold ${analysis.recommendation === 'BUY' ? 'text-green-600' : analysis.recommendation === 'SELL' ? 'text-red-600' : 'text-yellow-600'}`}>
                    {analysis.recommendation}
                </p>
                <p className="text-gray-600">Score: {analysis.score}</p>
            </div>

            {/* Candlestick Chart Section */}
            <div className="mt-6 bg-white p-6 rounded-lg shadow-md">
                <h2 className="text-xl font-semibold mb-4">Candlestick Chart</h2>
                <HighchartsReact highcharts={Highcharts} constructorType={'stockChart'} options={chartOptions} />
            </div>
        </div>
    );
};

export default StockAnalysis;
