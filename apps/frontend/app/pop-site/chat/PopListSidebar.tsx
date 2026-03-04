'use client';

import { useState } from 'react';
import Link from 'next/link';
import { DynamicRenderer } from '../../components/sdui/DynamicRenderer';

interface Deal {
  id: number;
  title: string;
  price: number;
  source: string;
  url: string;
  image_url: string | null;
  is_selected: boolean;
}

interface ListItem {
  id: number;
  title: string;
  status: string;
  deals?: Deal[];
  lowest_price?: number | null;
  deal_count?: number;
  ui_schema?: Record<string, unknown> | null;
}

interface PopListSidebarProps {
  listItems: ListItem[];
  isLoggedIn: boolean;
  projectId: number | null;
  projectTitle: string;
  allProjects: { id: number; title: string }[];
  expandedItemId: number | null;
  setExpandedItemId: (id: number | null) => void;
  editingId: number | null;
  editValue: string;
  setEditValue: (v: string) => void;
  editInputRef: React.RefObject<HTMLInputElement>;
  startEdit: (item: ListItem) => void;
  commitEdit: (item: ListItem) => void;
  setEditingId: (id: number | null) => void;
  handleSwitchProject: (id: number) => void;
  handleCreateProject: () => void;
  handleDuplicateProject: () => void;
  handleDeleteItem: (item: ListItem) => void;
  handleClaimDeal: (itemId: number, dealId: number) => void;
  sourceColor: (source: string) => string;
  sourceLabel: (source: string) => string;
}

