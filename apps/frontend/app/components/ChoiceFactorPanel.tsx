import { useState, useEffect, useRef } from 'react';
import { parseChoiceFactors, parseChoiceAnswers, useShoppingStore } from '../store';
import { saveChoiceAnswerToDb, fetchRowsFromDb, runSearchApi } from '../utils/api';
import { Loader2, Check, AlertCircle, ChevronLeft, RefreshCw, SlidersHorizontal } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { cn } from '../../utils/cn';

export default function ChoiceFactorPanel() {
  const { rows, activeRowId, updateRow, setRows, setRowResults, setIsSearching, isSidebarOpen, setSidebarOpen } = useShoppingStore();
  
  const row = rows.find(r => r.id === activeRowId);
  const factors = row ? parseChoiceFactors(row) : [];
  
  // Local state
  const [localAnswers, setLocalAnswers] = useState<Record<string, any>>({});
  const [savingFields, setSavingFields] = useState<Record<string, boolean>>({});
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pollCount, setPollCount] = useState(0);

  const prevRowIdRef = useRef<number | null>(null);

  // Sync local state when active row changes (ID based)
  useEffect(() => {
    const prevId = prevRowIdRef.current;
    const currId = row?.id || null;

    if (currId !== prevId) {
      if (row) {
        setLocalAnswers(parseChoiceAnswers(row));
      } else {
        setLocalAnswers({});
      }

      setPollCount(0);
      prevRowIdRef.current = currId;
    }
  }, [row?.id]);

  useEffect(() => {
    if (!row) return;

    if (row.id !== prevRowIdRef.current) return;

    const serverAnswers = parseChoiceAnswers(row);
    setLocalAnswers(prev => {
      const merged = { ...prev };
      Object.entries(serverAnswers).forEach(([k, v]) => {
        if (merged[k] === undefined || merged[k] === '') {
          merged[k] = v;
        }
      });
      return merged;
    });
  }, [row]);

  // Polling effect: If row exists but no factors, try to fetch fresh data a few times
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    
    if (isSidebarOpen && row && factors.length === 0 && pollCount < 5) {
      timeoutId = setTimeout(async () => {
        console.log(`[ChoiceFactorPanel] Polling for specs... attempt ${pollCount + 1}`);
        const freshRows = await fetchRowsFromDb();
        setRows(freshRows);
        setPollCount(prev => prev + 1);
      }, 2000); // Poll every 2s
    }

    return () => clearTimeout(timeoutId);
  }, [isSidebarOpen, row, factors.length, pollCount, setRows]);

  const handleManualRefresh = async () => {
    if (!row) return;
    setIsRefreshing(true);
    setPollCount(0); // Reset poll count to allow more auto-polls if needed
    try {
      // Ask backend (via BFF) to regenerate specs for this row.
      await fetch(`/api/rows?id=${row.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ regenerate_choice_factors: true }),
      });

      const freshRows = await fetchRowsFromDb();
      setRows(freshRows);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleAnswerChange = async (factorName: string, value: string | number | boolean) => {
    if (!row) return;

    // 1. Optimistic local update
    const newAnswers: Record<string, any> = { ...localAnswers };
    const shouldClear = value === '' || (typeof value === 'number' && Number.isNaN(value));
    if (shouldClear) {
      delete newAnswers[factorName];
    } else {
      newAnswers[factorName] = value;
    }
    setLocalAnswers(newAnswers);
    setSavingFields(prev => ({ ...prev, [factorName]: true }));

    // 2. Persist to DB
    const success = await saveChoiceAnswerToDb(row.id, factorName, value, newAnswers);
    
    // 3. Update global store if successful
    if (success) {
      updateRow(row.id, { choice_answers: JSON.stringify(newAnswers) });

      // 4. Refresh results for this row
      setIsSearching(true);
      const results = await runSearchApi(row.title, row.id);
      setRowResults(row.id, results);
    }
    
    // 5. Clear saving state
    setTimeout(() => {
      setSavingFields(prev => ({ ...prev, [factorName]: false }));
    }, 500);
  };

  const handleTextChange = (factorName: string, value: string | number) => {
    // Local-only update; commit onBlur
    setLocalAnswers(prev => ({ ...prev, [factorName]: value }));
  };

  const isPriceRangeFactor = (factor: any) => {
    const name = String(factor?.name || '').toLowerCase();
    return factor?.type === 'number' && (name.includes('price') || name.includes('budget'));
  };

  return (
    <div 
      className={cn(
        "h-full bg-white/80 backdrop-blur-xl flex flex-col shrink-0 transition-all duration-300 ease-in-out overflow-hidden border-warm-grey/50 z-20",
        isSidebarOpen ? "w-80 border-r opacity-100" : "w-0 border-none opacity-0"
      )}
    >
      <div className="w-80 h-full flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-warm-grey/50 flex justify-between items-center bg-white/50">
          <div>
            <h2 className="font-serif font-semibold text-lg text-onyx flex items-center gap-2">
              <SlidersHorizontal size={18} className="text-agent-blurple" />
              Specifications
            </h2>
            <p className="text-xs text-onyx-muted mt-0.5">
              {row ? 'Refine your requirements' : 'No request selected'}
            </p>
          </div>
          <div className="flex items-center gap-1">
            {row && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleManualRefresh}
                className={cn("h-8 w-8 p-0 text-onyx-muted hover:text-agent-blurple", isRefreshing && "animate-spin")}
                title="Refresh specs"
              >
                <RefreshCw size={16} />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(false)}
              className="h-8 w-8 p-0 text-onyx-muted hover:text-onyx"
              title="Collapse sidebar"
            >
              <ChevronLeft size={20} />
            </Button>
          </div>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
          {!row ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-onyx-muted space-y-4">
               <div className="w-12 h-12 bg-warm-light rounded-full flex items-center justify-center">
                 <AlertCircle size={24} className="opacity-50" />
               </div>
               <p className="text-sm">Select a request from the board to edit its specifications.</p>
            </div>
          ) : factors.length === 0 ? (
            <div className="text-center py-12">
              {pollCount < 5 ? (
                <>
                  <div className="w-12 h-12 bg-agent-blurple/10 text-agent-blurple rounded-full flex items-center justify-center mx-auto mb-4">
                    <Loader2 className="animate-spin" size={24} />
                  </div>
                  <p className="text-onyx font-medium text-sm">Analyzing Request...</p>
                  <p className="text-xs text-onyx-muted mt-2">
                    Extracting key buying criteria...
                  </p>
                </>
              ) : (
                <div className="space-y-4">
                   <div className="w-12 h-12 bg-warm-light text-onyx-muted rounded-full flex items-center justify-center mx-auto mb-2">
                    <AlertCircle size={24} />
                  </div>
                  <div>
                    <p className="text-onyx font-medium text-sm">No specifications found</p>
                    <p className="text-xs text-onyx-muted mt-1 px-4">
                      We couldn't identify specific criteria for this item.
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleManualRefresh}
                    className="text-agent-blurple hover:bg-agent-blurple/5"
                  >
                    Try Refreshing
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {factors.map(factor => {
                const isSaving = savingFields[factor.name];
                const hasAnswer = localAnswers[factor.name] !== undefined && localAnswers[factor.name] !== '';
                
                // Convert snake_case name to Title Case Label
                const label = factor.name.split('_').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                
                return (
                  <div key={factor.name} className="group">
                    <label className="flex items-center justify-between text-xs font-semibold text-onyx-muted mb-2 uppercase tracking-wide">
                      <span className="flex items-center gap-2">
                        {label}
                        {factor.required && (
                          <span className="text-[9px] font-bold text-agent-camel bg-agent-camel/10 px-1.5 py-0.5 rounded">
                            REQ
                          </span>
                        )}
                      </span>
                      <div className="h-3 w-3">
                        {isSaving ? (
                          <Loader2 className="animate-spin text-agent-blurple" size={12} />
                        ) : hasAnswer ? (
                          <Check className="text-status-success" size={12} />
                        ) : null}
                      </div>
                    </label>
                    
                    <div className="relative">
                      {factor.type === 'select' && factor.options ? (
                        <div className="relative">
                          <select
                            value={localAnswers[factor.name] || ''}
                            onChange={(e) => handleAnswerChange(factor.name, e.target.value)}
                            className="w-full px-4 py-3 bg-warm-light border-b-2 border-transparent rounded-t-md text-sm text-onyx focus:border-onyx transition-colors outline-none appearance-none cursor-pointer hover:bg-warm-grey/20"
                          >
                            <option value="" disabled>Select...</option>
                            {factor.options.map((opt: string) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-onyx-muted">
                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </div>
                      ) : factor.type === 'boolean' ? (
                        <div className="flex gap-2">
                          {['Yes', 'No'].map((opt) => {
                            const boolVal = opt === 'Yes';
                            const isSelected = localAnswers[factor.name] === boolVal;
                            return (
                              <button
                                key={opt}
                                onClick={() => handleAnswerChange(factor.name, boolVal)}
                                className={cn(
                                  "flex-1 py-2 px-4 rounded-lg text-xs font-medium border transition-all duration-200",
                                  isSelected 
                                    ? "bg-onyx text-white border-onyx shadow-md" 
                                    : "bg-white border-warm-grey text-onyx hover:bg-warm-light"
                                )}
                              >
                                {opt}
                              </button>
                            );
                          })}
                        </div>
                      ) : isPriceRangeFactor(factor) ? (
                        <div className="grid grid-cols-2 gap-3">
                          <Input
                            type="number"
                            value={localAnswers.min_price ?? ''}
                            onChange={(e) => handleTextChange('min_price', e.target.value === '' ? '' : Number(e.target.value))}
                            onBlur={(e) => handleAnswerChange('min_price', e.target.value === '' ? '' : Number(e.target.value))}
                            placeholder="Min"
                            className="text-sm py-2"
                          />
                          <Input
                            type="number"
                            value={localAnswers.max_price ?? ''}
                            onChange={(e) => handleTextChange('max_price', e.target.value === '' ? '' : Number(e.target.value))}
                            onBlur={(e) => handleAnswerChange('max_price', e.target.value === '' ? '' : Number(e.target.value))}
                            placeholder="Max"
                            className="text-sm py-2"
                          />
                        </div>
                      ) : (
                        <Input
                          type={factor.type === 'number' ? 'number' : 'text'}
                          value={localAnswers[factor.name] || ''}
                          onChange={(e) => handleTextChange(factor.name, factor.type === 'number' ? Number(e.target.value) : e.target.value)}
                          onBlur={(e) => handleAnswerChange(factor.name, factor.type === 'number' ? Number(e.target.value) : e.target.value)}
                          placeholder="..."
                          className="text-sm"
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        
        {/* Footer */}
        {row && factors.length > 0 && (
          <div className="p-4 bg-warm-light/30 border-t border-warm-grey/30">
            <div className="flex items-center justify-center gap-1.5 text-[10px] text-onyx-muted uppercase tracking-wider font-medium">
              <Check size={12} className="text-status-success" />
              <span>Auto-saved</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

