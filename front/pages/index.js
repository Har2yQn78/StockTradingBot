import { useState } from 'react';
import { useRouter } from 'next/router';

export default function Home() {
    const [ticker, setTicker] = useState('');
    const router = useRouter();

    const handleSubmit = (e) => {
        e.preventDefault();
        const upperTicker = ticker.toUpperCase(); // Convert to uppercase
        router.push(`/stock/${upperTicker}`);
    };

    return (
        <div className="p-4">
            <h1 className="text-2xl font-bold mb-4">Stock Analysis Tool</h1>
            <form onSubmit={handleSubmit} className="flex gap-2">
                <input
                    type="text"
                    placeholder="Enter stock ticker (e.g., AAPL)"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())} // Convert to uppercase on input
                    className="p-2 border rounded"
                />
                <button type="submit" className="p-2 bg-blue-500 text-white rounded">
                    Analyze
                </button>
            </form>
        </div>
    );
}