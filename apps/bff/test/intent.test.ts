import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { extractSearchIntent } from '../src/intent';

describe('extractSearchIntent (heuristic fallback)', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env = { ...originalEnv };
    delete process.env.GOOGLE_GENERATIVE_AI_API_KEY;
  });

  afterEach(() => {
    process.env = { ...originalEnv };
  });

  it('builds intent with parsed price constraints', async () => {
    const result = await extractSearchIntent({
      displayQuery: 'red running shoes under $80',
      rowTitle: 'running shoes',
      projectTitle: null,
      choiceAnswersJson: null,
      requestSpecConstraintsJson: JSON.stringify({ color: 'red' }),
    });

    expect(result.source).toBe('heuristic');
    expect(result.search_intent.product_category).toBe('red_running_shoes');
    expect(result.search_intent.min_price).toBeNull();
    expect(result.search_intent.max_price).toBe(80);
    expect(result.search_intent.features.color).toBe('red');
    expect(result.search_intent.keywords).toContain('running');
  });

  it('prefers choice answers for price over text', async () => {
    const result = await extractSearchIntent({
      displayQuery: 'standing desk under $600',
      rowTitle: 'standing desk',
      projectTitle: null,
      choiceAnswersJson: JSON.stringify({ min_price: 200, max_price: 450, finish: 'walnut' }),
      requestSpecConstraintsJson: JSON.stringify({ brand: 'uplift' }),
    });

    expect(result.search_intent.min_price).toBe(200);
    expect(result.search_intent.max_price).toBe(450);
    expect(result.search_intent.features.finish).toBe('walnut');
    expect(result.search_intent.features.brand).toBe('uplift');
  });

  it('excludes min/max from feature map', async () => {
    const result = await extractSearchIntent({
      displayQuery: 'coffee grinder',
      rowTitle: 'coffee grinder',
      projectTitle: null,
      choiceAnswersJson: JSON.stringify({ min_price: 50, max_price: 120, burrs: 'steel' }),
      requestSpecConstraintsJson: null,
    });

    expect(result.search_intent.features.min_price).toBeUndefined();
    expect(result.search_intent.features.max_price).toBeUndefined();
    expect(result.search_intent.features.burrs).toBe('steel');
  });
});
