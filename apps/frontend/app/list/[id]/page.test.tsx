import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import ListPage from './page';
import * as authUtils from '../../utils/auth';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useParams: vi.fn(() => ({ id: '5' })),
}));

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) =>
    React.createElement('a', { href, ...props }, children),
}));

// Mock auth utils
vi.mock('../../utils/auth', () => ({
  getMe: vi.fn(),
}));

const mockRow = {
  id: 5,
  title: 'Nike Running Shoes',
  status: 'open',
  budget_max: 200,
  currency: 'USD',
};

const mockRowWithBids = {
  ...mockRow,
  bids: [
    { id: 1, item_title: 'Nike Air Max', price: 129.99, currency: 'USD', image_url: null, item_url: 'http://example.com/1' },
    { id: 2, item_title: 'Nike React Infinity', price: 159.99, currency: 'USD', image_url: null, item_url: 'http://example.com/2' },
  ],
};

describe('ListPage — Login button', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRow),
    }) as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows Sign In button linking to /login when user is not authenticated', async () => {
    vi.mocked(authUtils.getMe).mockResolvedValue({ authenticated: false });

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('login-btn')).toBeInTheDocument();
    });

    expect(screen.getByTestId('login-btn')).toHaveAttribute('href', '/login');
    expect(screen.queryByText('Open My Board')).not.toBeInTheDocument();
  });

  it('shows Open My Board button when user is authenticated', async () => {
    vi.mocked(authUtils.getMe).mockResolvedValue({ authenticated: true, user_id: 1 });

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByText('Open My Board')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('login-btn')).not.toBeInTheDocument();
  });
});

describe('ListPage — Share with Family', () => {
  let clipboardWriteText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    clipboardWriteText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: clipboardWriteText },
      writable: true,
      configurable: true,
    });

    vi.mocked(authUtils.getMe).mockResolvedValue({ authenticated: true, user_id: 1 });

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

  it('shows "Copy failed" feedback when clipboard write fails with a non-AbortError and execCommand also fails', async () => {
    clipboardWriteText.mockRejectedValue(new DOMException('Permission denied', 'NotAllowedError'));
    // execCommand is absent in jsdom — success stays false → "Copy failed" is shown
    Object.defineProperty(document, 'execCommand', {
      value: vi.fn().mockReturnValue(false),
      writable: true,
      configurable: true,
    });

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('share-with-family-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('share-with-family-btn'));

    await waitFor(() => {
      expect(screen.getByText('Copy failed')).toBeInTheDocument();
    });

    expect(screen.queryByText('Copied!')).not.toBeInTheDocument();
  });

  it('shows "Copied!" when clipboard fails but execCommand succeeds', async () => {
    clipboardWriteText.mockRejectedValue(new DOMException('Permission denied', 'NotAllowedError'));
    Object.defineProperty(document, 'execCommand', {
      value: vi.fn().mockReturnValue(true),
      writable: true,
      configurable: true,
    });

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('share-with-family-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('share-with-family-btn'));

    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });
  });

  it('does nothing (no Copied!, no Copy failed) when clipboard throws AbortError', async () => {
    clipboardWriteText.mockRejectedValue(new DOMException('Share canceled', 'AbortError'));

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('share-with-family-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('share-with-family-btn'));

    // Neither success nor failure feedback should appear — AbortError is silenced
    await new Promise((r) => setTimeout(r, 100));
    expect(screen.queryByText('Copied!')).not.toBeInTheDocument();
    expect(screen.queryByText('Copy failed')).not.toBeInTheDocument();
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

describe('ListPage — Inline title editing', () => {
  beforeEach(() => {
    vi.mocked(authUtils.getMe).mockResolvedValue({ authenticated: true, user_id: 1 });

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRow),
    }) as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the title as a clickable button', async () => {
    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('title-edit-btn')).toBeInTheDocument();
    });

    expect(screen.getByText('Nike Running Shoes')).toBeInTheDocument();
  });

  it('switches to an input when the title is clicked', async () => {
    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('title-edit-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('title-edit-btn'));

    expect(screen.getByTestId('title-edit-input')).toBeInTheDocument();
    expect((screen.getByTestId('title-edit-input') as HTMLInputElement).value).toBe('Nike Running Shoes');
  });

  it('saves updated title on Enter key and calls PATCH', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockRow) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ ...mockRow, title: 'Updated Title' }) }) as unknown as typeof fetch;

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('title-edit-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('title-edit-btn'));
    const input = screen.getByTestId('title-edit-input') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Updated Title' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/rows?id=5',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ title: 'Updated Title' }),
        }),
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Updated Title')).toBeInTheDocument();
    });
  });

  it('cancels edit on Escape key without saving', async () => {
    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('title-edit-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('title-edit-btn'));
    const input = screen.getByTestId('title-edit-input');
    fireEvent.change(input, { target: { value: 'Changed Title' } });
    fireEvent.keyDown(input, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByTestId('title-edit-input')).not.toBeInTheDocument();
    });

    expect(screen.getByText('Nike Running Shoes')).toBeInTheDocument();
    // fetch should only have been called once (the initial load), not for PATCH
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it('does not call PATCH when title is unchanged', async () => {
    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('title-edit-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('title-edit-btn'));
    const input = screen.getByTestId('title-edit-input');
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(screen.queryByTestId('title-edit-input')).not.toBeInTheDocument();
    });

    // Only initial fetch, no PATCH
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });
});

