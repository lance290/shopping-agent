/**
 * Tests for ui_schema_updated SSE event handling in the store.
 *
 * Covers:
 * - Store updateRow correctly sets ui_schema and ui_schema_version
 * - Row interface includes ui_schema fields
 * - Schema validation on received SSE data
 * - Fallback when schema is invalid
 */

import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore } from '../store';
import type { Row } from '../store';
import { validateUISchema, getMinimumViableRow } from '../sdui/types';

beforeEach(() => {
  useShoppingStore.setState({
    rows: [],
    projects: [],
    rowResults: {},
    rowProviderStatuses: {},
    rowSearchErrors: {},
    rowOfferSort: {},
    moreResultsIncoming: {},
    streamingRowIds: {},
    isSearching: false,
    activeRowId: null,
    currentQuery: '',
    cardClickQuery: null,
    pendingRowDelete: null,
  });
});

describe('ui_schema_updated SSE handler via store.updateRow', () => {
  test('updateRow sets ui_schema on row', () => {
    const store = useShoppingStore.getState();
    const row: Row = {
      id: 1, title: 'Eggs', status: 'sourcing', budget_max: null, currency: 'USD',
    };
    store.setRows([row]);

    const schema = {
      version: 1,
      layout: 'ROW_MEDIA_LEFT',
      blocks: [
        { type: 'ProductImage', url: 'https://img.com/eggs.jpg', alt: 'Eggs' },
        { type: 'PriceBlock', amount: 3.49, currency: 'USD', label: 'Best' },
      ],
    };

    store.updateRow(1, { ui_schema: schema, ui_schema_version: 1 });

    const updated = useShoppingStore.getState().rows.find((r) => r.id === 1);
    expect(updated?.ui_schema).toEqual(schema);
    expect(updated?.ui_schema_version).toBe(1);
  });

  test('updateRow overwrites previous ui_schema (full replacement)', () => {
    const store = useShoppingStore.getState();
    const row: Row = {
      id: 1, title: 'Eggs', status: 'sourcing', budget_max: null, currency: 'USD',
      ui_schema: { version: 1, layout: 'ROW_COMPACT', blocks: [] },
      ui_schema_version: 1,
    };
    store.setRows([row]);

    const newSchema = {
      version: 2,
      layout: 'ROW_MEDIA_LEFT',
      blocks: [{ type: 'MarkdownText', content: '**Updated**' }],
    };

    store.updateRow(1, { ui_schema: newSchema, ui_schema_version: 2 });

    const updated = useShoppingStore.getState().rows.find((r) => r.id === 1);
    expect(updated?.ui_schema_version).toBe(2);
    expect((updated?.ui_schema as any)?.layout).toBe('ROW_MEDIA_LEFT');
  });

  test('received schema validates via validateUISchema', () => {
    const sseSchema = {
      version: 1,
      layout: 'ROW_TIMELINE',
      value_vector: 'safety',
      blocks: [
        { type: 'DataGrid', items: [{ key: 'Origin', value: 'SAN' }] },
        { type: 'Timeline', steps: [{ label: 'Sourcing', status: 'done' }] },
        { type: 'ActionRow', actions: [{ label: 'Contact', intent: 'contact_vendor' }] },
      ],
    };
    const validated = validateUISchema(sseSchema);
    expect(validated).not.toBeNull();
    expect(validated!.layout).toBe('ROW_TIMELINE');
    expect(validated!.value_vector).toBe('safety');
  });

  test('invalid schema from SSE is rejected by validateUISchema', () => {
    const badSchema = { version: 'bad', layout: 'INVALID' };
    const validated = validateUISchema(badSchema);
    expect(validated).toBeNull();
  });

  test('null ui_schema handled gracefully', () => {
    const store = useShoppingStore.getState();
    const row: Row = {
      id: 1, title: 'Test', status: 'sourcing', budget_max: null, currency: 'USD',
      ui_schema: null,
    };
    store.setRows([row]);

    const found = useShoppingStore.getState().rows.find((r) => r.id === 1);
    expect(found?.ui_schema).toBeNull();

    // MVR fallback available
    const fallback = getMinimumViableRow('Test', 'sourcing');
    expect(validateUISchema(fallback)).not.toBeNull();
  });

  test('ui_schema persists across setRows calls', () => {
    const store = useShoppingStore.getState();
    const schema = { version: 1, layout: 'ROW_COMPACT', blocks: [] };
    const row: Row = {
      id: 1, title: 'Eggs', status: 'sourcing', budget_max: null, currency: 'USD',
      ui_schema: schema,
      ui_schema_version: 1,
    };
    store.setRows([row]);

    // Simulate a re-fetch that includes the same row
    store.setRows([{
      id: 1, title: 'Eggs', status: 'sourcing', budget_max: null, currency: 'USD',
      ui_schema: schema,
      ui_schema_version: 1,
    }]);

    const found = useShoppingStore.getState().rows.find((r) => r.id === 1);
    expect(found?.ui_schema).toEqual(schema);
  });
});

describe('Simulated SSE event processing', () => {
  test('grocery search_complete → ui_schema_updated flow', () => {
    const store = useShoppingStore.getState();
    store.setRows([{
      id: 42, title: 'Organic Eggs', status: 'sourcing', budget_max: null, currency: 'USD',
    }]);

    // Simulate: backend emits ui_schema_updated after search completes
    const sseData = {
      entity_type: 'row',
      entity_id: 42,
      schema: {
        version: 1,
        layout: 'ROW_MEDIA_LEFT',
        value_vector: 'unit_price',
        blocks: [
          { type: 'ProductImage', url: 'https://img.com/eggs.jpg', alt: 'Eggs' },
          { type: 'PriceBlock', amount: 3.49, currency: 'USD', label: 'Best Price' },
          { type: 'BadgeList', tags: ['Organic', 'Kroger'] },
          { type: 'ActionRow', actions: [{ label: 'View Deal', intent: 'outbound_affiliate' }] },
        ],
      },
      version: 1,
      trigger: 'search_complete',
    };

    // Frontend handler: store.updateRow(entityId, { ui_schema, ui_schema_version })
    store.updateRow(sseData.entity_id, {
      ui_schema: sseData.schema,
      ui_schema_version: sseData.version,
    });

    const row = useShoppingStore.getState().rows.find((r) => r.id === 42);
    expect(row?.ui_schema).not.toBeNull();
    expect((row?.ui_schema as any)?.layout).toBe('ROW_MEDIA_LEFT');
    expect((row?.ui_schema as any)?.value_vector).toBe('unit_price');
    expect(row?.ui_schema_version).toBe(1);
  });

  test('choice_factor_updated → new schema replaces old', () => {
    const store = useShoppingStore.getState();
    store.setRows([{
      id: 10, title: 'Laptop', status: 'sourcing', budget_max: null, currency: 'USD',
      ui_schema: { version: 1, layout: 'ROW_COMPACT', blocks: [] },
      ui_schema_version: 1,
    }]);

    // User answered choice factor → backend rebuilds schema
    store.updateRow(10, {
      ui_schema: {
        version: 2,
        layout: 'ROW_MEDIA_LEFT',
        blocks: [
          { type: 'ProductImage', url: 'https://img.com/laptop.jpg', alt: 'Laptop' },
          { type: 'PriceBlock', amount: 999, currency: 'USD', label: 'From' },
        ],
      },
      ui_schema_version: 2,
    });

    const row = useShoppingStore.getState().rows.find((r) => r.id === 10);
    expect(row?.ui_schema_version).toBe(2);
    expect((row?.ui_schema as any)?.layout).toBe('ROW_MEDIA_LEFT');
  });
});
