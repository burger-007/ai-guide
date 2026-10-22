export type BarcodePattern = 'classic' | 'rounded' | 'dots' | 'diamond';

export interface BarcodeConfig {
  value: string;
  primaryColor: string;
  backgroundColor: string;
  pattern: BarcodePattern;
}

export interface AnalyticsEvent {
  name: string;
  properties: Record<string, string | number | boolean>;
}
