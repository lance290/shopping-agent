import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import ReportBugModal from './ReportBugModal';
import { useShoppingStore } from '../store';

// Mock the store
const mockClose = vi.fn();
vi.mock('../store', () => ({
  useShoppingStore: vi.fn(),
}));

// Mock the API
vi.mock('../utils/api', () => ({
  submitBugReport: vi.fn(),
}));

// Mock diagnostics
vi.mock('../utils/diagnostics', () => ({
  getDiagnostics: vi.fn(() => ({})),
  redactDiagnostics: vi.fn((d) => d),
  addBreadcrumb: vi.fn(),
}));

describe('ReportBugModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useShoppingStore as any).mockImplementation((selector: any) => {
      const state = {
        isReportBugModalOpen: true,
        setReportBugModalOpen: mockClose,
      };
      return selector(state);
    });
  });

  it('uses ink colors for text on white background', () => {
    const { container } = render(<ReportBugModal />);

    // Check that the modal uses bg-white
    const modalContent = container.querySelector('.bg-white');
    expect(modalContent).toBeInTheDocument();

    // Check that labels use text-ink (dark text on light background)
    const labels = container.querySelectorAll('label');
    let hasInkText = false;
    labels.forEach(label => {
      if (label.className.includes('text-ink')) {
        hasInkText = true;
      }
    });
    expect(hasInkText).toBe(true);
  });

  it('has readable form field text colors', () => {
    render(<ReportBugModal />);

    // The "What happened?" label should be visible
    expect(screen.getByText(/What happened\?/)).toBeInTheDocument();

    // Check that the textarea has proper text color (text-ink instead of text-gray-900)
    const textarea = screen.getByPlaceholderText(/Describe the issue/);
    expect(textarea.className).toContain('text-ink');
  });

  it('has readable placeholder text colors', () => {
    render(<ReportBugModal />);

    const textarea = screen.getByPlaceholderText(/Describe the issue/);
    // Check that placeholder color is ink-muted (not gray-400)
    expect(textarea.className).toContain('placeholder:text-ink-muted');
  });
});
