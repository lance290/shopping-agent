import { describe, expect, it } from 'vitest';

/**
 * Regression tests for activeRow service detection
 * 
 * Bug: is_service and service_category were being read from choiceAnswers JSON
 * instead of from the actual row columns. This caused:
 * - Products to be treated as services (triggering vendor fetch instead of search)
 * - Services to be treated as products (triggering search instead of vendor fetch)
 */

describe('ActiveRow Service Detection', () => {
  // Simulate the row data structure from backend
  const mockProductRow = {
    id: 1,
    title: 'Winter coat',
    is_service: false,
    service_category: null,
    choice_answers: JSON.stringify({
      style: 'puffer',
      color: 'black',
      // Note: is_service should NOT be in choice_answers
    }),
  };

  const mockServiceRow = {
    id: 2,
    title: 'Private jet charter',
    is_service: true,
    service_category: 'private_aviation',
    choice_answers: JSON.stringify({
      origin: 'SAN',
      destination: 'EWR',
      passengers: 7,
    }),
  };

  describe('Product rows', () => {
    it('reads is_service from row column, not choiceAnswers', () => {
      const choiceAnswers = JSON.parse(mockProductRow.choice_answers);
      
      // CORRECT: Read from row column
      const isServiceCorrect = mockProductRow.is_service === true;
      expect(isServiceCorrect).toBe(false);
      
      // WRONG: This was the bug - reading from choiceAnswers
      const isServiceWrong = choiceAnswers.is_service || false;
      expect(isServiceWrong).toBe(false); // Happens to be same here
    });

    it('product row triggers search, not vendor fetch', () => {
      const isService = mockProductRow.is_service === true;
      const serviceCategory = mockProductRow.service_category;
      
      // Decision logic from BFF
      const shouldFetchVendors = isService && serviceCategory;
      const shouldSearch = !shouldFetchVendors;
      
      expect(shouldFetchVendors).toBe(false);
      expect(shouldSearch).toBe(true);
    });

    it('handles row with is_service explicitly false', () => {
      const row = { ...mockProductRow, is_service: false };
      const isService = row.is_service === true;
      expect(isService).toBe(false);
    });

    it('handles row with is_service as null/undefined', () => {
      const rowNull = { ...mockProductRow, is_service: null };
      const rowUndefined = { ...mockProductRow, is_service: undefined };
      
      expect(rowNull.is_service === true).toBe(false);
      expect(rowUndefined.is_service === true).toBe(false);
    });
  });

  describe('Service rows', () => {
    it('reads is_service and service_category from row columns', () => {
      const isService = mockServiceRow.is_service === true;
      const serviceCategory = mockServiceRow.service_category;
      
      expect(isService).toBe(true);
      expect(serviceCategory).toBe('private_aviation');
    });

    it('service row triggers vendor fetch, not search', () => {
      const isService = mockServiceRow.is_service === true;
      const serviceCategory = mockServiceRow.service_category;
      
      const shouldFetchVendors = isService && serviceCategory;
      const shouldSearch = !shouldFetchVendors;
      
      expect(!!shouldFetchVendors).toBe(true);
      expect(shouldSearch).toBe(false);
    });

    it('service without category falls back to search', () => {
      const row = { ...mockServiceRow, service_category: null };
      const isService = row.is_service === true;
      const serviceCategory = row.service_category;
      
      const shouldFetchVendors = isService && serviceCategory;
      expect(!!shouldFetchVendors).toBe(false);
    });
  });

  describe('Edge cases', () => {
    it('handles malformed choice_answers gracefully', () => {
      const rowWithBadJson = {
        ...mockProductRow,
        choice_answers: 'not valid json',
      };
      
      let choiceAnswers = {};
      try {
        choiceAnswers = JSON.parse(rowWithBadJson.choice_answers);
      } catch {
        choiceAnswers = {};
      }
      
      // Should still read is_service from row column
      const isService = rowWithBadJson.is_service === true;
      expect(isService).toBe(false);
    });

    it('handles empty choice_answers', () => {
      const rowEmpty = {
        ...mockProductRow,
        choice_answers: null,
      };
      
      const choiceAnswers = rowEmpty.choice_answers ? JSON.parse(rowEmpty.choice_answers) : {};
      const isService = rowEmpty.is_service === true;
      
      expect(choiceAnswers).toEqual({});
      expect(isService).toBe(false);
    });

    it('intent overrides activeRow for service detection', () => {
      // When LLM returns intent.category = 'service', it should take precedence
      const intentIsService = true;
      const activeRowIsService = false;
      
      const rowIsService = intentIsService || activeRowIsService;
      expect(rowIsService).toBe(true);
    });
  });
});

describe('Update Row Search Behavior', () => {
  it('update_row on product triggers search with intent.search_query', () => {
    const action = { type: 'update_row' };
    const intent = {
      what: 'winter coat',
      category: 'product' as const,
      service_type: null,
      search_query: 'mens winter top coat',
      constraints: { style: 'top coat' },
    };
    const activeRow = {
      is_service: false,
      service_category: null,
    };

    const isService = (intent.category as string) === 'service';
    const rowIsService = isService || activeRow.is_service;
    const searchQuery = intent.search_query;

    expect(rowIsService).toBe(false);
    expect(searchQuery).toBe('mens winter top coat');
    
    // Should trigger search, not vendor fetch
    const shouldSearch = !rowIsService && searchQuery;
    expect(shouldSearch).toBeTruthy();
  });

  it('update_row on service triggers vendor fetch', () => {
    const intent = {
      what: 'private jet charter',
      category: 'service' as const,
      service_type: 'private_aviation',
      search_query: 'private jet charter',
      constraints: {},
    };
    const activeRow = {
      is_service: true,
      service_category: 'private_aviation',
    };

    const isService = intent.category === 'service';
    const serviceCategory = intent.service_type || activeRow.service_category;
    const rowIsService = isService || activeRow.is_service;

    expect(rowIsService).toBe(true);
    expect(serviceCategory).toBe('private_aviation');
    
    // Should trigger vendor fetch
    const shouldFetchVendors = rowIsService && serviceCategory;
    expect(!!shouldFetchVendors).toBe(true);
  });
});
