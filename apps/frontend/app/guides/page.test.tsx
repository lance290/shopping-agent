import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import GuidesIndexPage from './page';

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) =>
    React.createElement('a', { href, ...props }, children),
}));

describe('GuidesIndexPage', () => {
  it('renders guide cards that link to guide slugs', () => {
    render(<GuidesIndexPage />);

    expect(screen.getByText('Guides')).toBeInTheDocument();

    const aviation = screen.getByRole('link', {
      name: /private aviation: charter vs\. fractional vs\. jet card/i,
    });
    expect(aviation).toHaveAttribute('href', '/guides/private-aviation');

    const menswear = screen.getByRole('link', {
      name: /sourcing bespoke menswear in 2025/i,
    });
    expect(menswear).toHaveAttribute('href', '/guides/bespoke-menswear');

    const relocation = screen.getByRole('link', {
      name: /executive relocation: vendor vetting checklist/i,
    });
    expect(relocation).toHaveAttribute('href', '/guides/executive-relocation');
  });
});
