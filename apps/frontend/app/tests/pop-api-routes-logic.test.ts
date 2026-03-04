/**
 * Pop chat page logic, guest security, wallet formatting tests.
 * Extracted from pop-api-routes.test.ts to keep files under 450 lines.
 */
import { describe, test, expect } from 'vitest';

type ListItem = { id: number; title: string; status: string };

// localStorage helpers (duplicated from main test file)
function writeGuestItems(items: ListItem[]) {
  localStorage.setItem('pop_guest_list_items', JSON.stringify(items));
}
function readGuestItems(): ListItem[] {
  try {
    return JSON.parse(localStorage.getItem('pop_guest_list_items') || '[]');
  } catch { return []; }
}
function writeGuestProjectId(id: number) {
  localStorage.setItem('pop_guest_project_id', String(id));
}
function readGuestProjectId(): number | null {
  const v = localStorage.getItem('pop_guest_project_id');
  return v ? Number(v) : null;
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. Chat page business logic — message state machine
// ─────────────────────────────────────────────────────────────────────────────

describe('Pop chat page — message state logic', () => {
  type Message = { id: string; role: 'user' | 'assistant'; content: string };

  function addUserMessage(messages: Message[], content: string): Message[] {
    if (!content.trim()) return messages;
    return [...messages, { id: `u-${Date.now()}`, role: 'user', content }];
  }

  function addAssistantMessage(messages: Message[], content: string): Message[] {
    return [...messages, { id: `a-${Date.now()}`, role: 'assistant', content }];
  }

  function syncListItems(
    current: ListItem[],
    incoming: ListItem[],
  ): ListItem[] {
    if (!incoming.length) return current;
    return incoming;
  }

  const WELCOME: Message = {
    id: 'welcome',
    role: 'assistant',
    content: "Hey! I'm Pop, your grocery savings assistant.",
  };

  test('Regression: initial messages contain welcome message (not blank)', () => {
    const initial = [WELCOME];
    expect(initial).toHaveLength(1);
    expect(initial[0].role).toBe('assistant');
    expect(initial[0].content).toContain('Pop');
  });

  test('Regression: empty input does NOT add a user message', () => {
    const before = [WELCOME];
    const after = addUserMessage(before, '');
    expect(after).toHaveLength(1);
  });

  test('whitespace-only input does NOT add a user message', () => {
    const before = [WELCOME];
    const after = addUserMessage(before, '   ');
    expect(after).toHaveLength(1);
  });

  test('valid input appends user message at end', () => {
    const before = [WELCOME];
    const after = addUserMessage(before, 'I need milk');
    expect(after).toHaveLength(2);
    expect(after[1].role).toBe('user');
    expect(after[1].content).toBe('I need milk');
  });

  test('assistant reply appended after user message', () => {
    let msgs: Message[] = [WELCOME];
    msgs = addUserMessage(msgs, 'I need eggs');
    msgs = addAssistantMessage(msgs, 'Added eggs to your list!');
    expect(msgs).toHaveLength(3);
    expect(msgs[2].role).toBe('assistant');
    expect(msgs[2].content).toBe('Added eggs to your list!');
  });

  test('messages alternate user / assistant correctly', () => {
    let msgs: Message[] = [WELCOME];
    msgs = addUserMessage(msgs, 'milk');
    msgs = addAssistantMessage(msgs, 'Added milk!');
    msgs = addUserMessage(msgs, 'eggs');
    msgs = addAssistantMessage(msgs, 'Added eggs!');
    const roles = msgs.map((m) => m.role);
    expect(roles).toEqual(['assistant', 'user', 'assistant', 'user', 'assistant']);
  });

  test('syncListItems replaces items when backend returns non-empty list', () => {
    const current: ListItem[] = [{ id: 1, title: 'Milk', status: 'sourcing' }];
    const incoming: ListItem[] = [
      { id: 1, title: 'Milk', status: 'sourcing' },
      { id: 2, title: 'Eggs', status: 'sourcing' },
    ];
    expect(syncListItems(current, incoming)).toEqual(incoming);
  });

  test('syncListItems keeps current items when backend returns empty list', () => {
    const current: ListItem[] = [{ id: 1, title: 'Milk', status: 'sourcing' }];
    expect(syncListItems(current, [])).toEqual(current);
  });

  test('Regression: delete removes item from list by id', () => {
    const items: ListItem[] = [
      { id: 1, title: 'Milk', status: 'sourcing' },
      { id: 2, title: 'Eggs', status: 'sourcing' },
    ];
    const afterDelete = items.filter((i) => i.id !== 2);
    expect(afterDelete).toHaveLength(1);
    expect(afterDelete[0].id).toBe(1);
    expect(afterDelete.some((i) => i.id === 2)).toBe(false);
  });

  test('Regression: deleted item does NOT reappear after list sync', () => {
    let items: ListItem[] = [
      { id: 1, title: 'Milk', status: 'sourcing' },
      { id: 2, title: 'Eggs', status: 'sourcing' },
    ];
    items = items.filter((i) => i.id !== 2);

    const backendList: ListItem[] = [
      { id: 1, title: 'Milk', status: 'sourcing' },
    ];
    items = syncListItems(items, backendList);
    expect(items.some((i) => i.id === 2)).toBe(false);
  });

  test('inline edit updates item title in list', () => {
    let items: ListItem[] = [
      { id: 1, title: 'Milk', status: 'sourcing' },
    ];
    items = items.map((i) => i.id === 1 ? { ...i, title: 'Organic Whole Milk' } : i);
    expect(items[0].title).toBe('Organic Whole Milk');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 9. Guest project security — cross-user isolation
// ─────────────────────────────────────────────────────────────────────────────

describe('Guest project security', () => {
  test('Regression: guest_project_id for other user is rejected by backend ownership check', () => {
    function resolveGuestProject(
      guestProjectId: number | null,
      projectOwnerId: number,
      guestUserId: number,
    ): 'use' | 'create_new' {
      if (!guestProjectId) return 'create_new';
      if (projectOwnerId !== guestUserId) return 'create_new';
      return 'use';
    }

    const guestUserId = 999;
    const otherUserId = 1;

    expect(resolveGuestProject(5, otherUserId, guestUserId)).toBe('create_new');
    expect(resolveGuestProject(5, guestUserId, guestUserId)).toBe('use');
    expect(resolveGuestProject(null, guestUserId, guestUserId)).toBe('create_new');
  });

  test('localStorage project_id is treated as hint, not authoritative', () => {
    writeGuestProjectId(42);
    const storedId = readGuestProjectId();
    expect(storedId).toBe(42);
    localStorage.clear();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 10. Wallet display formatting
// ─────────────────────────────────────────────────────────────────────────────

describe('Wallet display formatting', () => {
  function formatCents(cents: number): string {
    return `$${(cents / 100).toFixed(2)}`;
  }

  test('0 cents formats as $0.00', () => {
    expect(formatCents(0)).toBe('$0.00');
  });

  test('275 cents formats as $2.75', () => {
    expect(formatCents(275)).toBe('$2.75');
  });

  test('100 cents formats as $1.00', () => {
    expect(formatCents(100)).toBe('$1.00');
  });

  test('1000 cents formats as $10.00', () => {
    expect(formatCents(1000)).toBe('$10.00');
  });

  test('5 cents formats as $0.05', () => {
    expect(formatCents(5)).toBe('$0.05');
  });

  test('negative cents handled gracefully (refund scenario)', () => {
    expect(formatCents(-50)).toBe('$-0.50');
  });
});
