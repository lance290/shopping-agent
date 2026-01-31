import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import ProviderStatusBadge from './ProviderStatusBadge';
import { ProviderStatusSnapshot } from '../store';

describe('ProviderStatusBadge', () => {
  it('renders OK status correctly', () => {
    const status: ProviderStatusSnapshot = {
      provider_id: 'rainforest',
      status: 'ok',
      result_count: 5,
      latency_ms: 120
    };
    render(<ProviderStatusBadge status={status} />);
    
    expect(screen.getByText('Rainforest')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    const badge = screen.getByText('Rainforest').parentElement;
    expect(badge?.className).toContain('text-status-success');
  });

  it('renders Timeout status correctly', () => {
    const status: ProviderStatusSnapshot = {
      provider_id: 'google_cse',
      status: 'timeout',
      result_count: 0,
      latency_ms: 8000,
      message: 'Timed out'
    };
    render(<ProviderStatusBadge status={status} />);
    
    expect(screen.getByText('Google CSE')).toBeInTheDocument();
    const badge = screen.getByText('Google CSE').parentElement;
    expect(badge?.className).toContain('text-status-warning');
  });

  it('renders Error status correctly', () => {
    const status: ProviderStatusSnapshot = {
      provider_id: 'search_api',
      status: 'error',
      result_count: 0,
      message: 'Failed'
    };
    render(<ProviderStatusBadge status={status} />);
    
    expect(screen.getByText('Search API')).toBeInTheDocument();
    const badge = screen.getByText('Search API').parentElement;
    expect(badge?.className).toContain('text-status-error');
  });
});
