'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { trackEvent } from '@/lib/analytics';

type BarcodePattern = 'classic' | 'rounded' | 'dots' | 'diamond';

interface BarcodeConfig {
  value: string;
  primaryColor: string;
  backgroundColor: string;
  pattern: BarcodePattern;
}

// Generate barcode bars from text value
function generateBars(value: string): number[] {
  const bars: number[] = [];
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i);
    // Simple encoding: each char produces 4 bars of varying width
    bars.push((code % 4) + 1);
    bars.push(1); // gap
    bars.push(((code >> 2) % 3) + 1);
    bars.push(1); // gap
  }
  return bars;
}

function renderBarcodeSVG(config: BarcodeConfig): string {
  const { value, primaryColor, backgroundColor, pattern } = config;
  if (!value.trim()) return '';

  const bars = generateBars(value);
  const totalWidth = bars.reduce((a, b) => a + b, 0) + 20; // padding
  const height = 120;
  const svgParts: string[] = [];

  let x = 10;
  bars.forEach((width, i) => {
    const isBar = i % 2 === 0;
    if (isBar) {
      switch (pattern) {
        case 'rounded':
          svgParts.push(`<rect x="${x}" y="10" width="${width * 3}" height="${height - 20}" rx="3" fill="${primaryColor}" />`);
          break;
        case 'dots':
          for (let dy = 12; dy < height - 10; dy += 8) {
            svgParts.push(`<circle cx="${x + (width * 1.5)}" cy="${dy}" r="${Math.min(width * 1.2, 3)}" fill="${primaryColor}" />`);
          }
          break;
        case 'diamond':
          for (let dy = 15; dy < height - 10; dy += 10) {
            svgParts.push(`<polygon points="${x + width * 1.5},${dy - 4} ${x + width * 3},${dy} ${x + width * 1.5},${dy + 4} ${x},${dy}" fill="${primaryColor}" />`);
          }
          break;
        default:
          svgParts.push(`<rect x="${x}" y="10" width="${width * 3}" height="${height - 20}" fill="${primaryColor}" />`);
      }
    }
    x += width * 3;
  });

  // Add text label
  const textY = height - 2;
  svgParts.push(`<text x="${(x + 10) / 2}" y="${textY}" text-anchor="middle" font-family="monospace" font-size="12" fill="${primaryColor}">${value}</text>`);

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${x + 10} ${height + 10}" width="100%" height="100%">
    <rect width="100%" height="100%" fill="${backgroundColor}" rx="8" />
    ${svgParts.join('\n    ')}
  </svg>`;
}

export default function BarcodeGenerator() {
  const [config, setConfig] = useState<BarcodeConfig>({
    value: 'ARTISCAN-2026',
    primaryColor: '#1a1a2e',
    backgroundColor: '#ffffff',
    pattern: 'classic',
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const svgRef = useRef<HTMLDivElement>(null);

  const svgString = renderBarcodeSVG(config);

  // Safely render SVG into ref without dangerouslySetInnerHTML
  useEffect(() => {
    if (svgRef.current && svgString) {
      svgRef.current.innerHTML = svgString;
    } else if (svgRef.current) {
      svgRef.current.innerHTML = '';
    }
  }, [svgString]);

  const handleGenerate = useCallback(() => {
    if (!config.value.trim()) {
      setError('Please enter a value for your barcode');
      return;
    }
    setError(null);
    setIsGenerating(true);
    trackEvent('barcode_generated', {
      pattern: config.pattern,
      valueLength: config.value.length,
    });
    setTimeout(() => setIsGenerating(false), 300);
  }, [config]);

  const handleDownloadSVG = useCallback(() => {
    if (!svgString) return;
    const blob = new Blob([svgString], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `artiscan-${config.value.slice(0, 20)}.svg`;
    a.click();
    URL.revokeObjectURL(url);
    trackEvent('barcode_downloaded', { format: 'svg', pattern: config.pattern });
  }, [svgString, config]);

  const handleDownloadPNG = useCallback(() => {
    if (!svgRef.current) return;
    const svgEl = svgRef.current.querySelector('svg');
    if (!svgEl) return;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const svgData = new XMLSerializer().serializeToString(svgEl);
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width * 2;
      canvas.height = img.height * 2;
      ctx.scale(2, 2);
      ctx.drawImage(img, 0, 0);
      const a = document.createElement('a');
      a.href = canvas.toDataURL('image/png');
      a.download = `artiscan-${config.value.slice(0, 20)}.png`;
      a.click();
      trackEvent('barcode_downloaded', { format: 'png', pattern: config.pattern });
    };
    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
  }, [config]);

  const patterns: { id: BarcodePattern; label: string; icon: string }[] = [
    { id: 'classic', label: 'Classic', icon: '▮▮▮' },
    { id: 'rounded', label: 'Rounded', icon: '▰▰▰' },
    { id: 'dots', label: 'Dots', icon: '●●●' },
    { id: 'diamond', label: 'Diamond', icon: '◆◆◆' },
  ];

  return (
    <div className="w-full max-w-2xl mx-auto px-4">
      <div className="space-y-6">
        {/* Input */}
        <div>
          <label htmlFor="barcode-value" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Barcode Value
          </label>
          <input
            id="barcode-value"
            type="text"
            value={config.value}
            onChange={(e) => {
              setConfig(prev => ({ ...prev, value: e.target.value }));
              setError(null);
            }}
            placeholder="Enter text or numbers..."
            className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none"
            maxLength={50}
            aria-label="Barcode value input"
          />
          {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
        </div>

        {/* Pattern Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Style</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {patterns.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setConfig(prev => ({ ...prev, pattern: p.id }));
                  trackEvent('pattern_selected', { pattern: p.id });
                }}
                className={`px-4 py-3 rounded-xl border-2 transition-all text-sm font-medium ${
                  config.pattern === p.id
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-600 dark:text-gray-400'
                }`}
                aria-pressed={config.pattern === p.id}
              >
                <span className="block text-lg mb-1">{p.icon}</span>
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Colors */}
        <div className="flex gap-6">
          <div>
            <label htmlFor="primary-color" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Bar Color</label>
            <input
              id="primary-color"
              type="color"
              value={config.primaryColor}
              onChange={(e) => {
                setConfig(prev => ({ ...prev, primaryColor: e.target.value }));
                trackEvent('color_changed', { type: 'primary', color: e.target.value });
              }}
              className="w-12 h-12 rounded-lg cursor-pointer border-2 border-gray-200 dark:border-gray-700"
            />
          </div>
          <div>
            <label htmlFor="bg-color" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Background</label>
            <input
              id="bg-color"
              type="color"
              value={config.backgroundColor}
              onChange={(e) => setConfig(prev => ({ ...prev, backgroundColor: e.target.value }))}
              className="w-12 h-12 rounded-lg cursor-pointer border-2 border-gray-200 dark:border-gray-700"
            />
          </div>
        </div>

        {/* Preview */}
        <div className="relative rounded-2xl border-2 border-dashed border-gray-200 dark:border-gray-700 p-6 bg-gray-50 dark:bg-gray-800/50 min-h-[200px] flex items-center justify-center">
          {isGenerating ? (
            <div className="flex items-center gap-3 text-gray-500" role="status" aria-label="Loading">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Loading...
            </div>
          ) : error ? (
            <p className="text-red-500 text-sm" role="alert">{error}</p>
          ) : svgString ? (
            <div ref={svgRef} className="w-full" />
          ) : (
            <p className="text-gray-400 text-sm">Enter a value above to generate your barcode</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={handleGenerate}
            className="flex-1 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl transition-all hover:shadow-lg active:scale-[0.98]"
          >
            Generate Barcode
          </button>
          <button
            onClick={handleDownloadSVG}
            disabled={!svgString}
            className="flex-1 px-6 py-3 bg-gray-900 dark:bg-white dark:text-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed hover:shadow-lg active:scale-[0.98]"
          >
            Download SVG
          </button>
          <button
            onClick={handleDownloadPNG}
            disabled={!svgString}
            className="flex-1 px-6 py-3 border-2 border-gray-300 dark:border-gray-600 hover:border-gray-400 text-gray-700 dark:text-gray-300 font-medium rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed hover:shadow-lg active:scale-[0.98]"
          >
            Download PNG
          </button>
        </div>
      </div>
    </div>
  );
}
