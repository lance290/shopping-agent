import { readFileSync } from 'fs';
import { join } from 'path';
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

describe('LoginPage - inputs not disabled/inactive (bug #122)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('phone input is enabled and interactive when not loading', async () => {
    render(<LoginPage />);

    const phoneInput = await screen.findByLabelText(/phone number/i);
    // Must not be disabled — a disabled input renders with grayed-out text
    // that looks "inactive" even when the user has typed into it
    expect(phoneInput).not.toBeDisabled();
    expect(phoneInput.className).not.toMatch(/opacity-\d/);
  });

  it('phone input text remains dark after user types', async () => {
    render(<LoginPage />);

    const phoneInput = await screen.findByLabelText(/phone number/i);
    fireEvent.change(phoneInput, { target: { value: '+15555555555' } });

    // After typing, the input must still carry text-gray-900 so typed characters
    // appear dark (not the light body color rgb(232,234,237)) — see bug #122
    expect(phoneInput.className).toContain('text-gray-900');
    expect(phoneInput.className).not.toMatch(/opacity-\d/);
  });

  it('OTP code input is enabled and interactive when not loading', async () => {
    render(<LoginPage />);

    const phoneInput = await screen.findByLabelText(/phone number/i);
    fireEvent.change(phoneInput, { target: { value: '+15555555555' } });

    await act(async () => {
      fireEvent.submit(phoneInput.closest('form')!);
    });

    const codeInput = await screen.findByLabelText(/verification code/i);
    expect(codeInput).not.toBeDisabled();
    expect(codeInput.className).not.toMatch(/opacity-\d/);
  });

  it('OTP code input text remains dark after user types digits', async () => {
    render(<LoginPage />);

    const phoneInput = await screen.findByLabelText(/phone number/i);
    fireEvent.change(phoneInput, { target: { value: '+15555555555' } });

    await act(async () => {
      fireEvent.submit(phoneInput.closest('form')!);
    });

    const codeInput = await screen.findByLabelText(/verification code/i);
    fireEvent.change(codeInput, { target: { value: '123456' } });

    // Typing digits must not change text styling to something that looks inactive
    expect(codeInput.className).toContain('text-gray-900');
    expect(codeInput.className).not.toMatch(/opacity-\d/);
  });

  it('globals.css includes -webkit-autofill override to prevent iOS from graying typed text', () => {
    const css = readFileSync(
      join(process.cwd(), 'app/globals.css'),
      'utf-8'
    );
    // The fix for bug #122: iOS WebKit autofill overrides the input text color
    // via -webkit-text-fill-color, making typed text appear inactive/grayed-out.
    expect(css).toContain('input:-webkit-autofill');
    expect(css).toContain('-webkit-text-fill-color: currentColor');
  });
});

describe('LoginPage - OTP text color on Chrome desktop (bug #126)', () => {
  it('globals.css applies -webkit-text-fill-color to all inputs to prevent Chrome from lightening typed text', () => {
    const css = readFileSync(
      join(process.cwd(), 'app/globals.css'),
      'utf-8'
    );
    // Bug #126: Chrome on Mac can override input text rendering via -webkit-text-fill-color,
    // making typed OTP digits appear lighter than the text-gray-900 color class specifies.
    // The fix adds a base rule for all inputs so Chrome always uses our explicit color value.
    expect(css).toMatch(/input\s*\{[^}]*-webkit-text-fill-color:\s*currentColor/);
  });

  it('OTP code input has dark text color class that currentColor will resolve to', async () => {
    render(<LoginPage />);

    const phoneInput = await screen.findByLabelText(/phone number/i);
    fireEvent.change(phoneInput, { target: { value: '+15555555555' } });

    await act(async () => {
      fireEvent.submit(phoneInput.closest('form')!);
    });

    const codeInput = await screen.findByLabelText(/verification code/i);
    // text-gray-900 resolves to #111827 — the -webkit-text-fill-color: currentColor
    // rule in globals.css ensures Chrome renders typed text using this dark color
    expect(codeInput.className).toContain('text-gray-900');
  });
});
