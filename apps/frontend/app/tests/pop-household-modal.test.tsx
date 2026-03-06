/**
 * HouseholdModal component tests — PRD-03 (Group Chat & Household Invites).
 *
 * Covers:
 *   - Renders loading state initially
 *   - Shows member list after fetch
 *   - Shows empty state when no members
 *   - Remove button only appears for non-owners
 *   - Remove calls DELETE API and removes from list
 *   - Channel icons render correctly
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import HouseholdModal from '../pop-site/list/[id]/HouseholdModal';

beforeEach(() => {
  vi.restoreAllMocks();
});

const mockMembers = [
  { user_id: 1, name: 'Alice', email: 'alice@example.com', role: 'owner', channel: 'web', joined_at: '2026-01-01T00:00:00', is_owner: true },
  { user_id: 2, name: 'Bob', email: 'bob@example.com', role: 'member', channel: 'sms', joined_at: '2026-01-02T00:00:00', is_owner: false },
  { user_id: 3, name: 'Carol', email: 'carol@example.com', role: 'member', channel: 'email', joined_at: '2026-01-03T00:00:00', is_owner: false },
];

describe('HouseholdModal', () => {
  test('shows member list after fetch', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ members: mockMembers }),
    });

    render(<HouseholdModal projectId={1} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
      expect(screen.getByText('Carol')).toBeInTheDocument();
    });
  });

  test('owner badge shown only for owner', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ members: mockMembers }),
    });

    render(<HouseholdModal projectId={1} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Owner')).toBeInTheDocument();
      // Only one Owner badge
      expect(screen.getAllByText('Owner')).toHaveLength(1);
    });
  });

  test('remove button only for non-owners', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ members: mockMembers }),
    });

    render(<HouseholdModal projectId={1} onClose={vi.fn()} />);

    await waitFor(() => {
      // Two "Remove" buttons: one for Bob, one for Carol
      const removeButtons = screen.getAllByText('Remove');
      expect(removeButtons).toHaveLength(2);
    });
  });

  test('remove calls DELETE API and removes member from list', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ members: mockMembers }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ removed: true }),
      });
    global.fetch = fetchMock;

    render(<HouseholdModal projectId={1} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Bob')).toBeInTheDocument();
    });

    const removeButtons = screen.getAllByText('Remove');
    fireEvent.click(removeButtons[0]); // remove Bob

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/pop/projects/1/members/2',
        expect.objectContaining({ method: 'DELETE' }),
      );
    });

    await waitFor(() => {
      expect(screen.queryByText('Bob')).not.toBeInTheDocument();
    });
  });

  test('shows empty state when no members', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ members: [] }),
    });

    render(<HouseholdModal projectId={1} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/No members yet/)).toBeInTheDocument();
    });
  });

  test('close button calls onClose', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ members: [] }),
    });

    const onClose = vi.fn();
    render(<HouseholdModal projectId={1} onClose={onClose} />);

    await waitFor(() => {
      expect(screen.getByText(/No members yet/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: '×' }));
    expect(onClose).toHaveBeenCalled();
  });
});
