import Header from '@/components/Header';
import Footer from '@/components/Footer';
import BarcodeGenerator from '@/components/BarcodeGenerator';

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen bg-white dark:bg-gray-950">
      <Header />
      <main className="flex-1 flex flex-col items-center py-12 sm:py-20">
        {/* Hero */}
        <div className="text-center mb-12 px-4">
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white mb-4 tracking-tight">
            Transform Barcodes into{' '}
            <span className="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              Art
            </span>
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 max-w-xl mx-auto">
            Generate beautiful, artistic barcodes as SVG. Choose from multiple styles,
            customize colors, and download in seconds. Free forever.
          </p>
        </div>

        {/* Tool */}
        <BarcodeGenerator />

        {/* Features */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl mx-auto mt-16 px-4">
          {[
            { icon: '🎨', title: '4 Artistic Styles', desc: 'Classic, rounded, dots, and diamond patterns' },
            { icon: '⬇️', title: 'SVG & PNG Export', desc: 'Download in high-quality vector or raster format' },
            { icon: '🔒', title: '100% Client-Side', desc: 'Your data never leaves your browser' },
          ].map((f) => (
            <div key={f.title} className="text-center p-6 rounded-2xl bg-gray-50 dark:bg-gray-900 border border-gray-100 dark:border-gray-800">
              <span className="text-3xl mb-3 block">{f.icon}</span>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">{f.title}</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
}
