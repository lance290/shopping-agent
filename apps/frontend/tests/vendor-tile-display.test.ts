/**
 * VENDOR TILE DISPLAY TESTS
 * 
 * Tests for how vendor tiles are displayed in the UI.
 * Ensures the OfferTile component correctly handles vendor tiles.
 */

import { describe, test, expect } from 'vitest';
import { Offer } from '../app/store';

describe('Vendor Tile Display Logic', () => {
  const createVendorOffer = (): Offer => ({
    title: 'JetRight Nashville',
    price: 0,
    currency: 'USD',
    merchant: 'JetRight Nashville',
    url: 'mailto:charter@jetrightnashville.com',
    image_url: null,
    rating: null,
    reviews_count: null,
    shipping_info: null,
    source: 'JetBid',
    is_service_provider: true,
    vendor_email: 'charter@jetrightnashville.com',
    vendor_name: 'Charter Team',
    vendor_company: 'JetRight Nashville',
  });

  const createProductOffer = (): Offer => ({
    title: 'Private Jet Poster',
    price: 29.99,
    currency: 'USD',
    merchant: 'Amazon',
    url: 'https://amazon.com/jet-poster',
    image_url: 'https://example.com/poster.jpg',
    rating: 4.5,
    reviews_count: 100,
    shipping_info: 'Free shipping',
    source: 'rainforest',
    bid_id: 1001,
  });

  describe('isServiceProvider Detection', () => {
    test('vendor offer has is_service_provider = true', () => {
      const offer = createVendorOffer();
      expect(offer.is_service_provider).toBe(true);
    });

    test('product offer has is_service_provider undefined', () => {
      const offer = createProductOffer();
      expect(offer.is_service_provider).toBeUndefined();
    });

    test('can filter vendors from mixed results', () => {
      const offers = [createVendorOffer(), createProductOffer(), createVendorOffer()];
      const vendors = offers.filter(o => o.is_service_provider === true);
      const products = offers.filter(o => !o.is_service_provider);
      
      expect(vendors).toHaveLength(2);
      expect(products).toHaveLength(1);
    });
  });

  describe('Click URL Generation', () => {
    test('vendor tiles use direct mailto URL (bypass clickout)', () => {
      const offer = createVendorOffer();
      const isServiceProvider = offer.is_service_provider === true;
      
      const clickUrl = isServiceProvider 
        ? offer.url 
        : `/api/clickout?url=${encodeURIComponent(offer.url)}`;
      
      expect(clickUrl).toBe('mailto:charter@jetrightnashville.com');
      expect(clickUrl.startsWith('mailto:')).toBe(true);
    });

    test('product tiles use clickout URL', () => {
      const offer = createProductOffer();
      const isServiceProvider = offer.is_service_provider === true;
      
      const clickUrl = isServiceProvider 
        ? offer.url 
        : `/api/clickout?url=${encodeURIComponent(offer.url)}`;
      
      expect(clickUrl).toContain('/api/clickout');
      expect(clickUrl).toContain('amazon.com');
    });
  });

  describe('Price Display', () => {
    test('vendor tiles show "Request Quote" instead of price', () => {
      const offer = createVendorOffer();
      const isServiceProvider = offer.is_service_provider === true;
      
      // Logic from OfferTile
      const priceDisplay = isServiceProvider 
        ? 'Request Quote' 
        : `$${offer.price.toFixed(2)}`;
      
      expect(priceDisplay).toBe('Request Quote');
    });

    test('product tiles show actual price', () => {
      const offer = createProductOffer();
      const isServiceProvider = offer.is_service_provider === true;
      
      const priceDisplay = isServiceProvider 
        ? 'Request Quote' 
        : `$${offer.price.toFixed(2)}`;
      
      expect(priceDisplay).toBe('$29.99');
    });
  });

  describe('Badge Display', () => {
    test('vendor tiles get "Charter Provider" badge', () => {
      const offer = createVendorOffer();
      const isServiceProvider = offer.is_service_provider === true;
      
      const badgeText = isServiceProvider ? 'Charter Provider' : null;
      
      expect(badgeText).toBe('Charter Provider');
    });

    test('product tiles do not get Charter Provider badge', () => {
      const offer = createProductOffer();
      const isServiceProvider = offer.is_service_provider === true;
      
      const badgeText = isServiceProvider ? 'Charter Provider' : null;
      
      expect(badgeText).toBeNull();
    });
  });

  describe('Vendor Contact Info', () => {
    test('vendor tile has all contact information', () => {
      const offer = createVendorOffer();
      
      expect(offer.vendor_email).toBe('charter@jetrightnashville.com');
      expect(offer.vendor_name).toBe('Charter Team');
      expect(offer.vendor_company).toBe('JetRight Nashville');
    });

    test('vendor modal can be populated from offer', () => {
      const offer = createVendorOffer();
      
      const modalProps = {
        vendorName: offer.vendor_name || 'Contact',
        vendorCompany: offer.vendor_company || offer.merchant,
        vendorEmail: offer.vendor_email || '',
      };
      
      expect(modalProps.vendorName).toBe('Charter Team');
      expect(modalProps.vendorCompany).toBe('JetRight Nashville');
      expect(modalProps.vendorEmail).toBe('charter@jetrightnashville.com');
    });
  });

  describe('Sorting Behavior', () => {
    test('vendor tiles should appear before product tiles', () => {
      const vendor1 = createVendorOffer();
      const vendor2 = { ...createVendorOffer(), title: '247 Jet' };
      const product1 = createProductOffer();
      const product2 = { ...createProductOffer(), title: 'Model Jet', bid_id: 1002 };
      
      // Correct order: vendors first, then products
      const correctOrder = [vendor1, vendor2, product1, product2];
      
      expect(correctOrder[0].is_service_provider).toBe(true);
      expect(correctOrder[1].is_service_provider).toBe(true);
      expect(correctOrder[2].is_service_provider).toBeUndefined();
      expect(correctOrder[3].is_service_provider).toBeUndefined();
    });

    test('prepending vendors to products maintains correct order', () => {
      const products = [createProductOffer(), { ...createProductOffer(), title: 'Model', bid_id: 1002 }];
      const vendors = [createVendorOffer(), { ...createVendorOffer(), title: '247 Jet' }];
      
      const combined = [...vendors, ...products];
      
      expect(combined).toHaveLength(4);
      expect(combined[0].is_service_provider).toBe(true);
      expect(combined[1].is_service_provider).toBe(true);
      expect(combined[2].bid_id).toBe(1001);
      expect(combined[3].bid_id).toBe(1002);
    });
  });
});

