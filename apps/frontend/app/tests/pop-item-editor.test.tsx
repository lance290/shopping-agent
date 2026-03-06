/**
 * PopItemEditor component tests — PRD-02 (Taxonomy UI).
 *
 * Covers:
 *   - Renders form fields with initial values
 *   - Save button disabled when title is empty
 *   - No-op when nothing changed (calls onClose, not onSaved)
 *   - Sends PATCH with only changed fields
 *   - Calls onSaved with API response data
 *   - Shows attribution channel label
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import PopItemEditor from '../pop-site/list/[id]/PopItemEditor';

beforeEach(() => {
  vi.restoreAllMocks();
});

const baseItem = {
  id: 42,
  title: 'Chicken Breast',
  department: 'Meat',
  brand: 'Tyson',
  size: '2 lbs',
  quantity: '1',
  origin_channel: 'sms' as const,
  origin_user_id: 7,
};

describe('PopItemEditor', () => {
  test('renders form fields with initial values', () => {
    render(<PopItemEditor item={baseItem} onClose={vi.fn()} onSaved={vi.fn()} />);
    expect(screen.getByDisplayValue('Chicken Breast')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Tyson')).toBeInTheDocument();
    expect(screen.getByDisplayValue('2 lbs')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1')).toBeInTheDocument();
    expect(screen.getByText('Edit Item')).toBeInTheDocument();
  });

  test('shows attribution channel label', () => {
    render(<PopItemEditor item={baseItem} onClose={vi.fn()} onSaved={vi.fn()} />);
    expect(screen.getByText('Added via SMS')).toBeInTheDocument();
  });

  test('no attribution label when origin_channel is null', () => {
    const item = { ...baseItem, origin_channel: null };
    render(<PopItemEditor item={item} onClose={vi.fn()} onSaved={vi.fn()} />);
    expect(screen.queryByText(/Added via/)).not.toBeInTheDocument();
  });

  test('save button disabled when title is empty', () => {
    render(<PopItemEditor item={baseItem} onClose={vi.fn()} onSaved={vi.fn()} />);
    const titleInput = screen.getByDisplayValue('Chicken Breast');
    fireEvent.change(titleInput, { target: { value: '' } });
    expect(screen.getByRole('button', { name: /Save/i })).toBeDisabled();
  });

  test('no-op save calls onClose when nothing changed', async () => {
    const onClose = vi.fn();
    const onSaved = vi.fn();
    render(<PopItemEditor item={baseItem} onClose={onClose} onSaved={onSaved} />);
    fireEvent.click(screen.getByRole('button', { name: /Save/i }));
    // Should call onClose directly without fetch
    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
    expect(onSaved).not.toHaveBeenCalled();
  });

  test('sends PATCH with only changed fields', async () => {
    const updated = { ...baseItem, brand: 'Perdue', department: 'Meat' };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(updated),
    });

    const onSaved = vi.fn();
    render(<PopItemEditor item={baseItem} onClose={vi.fn()} onSaved={onSaved} />);

    const brandInput = screen.getByDisplayValue('Tyson');
    fireEvent.change(brandInput, { target: { value: 'Perdue' } });
    fireEvent.click(screen.getByRole('button', { name: /Save/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/pop/item/42',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ brand: 'Perdue' }),
        }),
      );
    });

    await waitFor(() => {
      expect(onSaved).toHaveBeenCalledWith(updated);
    });
  });

  test('department select has all standard departments', () => {
    render(<PopItemEditor item={baseItem} onClose={vi.fn()} onSaved={vi.fn()} />);
    const departments = ['Produce', 'Meat', 'Dairy', 'Pantry', 'Frozen', 'Bakery', 'Household', 'Personal Care', 'Pet', 'Other'];
    for (const dept of departments) {
      expect(screen.getByText(dept)).toBeInTheDocument();
    }
  });
});
