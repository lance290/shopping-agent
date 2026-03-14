import * as fs from 'fs';
import * as path from 'path';
import { describe, expect, test } from 'vitest';

const APP_ROOT = path.resolve(__dirname, '..');

function read(relativePath: string): string {
  return fs.readFileSync(path.join(APP_ROOT, relativePath), 'utf-8');
}

describe('Thank-you copy regressions', () => {
  test('main chat uses thank-you copy for the tip action', () => {
    const source = read('components/Chat.tsx');
    expect(source).toContain('title="Send a Thank-You"');
    expect(source).toContain("'Send a Thank-You'");
    expect(source).not.toContain("'Tip Jar'");
  });

  test('app view uses thank-you copy for the desktop tip action', () => {
    const source = read('components/sdui/AppView.tsx');
    expect(source).toContain('title="Send a Thank-You"');
    expect(source).toContain("'Send a Thank-You'");
    expect(source).not.toContain("'Tip Jar'");
  });

});
