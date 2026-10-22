import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="w-full border-t border-gray-100 dark:border-gray-800 py-8 mt-auto">
      <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-500 dark:text-gray-400">
        <p>&copy; {new Date().getFullYear()} Artiscan. Free &amp; open.</p>
        <div className="flex gap-4">
          <Link href="/privacy" className="hover:text-gray-900 dark:hover:text-white transition-colors">
            Privacy
          </Link>
          <span className="text-gray-300 dark:text-gray-700">·</span>
          <span>Built with Next.js</span>
        </div>
      </div>
    </footer>
  );
}
