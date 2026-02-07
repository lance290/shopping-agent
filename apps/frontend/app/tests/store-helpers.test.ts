import { describe, test, expect } from 'vitest';
import { mapBidToOffer, parseChoiceFactors, parseChoiceAnswers } from '../store';
import type { Bid, Row } from '../store';

describe('mapBidToOffer', () => {
  test('maps basic bid to offer', () => {
    const bid: Bid = {
      id: 1, price: 29.99, currency: 'USD',
      item_title: 'Widget', item_url: 'https://example.com/widget',
      image_url: 'https://img.com/w.jpg', source: 'amazon',
      is_selected: false,
    };

    const offer = mapBidToOffer(bid);

    expect(offer.title).toBe('Widget');
    expect(offer.price).toBe(29.99);
    expect(offer.currency).toBe('USD');
    expect(offer.url).toBe('https://example.com/widget');
    expect(offer.image_url).toBe('https://img.com/w.jpg');
    expect(offer.source).toBe('amazon');
    expect(offer.bid_id).toBe(1);
    expect(offer.is_selected).toBe(false);
    expect(offer.merchant).toBe('Unknown');
  });

  test('uses seller name as merchant', () => {
    const bid: Bid = {
      id: 2, price: 10, currency: 'USD',
      item_title: 'Gadget', item_url: 'https://store.com',
      image_url: null, source: 'google',
      is_selected: true,
      seller: { name: 'Best Store', domain: 'store.com' },
    };

    const offer = mapBidToOffer(bid);
    expect(offer.merchant).toBe('Best Store');
    expect(offer.merchant_domain).toBe('store.com');
    expect(offer.is_selected).toBe(true);
  });

  test('extracts contact name from title pattern', () => {
    const bid: Bid = {
      id: 3, price: 5000, currency: 'USD',
      item_title: 'JetRight (Contact: John Smith)',
      item_url: 'mailto:john@jetright.com',
      image_url: null, source: 'vendor',
      is_selected: false,
    };

    const offer = mapBidToOffer(bid);
    expect(offer.title).toBe('JetRight');
    expect(offer.vendor_name).toBe('John Smith');
    expect(offer.vendor_email).toBe('john@jetright.com');
  });

  test('prefers explicit contact_email over mailto URL', () => {
    const bid: Bid = {
      id: 4, price: 100, currency: 'USD',
      item_title: 'Service Co', item_url: 'mailto:old@co.com',
      image_url: null, source: 'vendor',
      is_selected: false,
      contact_email: 'new@co.com',
    };

    const offer = mapBidToOffer(bid);
    expect(offer.vendor_email).toBe('new@co.com');
  });

  test('prefers explicit contact_name over parsed name', () => {
    const bid: Bid = {
      id: 5, price: 100, currency: 'USD',
      item_title: 'Vendor (Contact: Parsed Name)',
      item_url: null, image_url: null, source: 'vendor',
      is_selected: false,
      contact_name: 'Explicit Name',
    };

    const offer = mapBidToOffer(bid);
    expect(offer.vendor_name).toBe('Explicit Name');
  });

  test('sets is_service_provider correctly', () => {
    const bid: Bid = {
      id: 6, price: 0, currency: 'USD',
      item_title: 'Charter Co', item_url: null,
      image_url: null, source: 'vendor',
      is_selected: false,
      is_service_provider: true,
    };

    const offer = mapBidToOffer(bid);
    expect(offer.is_service_provider).toBe(true);
  });

  test('handles null item_url', () => {
    const bid: Bid = {
      id: 7, price: 50, currency: 'USD',
      item_title: 'No URL Item', item_url: null,
      image_url: null, source: 'test',
      is_selected: false,
    };

    const offer = mapBidToOffer(bid);
    expect(offer.url).toBe('#');
    expect(offer.click_url).toBe('/api/clickout?url=');
  });

  test('generates click_url from item_url', () => {
    const bid: Bid = {
      id: 8, price: 25, currency: 'USD',
      item_title: 'Item', item_url: 'https://shop.com/item',
      image_url: null, source: 'test',
      is_selected: false,
    };

    const offer = mapBidToOffer(bid);
    expect(offer.click_url).toBe('/api/clickout?url=https%3A%2F%2Fshop.com%2Fitem');
  });
});

describe('parseChoiceFactors', () => {
  test('parses array of factors', () => {
    const row: Row = {
      id: 1, title: 'test', status: 'sourcing', budget_max: null, currency: 'USD',
      choice_factors: JSON.stringify([
        { name: 'size', label: 'Size', type: 'select', options: ['S', 'M', 'L'], required: false },
      ]),
    };

    const factors = parseChoiceFactors(row);
    expect(factors).toHaveLength(1);
    expect(factors[0].name).toBe('size');
  });

  test('converts object format to array', () => {
    const row: Row = {
      id: 1, title: 'test', status: 'sourcing', budget_max: null, currency: 'USD',
      choice_factors: JSON.stringify({
        size: { label: 'Size', type: 'select' },
        color: { label: 'Color', type: 'text' },
      }),
    };

    const factors = parseChoiceFactors(row);
    expect(factors).toHaveLength(2);
    expect(factors[0].name).toBe('size');
    expect(factors[1].name).toBe('color');
  });

  test('returns empty array for null', () => {
    const row: Row = {
      id: 1, title: 'test', status: 'sourcing', budget_max: null, currency: 'USD',
    };
    expect(parseChoiceFactors(row)).toEqual([]);
  });

  test('returns empty array for invalid JSON', () => {
    const row: Row = {
      id: 1, title: 'test', status: 'sourcing', budget_max: null, currency: 'USD',
      choice_factors: 'not json',
    };
    expect(parseChoiceFactors(row)).toEqual([]);
  });

  test('returns empty array for non-object/non-array JSON', () => {
    const row: Row = {
      id: 1, title: 'test', status: 'sourcing', budget_max: null, currency: 'USD',
      choice_factors: JSON.stringify('just a string'),
    };
    expect(parseChoiceFactors(row)).toEqual([]);
  });
});

describe('parseChoiceAnswers', () => {
  test('parses valid JSON object', () => {
    const row: Row = {
      id: 1, title: 'test', status: 'sourcing', budget_max: null, currency: 'USD',
      choice_answers: JSON.stringify({ size: 'M', color: 'blue', min_price: 50 }),
    };

    const answers = parseChoiceAnswers(row);
    expect(answers.size).toBe('M');
    expect(answers.min_price).toBe(50);
  });

  test('returns empty object for null', () => {
    const row: Row = {
      id: 1, title: 'test', status: 'sourcing', budget_max: null, currency: 'USD',
    };
    expect(parseChoiceAnswers(row)).toEqual({});
  });

  test('returns empty object for invalid JSON', () => {
    const row: Row = {
      id: 1, title: 'test', status: 'sourcing', budget_max: null, currency: 'USD',
      choice_answers: '{broken',
    };
    expect(parseChoiceAnswers(row)).toEqual({});
  });
});
