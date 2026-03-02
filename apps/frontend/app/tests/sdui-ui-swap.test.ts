/**
 * Tests for Phase 3.3 UI swap — Board replaced by AppView.
 *
 * Verifies:
 * - page.tsx no longer imports ProcurementBoard
 * - page.tsx imports AppView from sdui
 * - (workspace)/app/page.tsx uses AppView
 * - WorkspaceView.tsx is no longer referenced by any page
 * - AppView renders Chat as children + vertical list
 */

import { describe, test, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const APP_DIR = path.resolve(__dirname, '..');

describe('Phase 3.3: Board replaced by AppView', () => {
  test('page.tsx does NOT import ProcurementBoard', () => {
    const content = fs.readFileSync(path.join(APP_DIR, 'page.tsx'), 'utf-8');
    expect(content).not.toContain('ProcurementBoard');
    expect(content).not.toContain("from './components/Board'");
  });

  test('page.tsx imports AppView from sdui', () => {
    const content = fs.readFileSync(path.join(APP_DIR, 'page.tsx'), 'utf-8');
    expect(content).toContain('AppView');
    expect(content).toContain("from './components/sdui'");
  });

  test('page.tsx renders AppView wrapping Chat', () => {
    const content = fs.readFileSync(path.join(APP_DIR, 'page.tsx'), 'utf-8');
    expect(content).toContain('<AppView>');
    expect(content).toContain('<Chat />');
    expect(content).toContain('</AppView>');
  });

  test('page.tsx has no drag handle code', () => {
    const content = fs.readFileSync(path.join(APP_DIR, 'page.tsx'), 'utf-8');
    expect(content).not.toContain('isDraggingRef');
    expect(content).not.toContain('col-resize');
    expect(content).not.toContain('chatWidthPx');
  });

  test('page.tsx has no mobile pane switching', () => {
    const content = fs.readFileSync(path.join(APP_DIR, 'page.tsx'), 'utf-8');
    expect(content).not.toContain('mobilePane');
    expect(content).not.toContain('setMobilePane');
    expect(content).not.toContain('isMobile');
  });

  test('workspace/app/page.tsx uses AppView, not WorkspaceView', () => {
    const content = fs.readFileSync(path.join(APP_DIR, '(workspace)', 'app', 'page.tsx'), 'utf-8');
    expect(content).toContain('AppView');
    expect(content).toContain('<Chat />');
    expect(content).not.toContain('WorkspaceView');
  });

  test('page.tsx preserves shared search link handler', () => {
    const content = fs.readFileSync(path.join(APP_DIR, 'page.tsx'), 'utf-8');
    expect(content).toContain('handleSharedSearch');
    expect(content).toContain("searchParams?.getAll('q')");
  });
});
