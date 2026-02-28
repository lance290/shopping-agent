import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import ListPage from './page';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useParams: vi.fn(() => ({ id: '5' })),
}));

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) =>
    React.createElement('a', { href }, children),
}));

const mockRow = {
  id: 5,
  title: 'Nike Running Shoes',
  status: 'open',
  budget_max: 200,
  currency: 'USD',
};

describe('ListPage — Share with Family', () => {
  let clipboardWriteText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    clipboardWriteText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: clipboardWriteText },
      writable: true,
      configurable: true,
    });

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRow),
    }) as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the list page with row data', async () => {
    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByText('Nike Running Shoes')).toBeInTheDocument();
    });

    expect(screen.getByTestId('share-with-family-btn')).toBeInTheDocument();
  });

  it('copies the current URL to clipboard when Share with Family is clicked — never calls navigator.share', async () => {
    // Ensure navigator.share is NOT present (or if present, should never be called)
    const mockNavigatorShare = vi.fn();
    Object.defineProperty(navigator, 'share', {
      value: mockNavigatorShare,
      writable: true,
      configurable: true,
    });

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('share-with-family-btn')).toBeInTheDocument();
    });

    const btn = screen.getByTestId('share-with-family-btn');
    fireEvent.click(btn);

    await waitFor(() => {
      expect(clipboardWriteText).toHaveBeenCalledOnce();
    });

    // navigator.share must never be called (AbortError: Share canceled would be unhandled)
    expect(mockNavigatorShare).not.toHaveBeenCalled();
  });

  it('shows "Copied!" feedback after clicking Share with Family', async () => {
    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('share-with-family-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('share-with-family-btn'));

    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });
  });

  it('shows an error state when the list is not found', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Not found' }),
    }) as unknown as typeof fetch;

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByText('List Not Found')).toBeInTheDocument();
    });
  });

  it('fetches the row using the correct API path', async () => {
    render(<ListPage />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/rows?id=5');
    });
  });
});
