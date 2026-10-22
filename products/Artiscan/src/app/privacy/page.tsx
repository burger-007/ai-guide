export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">Privacy Policy</h1>
        <div className="prose dark:prose-invert max-w-none space-y-6">
          <p className="text-gray-600 dark:text-gray-300">
            Last updated: April 13, 2026
          </p>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            1. Information We Collect
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            Artiscan collects anonymous usage data to improve the service.
            We do NOT collect personal information such as names, emails, or addresses
            unless you explicitly provide them.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            2. Usage Analytics
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            We use PostHog (posthog.com) for anonymous product analytics.
            This helps us understand how the tool is used and how to improve it.
            Data collected includes: page views, feature usage patterns, and
            general interaction metrics. No personally identifiable information (PII)
            is collected through analytics.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            3. Data Processing
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            All tool processing happens in your browser (client-side).
            Your input data is not sent to or stored on our servers unless
            specifically required for the tool&apos;s functionality.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            4. Third-Party Services
          </h2>
          <ul className="list-disc pl-6 text-gray-600 dark:text-gray-300">
            <li>PostHog — Anonymous analytics</li>
            <li>Vercel — Hosting</li>
          </ul>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            5. Your Rights
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            You can opt out of analytics tracking by using a browser ad blocker
            or Do Not Track setting. You may request deletion of any data
            associated with your usage.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            6. Contact
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            For privacy-related questions, please open an issue on our GitHub repository.
          </p>
        </div>
        <div className="mt-8">
          <a href="/" className="text-blue-600 dark:text-blue-400 hover:underline">
            &larr; Back to Artiscan
          </a>
        </div>
      </div>
    </div>
  );
}
