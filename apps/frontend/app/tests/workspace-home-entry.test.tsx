import type { AnchorHTMLAttributes } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { useShoppingStore } from '../store';

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('../utils/api', () => ({
  fetchRowsFromDb: vi.fn().mockResolvedValue([]),
  fetchProjectsFromDb: vi.fn().mockResolvedValue([]),
  fetchSingleRowFromDb: vi.fn().mockResolvedValue(null),
  saveChatHistory: vi.fn().mockResolvedValue(undefined),
  createProjectInDb: vi.fn().mockResolvedValue({ id: 99, title: 'Test Project', created_at: '', updated_at: '' }),
  duplicateProjectInDb: vi.fn().mockResolvedValue(null),
}));

vi.mock('../utils/auth', () => ({
  getMe: vi.fn().mockResolvedValue({ authenticated: false }),
  logout: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../utils/anonymous-session', () => ({
  getAnonymousSessionId: vi.fn().mockReturnValue('anon-test-session'),
}));

import Chat from '../components/Chat';
import ChatMessages from '../components/ChatMessages';
import { AppView } from '../components/sdui/AppView';

function resetStore() {
  useShoppingStore.setState({
    currentQuery: '',
    activeRowId: null,
    targetProjectId: null,
    newRowAggressiveness: 50,
    rows: [],
    projects: [],
    rowResults: {},
    rowProviderStatuses: {},
    rowSearchErrors: {},
    rowOfferSort: {},
    moreResultsIncoming: {},
    streamingRowIds: {},
    isSearching: false,
    cardClickQuery: null,
    selectedProviders: { amazon: true, ebay: true, serpapi: true, vendor_directory: true },
    isSidebarOpen: false,
    isReportBugModalOpen: false,
    pendingRowDelete: null,
    expandedRowId: null,
    sduiFallbackCount: 0,
  });
}

describe('Workspace home entry UX', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    resetStore();
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1280,
    });
  });

  test('ChatMessages renders starter prompts and forwards prompt clicks', () => {
    const onPromptSelect = vi.fn();

    render(
      <ChatMessages
        messages={[]}
        isLoading={false}
        promptSuggestions={['Find the best carry-on under $300']}
        onPromptSelect={onPromptSelect}
      />
    );

    expect(screen.getByText('Start with a sentence.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Find the best carry-on under $300' }));
    expect(onPromptSelect).toHaveBeenCalledWith('Find the best carry-on under $300');
  });

  test('AppView shows the desktop hero for anonymous users and routes CTA into store intent', async () => {
    render(
      <AppView>
        <div>Chat Pane</div>
      </AppView>
    );

    await waitFor(() => {
      expect(screen.getByText('Tell the chat what to buy. It does the legwork.')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Ask chat now/i }));

    expect(useShoppingStore.getState().cardClickQuery).toBe('Find the best carry-on under $300');
  });

  test('hero prompt handoff triggers chat submission through the shared store bridge', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      body: undefined,
      text: async () => 'Assistant reply',
    });
    vi.stubGlobal('fetch', fetchMock);

    render(
      <AppView>
        <Chat />
      </AppView>
    );

    await waitFor(() => {
      expect(screen.getByText('Tell the chat what to buy. It does the legwork.')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Ask chat now/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/chat',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    const [, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    const payload = JSON.parse(String(requestInit.body));
    expect(payload.messages[0].content).toBe('Find the best carry-on under $300');
    expect(payload.activeRowId).toBeNull();
  });

  test('home state shows customer-safe project education instead of internal notes', async () => {
    render(
      <AppView>
        <div>Chat Pane</div>
      </AppView>
    );

    await waitFor(() => {
      expect(screen.getByText(/Start with a real project/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Zac's Birthday/i)).toBeInTheDocument();
    expect(screen.getByText(/Vegas Trip/i)).toBeInTheDocument();
    expect(screen.getByText(/Kitchen Remodel/i)).toBeInTheDocument();

    expect(screen.queryByText(/What the home screen should communicate/i)).not.toBeInTheDocument();
  });

  test('home state shows customer-facing sidebar instead of internal strategy copy', async () => {
    render(
      <AppView>
        <div>Chat Pane</div>
      </AppView>
    );

    await waitFor(() => {
      expect(screen.getByText(/Why people use BuyAnything/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Ask once, compare everywhere/i)).toBeInTheDocument();
    expect(screen.getByText(/Keep everything organized/i)).toBeInTheDocument();
    expect(screen.getByText(/Share before you decide/i)).toBeInTheDocument();
    expect(screen.getByText(/Save your favorites as you go/i)).toBeInTheDocument();

    expect(screen.queryByText(/Why this feels different/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Intent-first/i)).not.toBeInTheDocument();
  });

  test('project education cards route prompts into chat via store', async () => {
    render(
      <AppView>
        <div>Chat Pane</div>
      </AppView>
    );

    await waitFor(() => {
      expect(screen.getByText(/Zac's Birthday/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Zac's Birthday/i).closest('button')!);

    await waitFor(() => {
      const query = useShoppingStore.getState().cardClickQuery;
      expect(query).toBeTruthy();
      expect(query!).toContain('birthday party');
    });
  });
});
