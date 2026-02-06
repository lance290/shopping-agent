/**
 * Tests for TileDetailPanel improvements (task-003).
 * Verifies: fallback message, accessibility attributes, keyboard navigation.
 */
import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const PANEL_PATH = path.resolve(__dirname, '../components/TileDetailPanel.tsx');
const panelSource = fs.readFileSync(PANEL_PATH, 'utf-8');

describe('TileDetailPanel Fallback Message (task-003)', () => {
  it('shows "Based on your search" instead of "Details unavailable"', () => {
    expect(panelSource).toContain('Based on your search');
    expect(panelSource).not.toContain('Details unavailable');
  });

  it('fallback has role="status" for screen readers', () => {
    expect(panelSource).toContain('role="status"');
  });
});

describe('TileDetailPanel Accessibility (task-003)', () => {
  it('panel has role="dialog" and aria-modal', () => {
    expect(panelSource).toContain('role="dialog"');
    expect(panelSource).toContain('aria-modal="true"');
  });

  it('panel has aria-labelledby pointing to panel-title', () => {
    expect(panelSource).toContain('aria-labelledby="panel-title"');
    expect(panelSource).toContain('id="panel-title"');
  });

  it('close button has aria-label', () => {
    expect(panelSource).toContain('aria-label="Close panel"');
  });

  it('Product Information section has aria-label and tabIndex', () => {
    expect(panelSource).toContain('aria-label="Product information"');
    // h4 for Product Information has tabIndex={0}
    const productInfoSection = panelSource.match(
      /aria-label="Product information"[\s\S]*?<\/section>/
    );
    expect(productInfoSection).not.toBeNull();
    expect(productInfoSection![0]).toContain('tabIndex={0}');
  });

  it('Matched features section has aria-label and tabIndex', () => {
    expect(panelSource).toContain('aria-label="Why this matches your search"');
    const matchSection = panelSource.match(
      /aria-label="Why this matches your search"[\s\S]*?<\/section>/
    );
    expect(matchSection).not.toBeNull();
    expect(matchSection![0]).toContain('tabIndex={0}');
  });

  it('Chat excerpts section has aria-label and tabIndex', () => {
    expect(panelSource).toContain('aria-label="Related conversation excerpts"');
    const chatSection = panelSource.match(
      /aria-label="Related conversation excerpts"[\s\S]*?<\/section>/
    );
    expect(chatSection).not.toBeNull();
    expect(chatSection![0]).toContain('tabIndex={0}');
  });

  it('Escape key handler is registered', () => {
    expect(panelSource).toContain("e.key === 'Escape'");
  });
});

describe('TileDetailPanel Structure (task-003)', () => {
  it('uses <section> elements for provenance areas', () => {
    const sectionCount = (panelSource.match(/<section /g) || []).length;
    expect(sectionCount).toBeGreaterThanOrEqual(3);
  });

  it('renders product info, matched features, and chat excerpts sections', () => {
    expect(panelSource).toContain('Product Information');
    expect(panelSource).toContain('Why this matches');
    expect(panelSource).toContain('From your conversation');
  });
});
