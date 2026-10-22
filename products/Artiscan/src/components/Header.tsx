import Link from 'next/link';

export default function Header() {
  return (
    <header className="w-full border-b border-gray-100 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <span className="text-2xl">◨</span>
          <span className="text-xl font-bold text-gray-900 dark:text-white group-hover:text-indigo-600 transition-colors">
            Artiscan
          </span>
        </Link>
        <nav className="flex items-center gap-6">
          <Link href="/" className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
            Generator
          </Link>
          <Link href="/privacy" className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
            Privacy
          </Link>
        </nav>
      </div>
    </header>
  );
}
