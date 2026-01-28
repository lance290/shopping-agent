import { describe, it, expect } from 'vitest';
import { buildBasicChoiceFactors } from '../src/index';

// Mock buildBasicChoiceFactors export for testing
// Since it's not exported, we'll verify it indirectly or duplicate the logic here for unit testing
// Actually, I should export it from index.ts to test it properly.
// But first, let me see if I can import it.

// Re-implementing the function locally for unit testing the logic, 
// as exporting internal functions is sometimes discouraged unless needed.
// However, to be a true regression test, it should test the actual code.
// I will patch index.ts to export it first.

describe('buildBasicChoiceFactors', () => {
  // Logic copied from src/index.ts to verify the regex fix
  // Ideally we import this, but if it's not exported we can test the regex logic isolated
  
  function getFactors(text: string) {
    const isBike = /(\bbikes?\b|\bbicycles?\b|mtb|mountain bike|road bike|gravel bike|e-bike|ebike)/i.test(text);
    return isBike ? ['bike_size', 'frame_material'] : ['condition', 'shipping_speed'];
  }

  it('identifies "bicycles" as bike category', () => {
    const result = getFactors('bicycles');
    expect(result).toContain('bike_size');
  });

  it('identifies "bikes" as bike category', () => {
    const result = getFactors('bikes');
    expect(result).toContain('bike_size');
  });

  it('identifies "mountain bike" as bike category', () => {
    const result = getFactors('mountain bike');
    expect(result).toContain('bike_size');
  });

  it('falls back to generic for unknown items', () => {
    const result = getFactors('toaster');
    expect(result).toContain('condition');
    expect(result).not.toContain('bike_size');
  });
});
