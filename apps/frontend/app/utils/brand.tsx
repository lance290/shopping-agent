'use client';

import { createContext, useContext, ReactNode } from 'react';

export type BrandId = 'buyanything' | 'pop';

export interface BrandConfig {
  id: BrandId;
  name: string;
  tagline: string;
  domain: string;
  agentName: string;
  agentEmail: string;
  colors: {
    primary: string;
    primaryHover: string;
    accent: string;
    bg: string;
    bgAlt: string;
    text: string;
    textMuted: string;
  };
  chatPlaceholder: string;
  logo: string;
}

export const BRANDS: Record<BrandId, BrandConfig> = {
  buyanything: {
    id: 'buyanything',
    name: 'BuyAnything',
    tagline: 'AI-powered procurement assistant',
    domain: 'buy-anything.com',
    agentName: 'BuyAnything',
    agentEmail: 'noreply@buy-anything.com',
    colors: {
      primary: '#2563eb',
      primaryHover: '#1d4ed8',
      accent: '#3b82f6',
      bg: '#ffffff',
      bgAlt: '#f8fafc',
      text: '#0f172a',
      textMuted: '#64748b',
    },
    chatPlaceholder: 'What are you looking for?',
    logo: '/logo.svg',
  },
  pop: {
    id: 'pop',
    name: 'Pop',
    tagline: 'Save money on groceries with AI',
    domain: 'popsavings.com',
    agentName: 'Pop',
    agentEmail: 'pop@popsavings.com',
    colors: {
      primary: '#16a34a',
      primaryHover: '#15803d',
      accent: '#22c55e',
      bg: '#ffffff',
      bgAlt: '#f0fdf4',
      text: '#052e16',
      textMuted: '#4b5563',
    },
    chatPlaceholder: 'What do you need from the store?',
    logo: '/pop-logo.svg',
  },
};

const BrandContext = createContext<BrandConfig>(BRANDS.buyanything);

export function BrandProvider({
  brand,
  children,
}: {
  brand: BrandId;
  children: ReactNode;
}) {
  return (
    <BrandContext.Provider value={BRANDS[brand]}>
      {children}
    </BrandContext.Provider>
  );
}

export function useBrand(): BrandConfig {
  return useContext(BrandContext);
}

export function detectBrand(): BrandId {
  if (typeof window === 'undefined') return 'buyanything';
  const hostname = window.location.hostname;
  if (hostname.includes('popsavings.com')) return 'pop';
  const params = new URLSearchParams(window.location.search);
  if (params.get('brand') === 'pop') return 'pop';
  return 'buyanything';
}
