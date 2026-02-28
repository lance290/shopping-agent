'use client';

import { useEffect, useRef, useState } from 'react';
import { Plus, ShoppingBag, Bug, FolderPlus, Trash2, Share2, Store } from 'lucide-react';
import { useShoppingStore, Project, Row } from '../store';
import { createRowInDb, createProjectInDb, deleteProjectFromDb } from '../utils/api';
import RowStrip from './RowStrip';
import { Button } from '../../components/ui/Button';
import { cn } from '../../utils/cn';
import { TileDetailPanel } from './TileDetailPanel';

export default function ProcurementBoard() {
  const rows = useShoppingStore(state => state.rows);
  const projects = useShoppingStore(state => state.projects);
  const activeRowId = useShoppingStore(state => state.activeRowId);
  const rowResults = useShoppingStore(state => state.rowResults);
  const targetProjectId = useShoppingStore(state => state.targetProjectId);
  const setTargetProjectId = useShoppingStore(state => state.setTargetProjectId);
  const setActiveRowId = useShoppingStore(state => state.setActiveRowId);
  const addRow = useShoppingStore(state => state.addRow);
  const addProject = useShoppingStore(state => state.addProject);
  const removeProject = useShoppingStore(state => state.removeProject);
  const pendingRowDelete = useShoppingStore(state => state.pendingRowDelete);
  const undoDeleteRow = useShoppingStore(state => state.undoDeleteRow);
  const setReportBugModalOpen = useShoppingStore(state => state.setReportBugModalOpen);
  const [toast, setToast] = useState<{ message: string; tone?: 'success' | 'error' } | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  const showToast = (message: string, tone: 'success' | 'error' = 'success') => {
    setToast({ message, tone });
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
    }
    toastTimerRef.current = setTimeout(() => setToast(null), 2400);
  };

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
    };
  }, []);

  // Auto-scroll to center the selected row when activeRowId changes
  useEffect(() => {
    if (activeRowId && scrollContainerRef.current) {
      // Find the row element by its data attribute
      const rowElement = scrollContainerRef.current.querySelector(`[data-row-id="${activeRowId}"]`);
      if (rowElement) {
        // Scroll the row into view, centering it in the viewport
        rowElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeRowId]);

  const handleCreateProject = async () => {
    const title = window.prompt('Enter project name:');
    if (!title || !title.trim()) return;

    const newProject = await createProjectInDb(title.trim());
    if (newProject) {
      addProject(newProject);
      setTargetProjectId(newProject.id);
      showToast(`Project "${newProject.title}" created`);
    } else {
      showToast('Failed to create project', 'error');
    }
  };

  const handleDeleteProject = async (id: number, title: string) => {
    if (!window.confirm(`Delete project "${title}"? Associated requests will be ungrouped.`)) return;
    
    const success = await deleteProjectFromDb(id);
    if (success) {
      removeProject(id);
      showToast(`Project "${title}" deleted`);
      // Optionally refresh rows to reflect ungrouping? The store might need a refresh or we optimistically update rows?
      // For now, let's rely on eventual consistency or manual refresh, or we could update local rows.
      // Ideally we should refetch rows or update store.
      // Let's implement optimistic update for rows:
      // const updatedRows = rows.map(r => r.project_id === id ? { ...r, project_id: null } : r);
      // setRows(updatedRows); 
      // But we don't have setRows exposed conveniently here without prop drilling or re-fetching.
      // Re-fetching is safer.
      // We can rely on the user refreshing or the next poll.
    } else {
      showToast('Failed to delete project', 'error');
    }
  };

  const handleSelectProject = (projectId: number) => {
    setTargetProjectId(projectId);

    const project = projects.find(p => p.id === projectId);
    showToast(`Selected "${project?.title || 'project'}"`);
  };

  const handleAddRequestToProject = (projectId: number) => {
    // Set the target project for new rows.
    setTargetProjectId(projectId);

    // Clear the active row so chat creates a new request rather than refining the current row.
    setActiveRowId(null);

    // Just focus the chat input - the chat will create the row when user types
    const chatInput = document.querySelector('input[placeholder*="looking for"], input[placeholder*="Refine"]') as HTMLInputElement | null;
    chatInput?.focus();

    const project = projects.find(p => p.id === projectId);
    showToast(`Adding to "${project?.title || 'project'}"...`);
  };

  const handleNewRequest = () => {
    setTargetProjectId(null);
    setActiveRowId(null);

    const chatInput = document.querySelector('input[placeholder*="looking for"], input[placeholder*="Refine"]') as HTMLInputElement | null;
    chatInput?.focus();
    showToast('Tell us what you are buying to start a new request.');
  };

  const handleShareBoard = async () => {
    if (rows.length === 0) {
      showToast('No requests to share', 'error');
      return;
    }

    try {
      // Create a URL with all search queries as parameters
      const url = new URL(window.location.origin);

      // Add all row titles as 'q' parameters (supporting multiple values)
      rows.forEach(row => {
        url.searchParams.append('q', row.title);
      });

      await navigator.clipboard.writeText(url.toString());
      showToast(`Board link copied! (${rows.length} request${rows.length !== 1 ? 's' : ''})`);
    } catch (err) {
      // AbortError: user dismissed the clipboard permission prompt — ignore silently
      if (err instanceof DOMException && err.name === 'AbortError') return;
      console.error('Failed to copy board link:', err);
      showToast('Failed to copy link', 'error');
    }
  };

  // Grouping logic with sorting by last_engaged_at (most recent first)
  const groupedRows: Record<number, Row[]> = {};
  const ungroupedRows: Row[] = [];

  rows.forEach(row => {
    if (row.project_id) {
      if (!groupedRows[row.project_id]) {
        groupedRows[row.project_id] = [];
      }
      groupedRows[row.project_id].push(row);
    } else {
      ungroupedRows.push(row);
    }
  });

  // Sort each group by last_engaged_at (most recent first)
  Object.keys(groupedRows).forEach(projectId => {
    groupedRows[Number(projectId)].sort((a, b) => {
      const aTime = a.last_engaged_at || 0;
      const bTime = b.last_engaged_at || 0;
      return bTime - aTime;
    });
  });

  // Sort ungrouped rows by last_engaged_at (most recent first)
  ungroupedRows.sort((a, b) => {
    const aTime = a.last_engaged_at || 0;
    const bTime = b.last_engaged_at || 0;
    return bTime - aTime;
  });

  return (
    <div className="flex-1 bg-transparent h-full flex flex-col overflow-hidden relative">
      {/* Header / Disclosure */}
      <div className="h-20 px-8 bg-warm-light border-b border-warm-grey/70 flex justify-between items-center z-10 shrink-0">
        <div className="flex items-center gap-6">
          <div>
            <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-onyx-muted/80">
              Board
            </div>
            <div className="text-xl font-medium text-onyx">Requests</div>
          </div>
          <div className="text-xs text-onyx-muted max-w-[220px]">
            The agent may earn a commission from purchases.
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-[10px] font-medium text-onyx uppercase tracking-[0.16em]">
            {projects.length} project{projects.length !== 1 ? 's' : ''}, {rows.length} active request{rows.length !== 1 ? 's' : ''}
          </div>
          <a href="/merchants/register">
            <Button
              variant="secondary"
              size="sm"
              className="flex items-center gap-2"
            >
              <Store size={16} />
              Become a Seller
            </Button>
          </a>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setReportBugModalOpen(true)}
            className="flex items-center gap-2"
          >
            <Bug size={16} />
            Report Bug
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleShareBoard}
            className="flex items-center gap-2"
          >
            <Share2 size={16} />
            Share Board
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleCreateProject}
            className="flex items-center gap-2"
          >
            <FolderPlus size={16} />
            New Project
          </Button>
          <Button
            size="sm"
            onClick={handleNewRequest}
            className="flex items-center gap-2"
          >
            <Plus size={16} />
            New Request
          </Button>
        </div>
      </div>
      
      {/* Scrollable Content */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-8 space-y-8">
        {rows.length === 0 && projects.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-onyx-muted">
            <div className="w-16 h-16 mb-5 rounded-full bg-white border border-warm-grey flex items-center justify-center">
              <ShoppingBag className="w-7 h-7 text-onyx/50" />
            </div>
            <h3 className="text-xl font-semibold text-onyx mb-2">Your Board is Empty</h3>
            <p className="text-sm max-w-sm text-center">
              Start a conversation with the agent to begin finding products.
            </p>
          </div>
        ) : (
          <>
            {/* Projects */}
            {projects.map(project => (
              <div key={project.id} className="space-y-4">
                <div className="flex items-center gap-3 pb-2 border-b border-warm-grey/50">
                  <button
                    type="button"
                    onClick={() => handleSelectProject(project.id)}
                    className={cn(
                      "flex items-center gap-2 text-onyx font-medium hover:text-agent-blurple",
                      targetProjectId === project.id ? "text-agent-blurple" : ""
                    )}
                  >
                    <FolderPlus size={18} className="text-agent-blurple" />
                    {project.title}
                  </button>
                  <div className="flex-1" />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleAddRequestToProject(project.id)}
                    className="h-7 text-xs text-onyx-muted hover:text-agent-blurple"
                  >
                    <Plus size={14} className="mr-1" />
                    Add Request
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteProject(project.id, project.title)}
                    className="h-7 w-7 p-0 text-onyx-muted hover:text-status-error"
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
                
                <div className="pl-6 border-l-2 border-warm-grey/30 space-y-6">
                  {(groupedRows[project.id] || []).length > 0 ? (
                    groupedRows[project.id].map(row => (
                      <RowStrip
                        key={row.id}
                        row={row}
                        offers={rowResults[row.id] || []}
                        isActive={row.id === activeRowId}
                        onSelect={() => setActiveRowId(row.id)}
                        onToast={showToast}
                      />
                    ))
                  ) : (
                    <div className="text-sm text-onyx-muted italic py-2">
                      No requests in this project yet.
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Ungrouped Rows */}
            {ungroupedRows.length > 0 && (
              <div className="space-y-6">
                {projects.length > 0 && (
                  <div className="text-xs font-medium text-onyx-muted uppercase tracking-wider pb-2 border-b border-warm-grey/50">
                    Other Requests
                  </div>
                )}
                {ungroupedRows.map(row => (
                  <RowStrip
                    key={row.id}
                    row={row}
                    offers={rowResults[row.id] || []}
                    isActive={row.id === activeRowId}
                    onSelect={() => setActiveRowId(row.id)}
                    onToast={showToast}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {toast && (
        <div className="absolute top-20 right-6 z-50">
          <div className={cn(
            "px-4 py-3 rounded-xl border text-sm font-medium flex items-center gap-2 bg-white shadow-[0_12px_24px_rgba(0,0,0,0.08)]",
            toast.tone === 'error'
              ? "border-status-error/40 text-status-error"
              : "border-status-success/40 text-status-success"
          )}>
            <span>{toast.message}</span>
          </div>
        </div>
      )}

      {pendingRowDelete && (
        <div className="absolute bottom-6 right-6 z-50 bg-white border border-warm-grey shadow-[0_16px_32px_rgba(0,0,0,0.1)] rounded-2xl px-6 py-4 w-[380px]">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="text-sm font-semibold text-onyx truncate">
                Archiving “{pendingRowDelete.row.title}”
              </div>
              <div className="text-xs text-onyx-muted mt-1">Undo available for a few seconds.</div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={undoDeleteRow}
            >
              Undo
            </Button>
          </div>
        </div>
      )}

      {/* Tile Detail Panel Overlay */}
      <TileDetailPanel />
    </div>
  );
}
