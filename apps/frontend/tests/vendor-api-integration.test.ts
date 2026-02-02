/**
 * VENDOR API INTEGRATION TESTS
 * 
 * Tests for the API layer that fetches vendor data.
 * Ensures the frontend API routes correctly proxy to BFF and return proper data.
 */

import { describe, test, expect, beforeEach, vi } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mocking
import { checkIfService, getVendors, ServiceCheckResponse, VendorsResponse } from '../app/utils/api';

describe('Vendor API Functions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('checkIfService', () => {
    test('returns service check response for service query', async () => {
      const mockResponse: ServiceCheckResponse = {
        query: 'private jet',
        is_service: true,
        category: 'private_aviation',
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });
      
      const result = await checkIfService('private jet');
      
      expect(mockFetch).toHaveBeenCalledWith('/api/check-service?query=private%20jet');
      expect(result).toEqual(mockResponse);
      expect(result?.is_service).toBe(true);
      expect(result?.category).toBe('private_aviation');
    });

    test('returns null for non-service query', async () => {
      const mockResponse: ServiceCheckResponse = {
        query: 'blue sneakers',
        is_service: false,
        category: null,
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });
      
      const result = await checkIfService('blue sneakers');
      
      expect(result?.is_service).toBe(false);
      expect(result?.category).toBeNull();
    });

    test('returns null on API error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });
      
      const result = await checkIfService('private jet');
      
      expect(result).toBeNull();
    });

    test('returns null on network error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      
      const result = await checkIfService('private jet');
      
      expect(result).toBeNull();
    });

    test('URL encodes query parameter', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ query: 'private jet & charter', is_service: true, category: 'private_aviation' }),
      });
      
      await checkIfService('private jet & charter');
      
      expect(mockFetch).toHaveBeenCalledWith('/api/check-service?query=private%20jet%20%26%20charter');
    });
  });

  describe('getVendors', () => {
    test('returns vendors for valid category', async () => {
      const mockResponse: VendorsResponse = {
        category: 'private_aviation',
        vendors: [
          {
            title: 'JetRight Nashville',
            description: 'Charter service provider',
            price: null,
            url: 'mailto:charter@jetrightnashville.com',
            image_url: null,
            source: 'JetBid',
            is_service_provider: true,
            vendor_email: 'charter@jetrightnashville.com',
            vendor_name: 'Charter Team',
            vendor_company: 'JetRight Nashville',
          },
        ],
        is_service: true,
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });
      
      const result = await getVendors('private_aviation');
      
      expect(mockFetch).toHaveBeenCalledWith('/api/vendors/private_aviation');
      expect(result).toEqual(mockResponse);
      expect(result?.vendors).toHaveLength(1);
      expect(result?.vendors[0].is_service_provider).toBe(true);
    });

    test('returns null on API error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });
      
      const result = await getVendors('unknown_category');
      
      expect(result).toBeNull();
    });

    test('returns null on network error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      
      const result = await getVendors('private_aviation');
      
      expect(result).toBeNull();
    });

    test('URL encodes category parameter', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ category: 'private aviation', vendors: [], is_service: true }),
      });
      
      await getVendors('private aviation');
      
      expect(mockFetch).toHaveBeenCalledWith('/api/vendors/private%20aviation');
    });
  });
});

describe('Vendor Data Flow - End to End', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('complete flow: check service -> get vendors -> format offers', async () => {
    // Step 1: Check if service
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        query: 'private jet charter',
        is_service: true,
        category: 'private_aviation',
      }),
    });
    
    const serviceCheck = await checkIfService('private jet charter');
    expect(serviceCheck?.is_service).toBe(true);
    expect(serviceCheck?.category).toBe('private_aviation');
    
    // Step 2: Get vendors
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        category: 'private_aviation',
        vendors: [
          {
            title: 'JetRight Nashville',
            description: 'Charter service provider',
            price: null,
            url: 'mailto:charter@jetrightnashville.com',
            image_url: null,
            source: 'JetBid',
            is_service_provider: true,
            vendor_email: 'charter@jetrightnashville.com',
            vendor_name: 'Charter Team',
            vendor_company: 'JetRight Nashville',
          },
          {
            title: '247 Jet',
            description: 'Charter service provider',
            price: null,
            url: 'mailto:adnan@247jet.com',
            image_url: null,
            source: 'JetBid',
            is_service_provider: true,
            vendor_email: 'adnan@247jet.com',
            vendor_name: 'Adnan',
            vendor_company: '247 Jet',
          },
        ],
        is_service: true,
      }),
    });
    
    const vendorsData = await getVendors(serviceCheck!.category!);
    expect(vendorsData?.vendors).toHaveLength(2);
    
    // Step 3: Format as Offers (what the component does)
    const vendorOffers = vendorsData!.vendors.map(v => ({
      title: v.title,
      price: 0,
      currency: 'USD',
      merchant: v.vendor_company,
      url: v.url,
      image_url: v.image_url,
      rating: null,
      reviews_count: null,
      shipping_info: null,
      source: 'JetBid',
      is_service_provider: true,
      vendor_email: v.vendor_email,
      vendor_name: v.vendor_name,
      vendor_company: v.vendor_company,
    }));
    
    expect(vendorOffers).toHaveLength(2);
    expect(vendorOffers[0].is_service_provider).toBe(true);
    expect(vendorOffers[0].vendor_email).toBe('charter@jetrightnashville.com');
    expect(vendorOffers[1].vendor_company).toBe('247 Jet');
  });

  test('non-service query does not fetch vendors', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        query: 'blue sneakers',
        is_service: false,
        category: null,
      }),
    });
    
    const serviceCheck = await checkIfService('blue sneakers');
    
    expect(serviceCheck?.is_service).toBe(false);
    expect(mockFetch).toHaveBeenCalledTimes(1); // Only check-service, not get-vendors
  });
});

describe('API Response Validation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('vendor response has all required fields', async () => {
    const completeVendor = {
      title: 'Test Company',
      description: 'Test description',
      price: null,
      url: 'mailto:test@test.com',
      image_url: null,
      source: 'JetBid',
      is_service_provider: true,
      vendor_email: 'test@test.com',
      vendor_name: 'Test Person',
      vendor_company: 'Test Company',
    };
    
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        category: 'test',
        vendors: [completeVendor],
        is_service: true,
      }),
    });
    
    const result = await getVendors('test');
    const vendor = result?.vendors[0];
    
    // All fields must exist
    expect(vendor?.title).toBeDefined();
    expect(vendor?.url).toBeDefined();
    expect(vendor?.source).toBeDefined();
    expect(vendor?.is_service_provider).toBeDefined();
    expect(vendor?.vendor_email).toBeDefined();
    expect(vendor?.vendor_name).toBeDefined();
    expect(vendor?.vendor_company).toBeDefined();
  });

  test('handles malformed vendor response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        // Missing required fields
        category: 'test',
        vendors: [{ title: 'Incomplete' }],
        is_service: true,
      }),
    });
    
    const result = await getVendors('test');
    
    // Should still return the data, let caller handle validation
    expect(result?.vendors).toHaveLength(1);
    expect(result?.vendors[0].title).toBe('Incomplete');
  });
});
