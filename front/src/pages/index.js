import Link from 'next/link';
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 p-4">
      <div className="container mx-auto flex flex-col items-center justify-center gap-8">
        <h1 className="text-center text-4xl font-extrabold tracking-tight text-slate-50 sm:text-5xl">
          Stock Trading Analysis
        </h1>
        <Link href="/stocks">
          <Button
            variant="secondary"
            size="lg"
            className="text-lg px-8 py-6"
          >
            Go to Stock Analysis
          </Button>
        </Link>
      </div>
    </div>
  );
}