/**
 * BulkParseModal component tests — PRD-04 (Bulk Actions).
 *
 * Covers:
 *   - Renders textarea and parse button
 *   - Parse button disabled when textarea is empty
 *   - Calls API on parse and invokes onParsed callback
 *   - Shows error when API returns no items
 *   - Shows error on API failure
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import BulkParseModal from '../pop-site/list/[id]/BulkParseModal';

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('BulkParseModal', () => {
  const defaultProps = {
    projectId: 1,
    onClose: vi.fn(),
    onParsed: vi.fn(),
  };

  test('renders heading and textarea', () => {
    render(<BulkParseModal {...defaultProps} />);
    expect(screen.getByText('Paste Recipe or List')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e.g. Need 2 lbs chicken/)).toBeInTheDocument();
  });

  test('parse button disabled when textarea is empty', () => {
    render(<BulkParseModal {...defaultProps} />);
    const button = screen.getByRole('button', { name: /Extract Items/i });
    expect(button).toBeDisabled();
  });

  test('parse button enabled when textarea has text', () => {
    render(<BulkParseModal {...defaultProps} />);
    const textarea = screen.getByPlaceholderText(/e.g. Need 2 lbs chicken/);
    fireEvent.change(textarea, { target: { value: 'Need milk and bread' } });
    const button = screen.getByRole('button', { name: /Extract Items/i });
    expect(button).not.toBeDisabled();
  });

  test('calls onParsed with rows on successful parse', async () => {
    const mockRows = [
      { id: 1, title: 'Milk', status: 'sourcing', deals: [], swaps: [], lowest_price: null, deal_count: 0 },
      { id: 2, title: 'Bread', status: 'sourcing', deals: [], swaps: [], lowest_price: null, deal_count: 0 },
    ];
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ parsed_items: 2, rows: mockRows }),
    });

    const onParsed = vi.fn();
    render(<BulkParseModal {...defaultProps} onParsed={onParsed} />);

    fireEvent.change(screen.getByPlaceholderText(/e.g. Need 2 lbs chicken/), {
      target: { value: 'Need milk and bread' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Extract Items/i }));

    await waitFor(() => {
      expect(onParsed).toHaveBeenCalledWith(mockRows);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/pop/projects/1/bulk_parse',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ text: 'Need milk and bread' }),
      }),
    );
  });

  test('shows error when API returns empty rows', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ parsed_items: 0, rows: [] }),
    });

    render(<BulkParseModal {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText(/e.g. Need 2 lbs chicken/), {
      target: { value: 'random text' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Extract Items/i }));

    await waitFor(() => {
      expect(screen.getByText(/Couldn't find any grocery items/)).toBeInTheDocument();
    });
    expect(defaultProps.onParsed).not.toHaveBeenCalled();
  });

  test('shows error on API failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    });

    render(<BulkParseModal {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText(/e.g. Need 2 lbs chicken/), {
      target: { value: 'some recipe' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Extract Items/i }));

    await waitFor(() => {
      expect(screen.getByText(/Failed to parse items/)).toBeInTheDocument();
    });
  });

  test('close button calls onClose', () => {
    const onClose = vi.fn();
    render(<BulkParseModal {...defaultProps} onClose={onClose} />);
    // The close button is the × character
    const closeButton = screen.getByRole('button', { name: '×' });
    fireEvent.click(closeButton);
    expect(onClose).toHaveBeenCalled();
  });
});