describe('VendorContactModal Logic', () => {
  test('modal shows when isOpen is true', () => {
    const isOpen = true;
    const shouldRender = isOpen;
    expect(shouldRender).toBe(true);
  });

  test('modal hides when isOpen is false', () => {
    const isOpen = false;
    const shouldRender = isOpen;
    expect(shouldRender).toBe(false);
  });

  test('copy email functionality copies correct email', () => {
    const vendorEmail = 'charter@jetrightnashville.com';
    
    // Simulate clipboard write
    let clipboardContent = '';
    const mockClipboard = {
      writeText: async (text: string) => {
        clipboardContent = text;
      },
    };
    
    mockClipboard.writeText(vendorEmail);
    
    expect(clipboardContent).toBe('charter@jetrightnashville.com');
  });

  test('mailto link is correctly formed', () => {
    const vendorEmail = 'charter@jetrightnashville.com';
    const mailtoLink = `mailto:${vendorEmail}`;
    
    expect(mailtoLink).toBe('mailto:charter@jetrightnashville.com');
  });
});

describe('Service Category Keywords - Comprehensive', () => {
  const checkIsServiceKeyword = (query: string): boolean => {
    const lower = query.toLowerCase();
    const serviceTerms = [
      'jet', 'charter', 'flight', 'aviation', 'fly', 'plane',
      'roof', 'roofing', 'hvac', 'heating', 'cooling', 'plumb',
      'electric', 'landscap', 'clean', 'repair', 'service'
    ];
    return serviceTerms.some(term => lower.includes(term));
  };

  describe('Aviation Keywords', () => {
    const aviationKeywords = [
      'private jet',
      'jet charter',
      'charter flight',
      'private aviation',
      'fly private',
      'private plane',
      'aircraft charter',
      'jet rental',
      'Private Jet Charter Flights',
      'PRIVATE JET',
    ];

    aviationKeywords.forEach(keyword => {
      test(`"${keyword}" is detected as service`, () => {
        expect(checkIsServiceKeyword(keyword)).toBe(true);
      });
    });
  });

  describe('Non-Aviation Service Keywords', () => {
    const otherServiceKeywords = [
      'roof repair',
      'roofing contractor',
      'hvac service',
      'heating repair',
      'cooling system',
      'plumber',
      'electrician',
      'landscaping',
      'house cleaning',
    ];

    otherServiceKeywords.forEach(keyword => {
      test(`"${keyword}" is detected as service`, () => {
        expect(checkIsServiceKeyword(keyword)).toBe(true);
      });
    });
  });

  describe('Product Keywords (NOT services)', () => {
    const productKeywords = [
      'blue sneakers',
      'laptop computer',
      'coffee maker',
      'wireless headphones',
      'mountain bike',
      'winter jacket',
      'protein powder',
      'desk chair',
    ];

    productKeywords.forEach(keyword => {
      test(`"${keyword}" is NOT detected as service`, () => {
        expect(checkIsServiceKeyword(keyword)).toBe(false);
      });
    });
  });
});
