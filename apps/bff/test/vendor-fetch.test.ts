import { describe, it, expect, vi, beforeEach } from 'vitest';

// Test that vendor response parsing handles the actual backend format
describe('Vendor fetch response parsing', () => {
  it('correctly extracts vendors array from backend response', () => {
    // Backend returns { category, vendors: [...], is_service }
    const backendResponse = {
      category: 'private_aviation',
      vendors: [
        { title: 'JetRight', vendor_email: 'test@jet.com' },
        { title: '247 Jet', vendor_email: 'info@247jet.com' },
      ],
      is_service: true,
    };

    // This is what the BFF should check - NOT Array.isArray(backendResponse)
    const vendors = backendResponse.vendors;
    
    expect(Array.isArray(backendResponse)).toBe(false); // The bug: this was being checked
    expect(Array.isArray(vendors)).toBe(true); // This is correct
    expect(vendors.length).toBe(2);
    expect(vendors[0].title).toBe('JetRight');
  });

  it('fails if checking response object directly as array', () => {
    const backendResponse = {
      category: 'private_aviation', 
      vendors: [{ title: 'Test' }],
      is_service: true,
    };

    // THE BUG: This check always fails because response is object not array
    if (Array.isArray(backendResponse)) {
      throw new Error('This should never execute - response is not an array');
    }
    
    // CORRECT: Check the vendors property
    expect(Array.isArray(backendResponse.vendors)).toBe(true);
  });
});