describe('ListPage — Shopping items and Done Shopping (bug #131)', () => {
  beforeEach(() => {
    vi.mocked(authUtils.getMe).mockResolvedValue({ authenticated: true, user_id: 1 });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders items from the list when bids are present', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRowWithBids),
    }) as unknown as typeof fetch;

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('items-list')).toBeInTheDocument();
    });

    expect(screen.getByText('Nike Air Max')).toBeInTheDocument();
    expect(screen.getByText('Nike React Infinity')).toBeInTheDocument();
  });

  it('renders a Done Shopping button when items are present', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRowWithBids),
    }) as unknown as typeof fetch;

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('done-shopping-btn')).toBeInTheDocument();
    });
  });

  it('does not render Done Shopping button when there are no items', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRow),
    }) as unknown as typeof fetch;

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByText('Nike Running Shoes')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('done-shopping-btn')).not.toBeInTheDocument();
  });

  it('keeps items visible after clicking Done Shopping (bug #131)', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRowWithBids),
    }) as unknown as typeof fetch;

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('done-shopping-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('done-shopping-btn'));

    // Items must still be visible after clicking Done Shopping
    expect(screen.getByTestId('items-list')).toBeInTheDocument();
    expect(screen.getByText('Nike Air Max')).toBeInTheDocument();
    expect(screen.getByText('Nike React Infinity')).toBeInTheDocument();
  });

  it('shows a success banner after clicking Done Shopping', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRowWithBids),
    }) as unknown as typeof fetch;

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('done-shopping-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('done-shopping-btn'));

    expect(screen.getByTestId('done-shopping-banner')).toBeInTheDocument();
    // Done Shopping button should be hidden after click
    expect(screen.queryByTestId('done-shopping-btn')).not.toBeInTheDocument();
  });

  it('allows checking off individual items', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRowWithBids),
    }) as unknown as typeof fetch;

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('item-checkbox-1')).toBeInTheDocument();
    });

    const checkbox = screen.getByTestId('item-checkbox-1') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);

    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(true);

    // Unchecking should work too
    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(false);
  });

  it('does not make any API calls when Done Shopping is clicked', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRowWithBids),
    }) as unknown as typeof fetch;
    global.fetch = fetchMock;

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('done-shopping-btn')).toBeInTheDocument();
    });

    const callCountBeforeClick = (fetchMock as ReturnType<typeof vi.fn>).mock.calls.length;
    fireEvent.click(screen.getByTestId('done-shopping-btn'));

    // No additional fetch calls should have been made
    expect((fetchMock as ReturnType<typeof vi.fn>).mock.calls.length).toBe(callCountBeforeClick);
  });
});
