import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import LoginPage from './page';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock('../utils/auth', () => ({
  startAuth: vi.fn().mockResolvedValue(undefined),
  verifyAuth: vi.fn().mockResolvedValue(undefined),
}));

describe('LoginPage - OTP text color visibility (bug #112)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('card container has explicit dark text color to prevent inheritance from dark-themed body', async () => {
    const { container } = render(<LoginPage />);

    // The card should have bg-white AND text-gray-900 so text doesn't inherit
    // the light body color (text-onyx / #E8EAED) which would be white-on-white
    const card = container.querySelector('.bg-white');
    expect(card).toBeInTheDocument();
    expect(card?.className).toContain('text-gray-900');
  });

  it('phone input has explicit dark text color to prevent white-on-white on light background', async () => {
    render(<LoginPage />);

    const phoneInput = await screen.findByLabelText(/phone number/i);
    // Without text-gray-900, the input would inherit text-onyx (#E8EAED) from body
    // resulting in white text on white (bg-white) input
    expect(phoneInput.className).toContain('text-gray-900');
  });

  it('phone input has explicit placeholder color', async () => {
    render(<LoginPage />);

    const phoneInput = await screen.findByLabelText(/phone number/i);
    expect(phoneInput.className).toContain('placeholder:text-gray-400');
  });

  it('OTP verification code input has explicit dark text color to prevent white-on-white', async () => {
    render(<LoginPage />);

    // Advance to step 2: fill phone and submit
    const phoneInput = await screen.findByLabelText(/phone number/i);
    fireEvent.change(phoneInput, { target: { value: '+15555555555' } });

    await act(async () => {
      fireEvent.submit(phoneInput.closest('form')!);
    });

    const codeInput = await screen.findByLabelText(/verification code/i);
    // Without text-gray-900, typed OTP digits would be white on white background
    expect(codeInput.className).toContain('text-gray-900');
  });

  it('OTP verification code input has explicit placeholder color', async () => {
    render(<LoginPage />);

    const phoneInput = await screen.findByLabelText(/phone number/i);
    fireEvent.change(phoneInput, { target: { value: '+15555555555' } });

    await act(async () => {
      fireEvent.submit(phoneInput.closest('form')!);
    });

    const codeInput = await screen.findByLabelText(/verification code/i);
    expect(codeInput.className).toContain('placeholder:text-gray-400');
  });
});
