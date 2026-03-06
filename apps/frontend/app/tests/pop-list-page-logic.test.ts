/**
 * Pop list page logic tests — PRD-02 (Taxonomy), PRD-04 (Bulk Actions), PRD-05 (Speed UX).
 *
 * Tests cover:
 *   - Expanded state: all items expanded by default on load (PRD-05)
 *   - Toggle expansion: individual toggle without collapsing others (PRD-05)
 *   - Checked items: toggle check, clear completed sends row_ids (PRD-04)
 *   - Bulk parse: new items prepended + auto-expanded (PRD-04 + PRD-05)
 *   - Taxonomy extraction from item data (PRD-02)
 */
import { describe, test, expect } from 'vitest';

// ─────────────────────────────────────────────────────────────────────────────
// Types (mirrored from page.tsx)
// ─────────────────────────────────────────────────────────────────────────────

interface ListItem {
  id: number;
  title: string;
  status: string;
  deals: { id: number; title: string; price: number | null; source: string; url: string | null; image_url: string | null }[];
  swaps: { id: number; title: string; price: number | null; source: string; url: string | null; image_url: string | null; savings_vs_first: number | null }[];
  lowest_price: number | null;
  deal_count: number;
  department?: string | null;
  brand?: string | null;
  size?: string | null;
  quantity?: string | null;
  origin_channel?: string | null;
  origin_user_id?: number | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Logic extracted from page.tsx for testability
// ─────────────────────────────────────────────────────────────────────────────

function initExpandedItems(items: ListItem[]): Set<number> {
  return new Set(items.map((i) => i.id));
}

function toggleExpanded(prev: Set<number>, itemId: number): Set<number> {
  const next = new Set(prev);
  if (next.has(itemId)) next.delete(itemId);
  else next.add(itemId);
  return next;
}

function toggleChecked(prev: Set<number>, itemId: number): Set<number> {
  const next = new Set(prev);
  if (next.has(itemId)) next.delete(itemId);
  else next.add(itemId);
  return next;
}

function buildClearCompletedPayload(checkedItems: Set<number>): { row_ids: number[] } {
  return { row_ids: Array.from(checkedItems) };
}

function handleClearCompletedLocally(
  items: ListItem[],
  checkedItems: Set<number>,
): { items: ListItem[]; checkedItems: Set<number> } {
  return {
    items: items.filter((item) => !checkedItems.has(item.id)),
    checkedItems: new Set(),
  };
}

function handleBulkParsed(
  currentItems: ListItem[],
  newItems: ListItem[],
  expandedItems: Set<number>,
): { items: ListItem[]; expandedItems: Set<number> } {
  const nextExpanded = new Set(expandedItems);
  newItems.forEach((item) => nextExpanded.add(item.id));
  return {
    items: [...newItems, ...currentItems],
    expandedItems: nextExpanded,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Fixtures
// ─────────────────────────────────────────────────────────────────────────────

function makeItem(id: number, title: string, overrides: Partial<ListItem> = {}): ListItem {
  return {
    id,
    title,
    status: 'sourcing',
    deals: [],
    swaps: [],
    lowest_price: null,
    deal_count: 0,
    department: null,
    brand: null,
    size: null,
    quantity: null,
    origin_channel: null,
    origin_user_id: null,
    ...overrides,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// PRD-05: List Expanded by Default
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-05: List expanded by default', () => {
  test('all items expanded on initial load', () => {
    const items = [makeItem(1, 'Milk'), makeItem(2, 'Bread'), makeItem(3, 'Eggs')];
    const expanded = initExpandedItems(items);
    expect(expanded.size).toBe(3);
    expect(expanded.has(1)).toBe(true);
    expect(expanded.has(2)).toBe(true);
    expect(expanded.has(3)).toBe(true);
  });

  test('empty list produces empty expanded set', () => {
    const expanded = initExpandedItems([]);
    expect(expanded.size).toBe(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// PRD-05: No Auto-Collapse (Accordion Disabled)
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-05: No auto-collapse', () => {
  test('collapsing one item does not affect others', () => {
    const items = [makeItem(1, 'Milk'), makeItem(2, 'Bread'), makeItem(3, 'Eggs')];
    let expanded = initExpandedItems(items);
    expanded = toggleExpanded(expanded, 2); // collapse Bread
    expect(expanded.has(1)).toBe(true);
    expect(expanded.has(2)).toBe(false);
    expect(expanded.has(3)).toBe(true);
  });

  test('expanding a collapsed item does not affect others', () => {
    let expanded = new Set([1, 3]); // 2 is collapsed
    expanded = toggleExpanded(expanded, 2); // expand Bread
    expect(expanded.has(1)).toBe(true);
    expect(expanded.has(2)).toBe(true);
    expect(expanded.has(3)).toBe(true);
  });

  test('toggle is idempotent: double toggle returns to original state', () => {
    const original = new Set([1, 2, 3]);
    let expanded = toggleExpanded(original, 2);
    expanded = toggleExpanded(expanded, 2);
    expect(expanded).toEqual(original);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// PRD-04: Clear Completed
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-04: Clear completed', () => {
  test('buildClearCompletedPayload sends checked item IDs', () => {
    const checked = new Set([10, 20, 30]);
    const payload = buildClearCompletedPayload(checked);
    expect(payload.row_ids).toHaveLength(3);
    expect(payload.row_ids).toContain(10);
    expect(payload.row_ids).toContain(20);
    expect(payload.row_ids).toContain(30);
  });

  test('empty checked items sends empty array', () => {
    const payload = buildClearCompletedPayload(new Set());
    expect(payload.row_ids).toEqual([]);
  });

  test('handleClearCompletedLocally removes checked items and resets set', () => {
    const items = [makeItem(1, 'Milk'), makeItem(2, 'Bread'), makeItem(3, 'Eggs')];
    const checked = new Set([1, 3]);
    const result = handleClearCompletedLocally(items, checked);
    expect(result.items).toHaveLength(1);
    expect(result.items[0].title).toBe('Bread');
    expect(result.checkedItems.size).toBe(0);
  });

  test('clearing with no checked items is a no-op', () => {
    const items = [makeItem(1, 'Milk'), makeItem(2, 'Bread')];
    const result = handleClearCompletedLocally(items, new Set());
    expect(result.items).toHaveLength(2);
    expect(result.checkedItems.size).toBe(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// PRD-04 + PRD-05: Bulk Parse
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-04: Bulk parse items', () => {
  test('new items prepended to existing list', () => {
    const existing = [makeItem(1, 'Milk')];
    const parsed = [makeItem(100, 'Chicken'), makeItem(101, 'Tortillas')];
    const result = handleBulkParsed(existing, parsed, new Set([1]));
    expect(result.items).toHaveLength(3);
    expect(result.items[0].title).toBe('Chicken');
    expect(result.items[1].title).toBe('Tortillas');
    expect(result.items[2].title).toBe('Milk');
  });

  test('new items auto-expanded (PRD-05 consistency)', () => {
    const existing = [makeItem(1, 'Milk')];
    const parsed = [makeItem(100, 'Chicken'), makeItem(101, 'Tortillas')];
    const result = handleBulkParsed(existing, parsed, new Set([1]));
    expect(result.expandedItems.has(1)).toBe(true);
    expect(result.expandedItems.has(100)).toBe(true);
    expect(result.expandedItems.has(101)).toBe(true);
  });

  test('bulk parse into empty list works', () => {
    const parsed = [makeItem(10, 'Eggs')];
    const result = handleBulkParsed([], parsed, new Set());
    expect(result.items).toHaveLength(1);
    expect(result.expandedItems.has(10)).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Checked items state
// ─────────────────────────────────────────────────────────────────────────────

describe('Checked items toggle', () => {
  test('checking an unchecked item adds it', () => {
    const checked = toggleChecked(new Set(), 5);
    expect(checked.has(5)).toBe(true);
  });

  test('unchecking a checked item removes it', () => {
    const checked = toggleChecked(new Set([5]), 5);
    expect(checked.has(5)).toBe(false);
  });

  test('checking multiple items independently', () => {
    let checked = new Set<number>();
    checked = toggleChecked(checked, 1);
    checked = toggleChecked(checked, 3);
    expect(checked.size).toBe(2);
    expect(checked.has(1)).toBe(true);
    expect(checked.has(2)).toBe(false);
    expect(checked.has(3)).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// PRD-02: Taxonomy display
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-02: Taxonomy fields in list items', () => {
  test('item with taxonomy fields exposes them correctly', () => {
    const item = makeItem(1, 'Chicken Breast', {
      department: 'Meat',
      brand: 'Tyson',
      size: '2 lbs',
      quantity: '1',
      origin_channel: 'sms',
      origin_user_id: 42,
    });
    expect(item.department).toBe('Meat');
    expect(item.brand).toBe('Tyson');
    expect(item.size).toBe('2 lbs');
    expect(item.quantity).toBe('1');
    expect(item.origin_channel).toBe('sms');
    expect(item.origin_user_id).toBe(42);
  });

  test('item without taxonomy has null fields', () => {
    const item = makeItem(1, 'Milk');
    expect(item.department).toBeNull();
    expect(item.brand).toBeNull();
    expect(item.origin_channel).toBeNull();
  });
});
