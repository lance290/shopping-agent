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
  logout: vi.fn(),
}));

const mockRow = {
  id: 5,
  title: 'Nike Running Shoes',
  status: 'open',
  budget_max: 200,
  currency: 'USD',
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
    expect(screen.queryByTestId('account-section')).not.toBeInTheDocument();
  });

  it('shows account section with Open My Board and Sign Out when user is authenticated', async () => {
    vi.mocked(authUtils.getMe).mockResolvedValue({ authenticated: true, user_id: 1, phone_number: '+15551234567' });

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('account-section')).toBeInTheDocument();
    });

    expect(screen.getByText('Open My Board')).toBeInTheDocument();
    expect(screen.getByTestId('sign-out-btn')).toBeInTheDocument();
    expect(screen.queryByTestId('login-btn')).not.toBeInTheDocument();
  });

  it('displays the user phone or email in the account section', async () => {
    vi.mocked(authUtils.getMe).mockResolvedValue({ authenticated: true, user_id: 1, phone_number: '+15559876543' });

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('account-identifier')).toHaveTextContent('+15559876543');
    });
  });

  it('does not show Sign In button while loading (prevents race condition)', async () => {
    // Simulate slow auth check
    let resolveMe!: (v: authUtils.AuthMeResponse) => void;
    const mePromise = new Promise<authUtils.AuthMeResponse>((res) => { resolveMe = res; });
    vi.mocked(authUtils.getMe).mockReturnValue(mePromise);

    render(<ListPage />);

    // While loading, neither Sign In nor account section should appear
    expect(screen.queryByTestId('login-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('account-section')).not.toBeInTheDocument();

    // Resolve auth — now the account section should appear
    resolveMe({ authenticated: true, user_id: 1 });

    await waitFor(() => {
      expect(screen.getByTestId('account-section')).toBeInTheDocument();
    });
  });

  it('calls logout and redirects to /login when Sign Out is clicked', async () => {
    vi.mocked(authUtils.getMe).mockResolvedValue({ authenticated: true, user_id: 1 });
    vi.mocked(authUtils.logout).mockResolvedValue(undefined);

    // Mock window.location
    const originalLocation = window.location;
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
      configurable: true,
    });

    render(<ListPage />);

    await waitFor(() => {
      expect(screen.getByTestId('sign-out-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('sign-out-btn'));

    await waitFor(() => {
      expect(authUtils.logout).toHaveBeenCalled();
      expect(window.location.href).toBe('/login');
    });

    Object.defineProperty(window, 'location', { value: originalLocation, configurable: true });
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
