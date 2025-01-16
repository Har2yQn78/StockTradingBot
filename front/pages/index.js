import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-6">Stock Trading Analysis</h1>
      <Link
        href="/stocks"
        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
      >
        Go to Stock Analysis
      </Link>
    </div>
  );
}