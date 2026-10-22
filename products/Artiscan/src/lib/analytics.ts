import posthog from 'posthog-js';

let initialized = false;

export function initAnalytics() {
  if (typeof window !== 'undefined' && !initialized) {
    const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (key) {
      posthog.init(key, {
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com',
        capture_pageview: true,
        capture_pageleave: true,
        autocapture: true,
      });
      initialized = true;
    }
  }
}

export function trackEvent(name: string, properties?: Record<string, any>) {
  if (initialized) {
    posthog.capture(name, {
      ...properties,
      timestamp: new Date().toISOString(),
    });
  }
}

export function identifyUser(userId: string, traits?: Record<string, any>) {
  if (initialized) {
    posthog.identify(userId, traits);
  }
}