export default function PopListSidebar({
  listItems,
  isLoggedIn,
  projectId,
  projectTitle,
  allProjects,
  expandedItemId,
  setExpandedItemId,
  editingId,
  editValue,
  setEditValue,
  editInputRef,
  startEdit,
  commitEdit,
  setEditingId,
  handleSwitchProject,
  handleCreateProject,
  handleDuplicateProject,
  handleDeleteItem,
  handleClaimDeal,
  sourceColor,
  sourceLabel,
}: PopListSidebarProps) {
  const [showProjectMenu, setShowProjectMenu] = useState(false);

  return (
    <div className="lg:w-96 border-t lg:border-t-0 lg:border-l border-gray-100 bg-gray-50/50 p-4 flex flex-col h-[calc(100vh-56px)]">
      <div className="flex items-center justify-between mb-3 relative flex-shrink-0">
        <button 
          onClick={() => isLoggedIn && setShowProjectMenu(!showProjectMenu)}
          className={`flex items-center gap-2 text-sm font-semibold text-gray-900 ${isLoggedIn ? 'hover:bg-gray-200 px-2 py-1 rounded -ml-2' : ''}`}
        >
          <span>🛒</span> {projectTitle}
          {isLoggedIn && (
            <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          )}
        </button>
        
        {showProjectMenu && isLoggedIn && (
          <div className="absolute top-full left-0 mt-1 w-48 bg-white rounded-xl shadow-lg border border-gray-100 py-1 z-50">
            <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wide border-b border-gray-100">
              Your Lists
            </div>
            {allProjects.map(p => (
              <button
                key={p.id}
                onClick={() => handleSwitchProject(p.id)}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center justify-between ${p.id === projectId ? 'text-green-700 font-medium bg-green-50/50' : 'text-gray-700'}`}
              >
                <span className="truncate">{p.title}</span>
                {p.id === projectId && <span className="text-green-500">✓</span>}
              </button>
            ))}
            <div className="border-t border-gray-100 mt-1">
              <button
                onClick={handleCreateProject}
                className="w-full text-left px-4 py-2 text-sm text-green-700 hover:bg-green-50 flex items-center gap-2 font-medium"
              >
                <span className="text-lg leading-none">+</span> New List
              </button>
            </div>
          </div>
        )}

        <div className="flex items-center gap-2">
          {isLoggedIn && projectId && (
            <button
              onClick={handleDuplicateProject}
              className="p-1.5 text-gray-400 hover:text-green-600 rounded hover:bg-green-50 transition-colors"
              title="Duplicate List"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          )}
          {projectId && (
            <Link
              href={`/pop-site/list/${projectId}`}
              className="text-xs text-green-600 hover:text-green-700 font-medium flex items-center gap-1"
            >
              View Full <span className="hidden sm:inline">List</span> →
            </Link>
          )}
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto -mx-4 px-4 pb-4">
        {listItems.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <span className="text-4xl block mb-3">🛒</span>
            <p className="text-sm">List is empty.</p>
            <p className="text-xs mt-1">Tell Pop what you need!</p>
          </div>
        ) : (
          <>
            <ul className="space-y-3">
              {listItems.map((item) => {
                const isExpanded = expandedItemId === item.id;
                const selectedDeal = item.deals?.find((d) => d.is_selected);
                const hasDealChoices = (item.deal_count ?? 0) > 0;

                return (
                  <li key={item.id} className="bg-white rounded-xl shadow-sm overflow-hidden">
                    {/* Item header */}
                    <div className="group flex items-center gap-2 px-3 py-2.5">
                      <button
                        className={`w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                          selectedDeal ? 'bg-green-500 border-green-500' : 'border-gray-300'
                        }`}
                        title={selectedDeal ? 'Deal picked' : 'No deal picked yet'}
                        onClick={() => hasDealChoices && setExpandedItemId(isExpanded ? null : item.id)}
                      >
                        {selectedDeal && (
                          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </button>

                      {editingId === item.id ? (
                        <input
                          ref={editInputRef}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onBlur={() => commitEdit(item)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') commitEdit(item);
                            if (e.key === 'Escape') setEditingId(null);
                          }}
                          className="flex-1 text-sm text-gray-900 border-b border-green-400 outline-none bg-transparent"
                        />
                      ) : (
                        <button
                          className="flex-1 text-left min-w-0"
                          onClick={() => hasDealChoices ? setExpandedItemId(isExpanded ? null : item.id) : startEdit(item)}
                        >
                          <span className="text-sm font-medium text-gray-900 truncate block">{item.title}</span>
                          {hasDealChoices && (
                            <span className="text-xs text-gray-500">
                              {item.deal_count} deal{item.deal_count !== 1 ? 's' : ''}
                              {item.lowest_price != null && ` from $${item.lowest_price.toFixed(2)}`}
                            </span>
                          )}
                          {!hasDealChoices && (
                            <span className="text-xs text-gray-400 italic">Searching for deals...</span>
                          )}
                        </button>
                      )}

                      <div className="flex items-center gap-1 flex-shrink-0">
                        {hasDealChoices && (
                          <button
                            onClick={() => setExpandedItemId(isExpanded ? null : item.id)}
                            className="p-1 text-gray-400 hover:text-green-600 transition-colors"
                            title="Show deals"
                          >
                            <svg className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteItem(item)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 text-gray-300 hover:text-red-400"
                          title="Remove item"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    </div>

                    {/* Expanded Content: SDUI + Legacy deal choices */}
                    {isExpanded && (
                      <div className="border-t border-gray-100 px-3 py-2 space-y-3 max-h-[400px] overflow-y-auto">
                        {item.ui_schema && (
                          <div className="mb-2">
                            <DynamicRenderer
                              schema={item.ui_schema}
                              fallbackTitle={item.title}
                              fallbackStatus={item.status}
                            />
                          </div>
                        )}

                        {item.deals && item.deals.length > 0 && (
                          <div className="space-y-2">
                            {item.deals.map((deal) => (
                              <button
                                key={deal.id}
                                onClick={() => handleClaimDeal(item.id, deal.id)}
                                className={`w-full flex items-center gap-2.5 p-2 rounded-lg text-left transition-colors ${
                                  deal.is_selected
                                    ? 'bg-green-50 ring-1 ring-green-300'
                                    : 'hover:bg-gray-50'
                                }`}
                              >
                                {deal.image_url ? (
                                  // eslint-disable-next-line @next/next/no-img-element
                                  <img
                                    src={deal.image_url}
                                    alt={deal.title}
                                    className="w-10 h-10 rounded-md object-cover flex-shrink-0 bg-gray-100"
                                  />
                                ) : (
                                  <div className="w-10 h-10 rounded-md bg-gray-100 flex-shrink-0 flex items-center justify-center">
                                    <svg className="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                    </svg>
                                  </div>
                                )}
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs text-gray-800 truncate">{deal.title}</p>
                                  <div className="flex items-center gap-1.5 mt-0.5">
                                    <span className="text-sm font-semibold text-gray-900">${deal.price.toFixed(2)}</span>
                                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${sourceColor(deal.source)}`}>
                                      {sourceLabel(deal.source)}
                                    </span>
                                  </div>
                                </div>
                                {deal.is_selected && (
                                  <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                  </svg>
                                )}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Selected deal summary (collapsed) */}
                    {!isExpanded && selectedDeal && (
                      <div className="border-t border-gray-100 px-3 py-1.5 flex items-center gap-2">
                        <span className="text-xs text-green-700 font-medium">${selectedDeal.price.toFixed(2)}</span>
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${sourceColor(selectedDeal.source)}`}>
                          {sourceLabel(selectedDeal.source)}
                        </span>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
            {!isLoggedIn && (
              <p className="mt-3 text-xs text-gray-400 text-center">
                <Link href="/login" className="text-green-600 hover:underline">Sign in</Link> to save your list permanently
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
