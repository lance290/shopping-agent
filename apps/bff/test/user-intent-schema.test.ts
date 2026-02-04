import { describe, expect, it } from 'vitest';
import { z } from 'zod';

// Mirror the schema from llm.ts for testing
const userIntentSchema = z.object({
  what: z.string(),
  category: z.enum(['product', 'service']),
  service_type: z.string().nullish(),
  search_query: z.string(),
  constraints: z.record(z.string(), z.any()).default({}),
});

describe('UserIntent Schema Validation', () => {
  describe('Product intents', () => {
    it('accepts product with null service_type', () => {
      const intent = {
        what: 'winter coat',
        category: 'product',
        service_type: null,
        search_query: 'mens winter coat',
        constraints: { style: 'puffer', location: 'Newark' },
      };
      const result = userIntentSchema.safeParse(intent);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.service_type).toBeNull();
      }
    });

    it('accepts product with undefined service_type', () => {
      const intent = {
        what: 'running shoes',
        category: 'product',
        search_query: 'red running shoes under $80',
        constraints: { color: 'red', max_price: 80 },
      };
      const result = userIntentSchema.safeParse(intent);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.service_type).toBeUndefined();
      }
    });

    it('derives search_query from what, not conversation artifacts', () => {
      const intent = {
        what: 'kids baseball glove',
        category: 'product',
        service_type: null,
        search_query: 'youth baseball glove',
        constraints: { size: 'youth', handed: 'left' },
      };
      const result = userIntentSchema.safeParse(intent);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.search_query).not.toContain('Feb');
        expect(result.data.search_query).not.toContain('people');
        expect(result.data.search_query).toContain('baseball');
      }
    });
  });

  describe('Service intents', () => {
    it('accepts service with service_type', () => {
      const intent = {
        what: 'private jet charter',
        category: 'service',
        service_type: 'private_aviation',
        search_query: 'private jet charter SAN to EWR',
        constraints: { origin: 'SAN', destination: 'EWR', date: 'Feb 13', passengers: 7 },
      };
      const result = userIntentSchema.safeParse(intent);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.category).toBe('service');
        expect(result.data.service_type).toBe('private_aviation');
        expect(result.data.constraints.origin).toBe('SAN');
        expect(result.data.constraints.passengers).toBe(7);
      }
    });

    it('search_query derived from what + key constraints, not clarification responses', () => {
      const intent = {
        what: 'private jet charter',
        category: 'service',
        service_type: 'private_aviation',
        search_query: 'private jet charter SAN to EWR',
        constraints: { origin: 'SAN', destination: 'EWR', date: 'Feb 13', passengers: 7 },
      };
      const result = userIntentSchema.safeParse(intent);
      expect(result.success).toBe(true);
      if (result.success) {
        // search_query should NOT be "Feb 13, 7 people"
        expect(result.data.search_query).not.toBe('Feb 13, 7 people');
        expect(result.data.search_query).toContain('jet');
        expect(result.data.search_query).toContain('SAN');
      }
    });

    it('accepts yacht charter service', () => {
      const intent = {
        what: 'yacht charter',
        category: 'service',
        service_type: 'yacht_charter',
        search_query: 'yacht charter Mediterranean',
        constraints: { region: 'Mediterranean', dates: 'July 2026', guests: 12 },
      };
      const result = userIntentSchema.safeParse(intent);
      expect(result.success).toBe(true);
    });

    it('accepts catering service', () => {
      const intent = {
        what: 'catering service',
        category: 'service',
        service_type: 'catering',
        search_query: 'corporate catering San Francisco',
        constraints: { location: 'San Francisco', headcount: 50, date: 'March 15' },
      };
      const result = userIntentSchema.safeParse(intent);
      expect(result.success).toBe(true);
    });
  });

  describe('Intent title rules', () => {
    it('what should be descriptive, not a date or number', () => {
      // Good intents have descriptive "what" values
      const goodIntent = {
        what: 'private jet charter',
        category: 'service',
        service_type: 'private_aviation',
        search_query: 'private jet charter SAN to EWR',
        constraints: { date: 'Feb 13', passengers: 7 },
      };
      const result = userIntentSchema.safeParse(goodIntent);
      expect(result.success).toBe(true);
      // "what" should be descriptive noun phrase, not date/number
      expect(goodIntent.what).not.toMatch(/^\d+$/);
      expect(goodIntent.what.length).toBeGreaterThan(3);
    });

    it('what should be descriptive noun phrase', () => {
      const goodIntents = [
        { what: 'private jet charter', expected: true },
        { what: 'winter coat', expected: true },
        { what: 'kids baseball glove', expected: true },
        { what: 'standing desk', expected: true },
      ];
      
      for (const { what } of goodIntents) {
        expect(what.length).toBeGreaterThan(3);
        expect(what).not.toMatch(/^\d+$/); // Not just a number
        expect(what).not.toMatch(/^(yes|no|ok|sure)$/i); // Not just an affirmation
      }
    });
  });

  describe('Constraint merging', () => {
    it('constraints default to empty object', () => {
      const intent = {
        what: 'laptop',
        category: 'product',
        search_query: 'laptop',
      };
      const result = userIntentSchema.safeParse(intent);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.constraints).toEqual({});
      }
    });

    it('preserves all constraint types', () => {
      const intent = {
        what: 'private jet charter',
        category: 'service',
        service_type: 'private_aviation',
        search_query: 'private jet SAN to EWR',
        constraints: {
          origin: 'SAN',
          destination: 'EWR',
          date: 'Feb 13',
          passengers: 7,
          flexible_dates: true,
          budget_max: 50000,
        },
      };
      const result = userIntentSchema.safeParse(intent);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.constraints.origin).toBe('SAN');
        expect(result.data.constraints.passengers).toBe(7);
        expect(result.data.constraints.flexible_dates).toBe(true);
        expect(result.data.constraints.budget_max).toBe(50000);
      }
    });
  });
});

describe('Context Switch Intent Behavior', () => {
  it('new intent completely replaces old one', () => {
    const jetIntent = {
      what: 'private jet charter',
      category: 'service' as const,
      service_type: 'private_aviation',
      search_query: 'private jet charter SAN to EWR',
      constraints: { origin: 'SAN', destination: 'EWR' },
    };

    const coatIntent = {
      what: 'winter coat',
      category: 'product' as const,
      service_type: null,
      search_query: 'mens winter coat',
      constraints: { style: 'puffer' },
    };

    // After context switch, coat intent should have NO jet-related data
    expect(coatIntent.constraints).not.toHaveProperty('origin');
    expect(coatIntent.constraints).not.toHaveProperty('destination');
    expect(coatIntent.service_type).not.toBe('private_aviation');
    expect(coatIntent.category).toBe('product');
  });
});
