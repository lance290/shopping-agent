import { useState, useEffect, useRef } from 'react';
import { parseChoiceFactors, parseChoiceAnswers, useShoppingStore } from '../store';
import { saveChoiceAnswerToDb, fetchSingleRowFromDb, runSearchApiWithStatus } from '../utils/api';
import { Loader2, Check, AlertCircle, ChevronLeft, RefreshCw, SlidersHorizontal } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { cn } from '../../utils/cn';

export default function ChoiceFactorPanel() {
  const { rows, activeRowId, updateRow, setRowResults, setIsSearching, isSidebarOpen, setSidebarOpen } = useShoppingStore();
  
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
        const freshRow = await fetchSingleRowFromDb(row.id);
        if (freshRow) {
          updateRow(row.id, freshRow);
        }
        setPollCount(prev => prev + 1);
      }, 2000); // Poll every 2s
    }

    return () => clearTimeout(timeoutId);
  }, [isSidebarOpen, row, factors.length, pollCount, updateRow]);

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

      const freshRow = await fetchSingleRowFromDb(row.id);
      if (freshRow) {
        updateRow(row.id, freshRow);
      }
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleAnswerChange = async (factorName: string, value: string | number | boolean | string[]) => {
    if (!row) return;

    // 1. Optimistic local update
    const newAnswers: Record<string, any> = { ...localAnswers };
    const shouldClear = value === '' || (typeof value === 'number' && Number.isNaN(value)) || (Array.isArray(value) && value.length === 0);
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
      const res = await runSearchApiWithStatus(row.title, row.id);
      setRowResults(row.id, res.results, res.providerStatuses);
      const freshRow = await fetchSingleRowFromDb(row.id);
      if (freshRow) {
        updateRow(row.id, freshRow);
      }
    }

    // 5. Clear saving state
    setTimeout(() => {
      setSavingFields(prev => ({ ...prev, [factorName]: false }));
    }, 500);
  };

  const handleMultiSelectToggle = async (factorName: string, option: string) => {
    if (!row) return;

    const currentValue = localAnswers[factorName];
    const currentArray = Array.isArray(currentValue) ? currentValue : [];

    let newArray: string[];
    if (currentArray.includes(option)) {
      // Remove the option
      newArray = currentArray.filter((item: string) => item !== option);
    } else {
      // Add the option
      newArray = [...currentArray, option];
    }

    await handleAnswerChange(factorName, newArray);
  };

  const handleTextChange = (factorName: string, value: string | number) => {
    // Local-only update; commit onBlur
    setLocalAnswers(prev => ({ ...prev, [factorName]: value }));
  };

  const isPriceRangeFactor = (factor: any) => {
    const name = String(factor?.name || '').toLowerCase();
    return factor?.type === 'number' && (name.includes('price') || name.includes('budget'));
  };

  // Determine which factors to display (progressive disclosure)
  const getVisibleFactors = () => {
    if (factors.length === 0) return [];

    // Separate required and optional factors
    const requiredFactors = factors.filter((f) => f.required);
    const optionalFactors = factors.filter((f) => !f.required);

    // Check which required factors have answers
    const answeredRequired: any[] = [];
    const unansweredRequired: any[] = [];

    requiredFactors.forEach((factor) => {
      const hasAnswer = factor.name === 'min_price'
        ? (localAnswers.min_price !== undefined && localAnswers.min_price !== '') ||
          (localAnswers.max_price !== undefined && localAnswers.max_price !== '')
        : factor.type === 'multiselect'
        ? Array.isArray(localAnswers[factor.name]) && localAnswers[factor.name].length > 0
        : localAnswers[factor.name] !== undefined && localAnswers[factor.name] !== '';

      if (hasAnswer) {
        answeredRequired.push(factor);
      } else {
        unansweredRequired.push(factor);
      }
    });

    // Progressive disclosure: Show answered required + first unanswered required
    // Once all required are answered, show all optional factors too
    if (unansweredRequired.length > 0) {
      // Show all answered required factors + only the FIRST unanswered required
      return [...answeredRequired, unansweredRequired[0]];
    } else {
      // All required answered - show everything
      return [...answeredRequired, ...optionalFactors];
    }
  };

  const visibleFactors = getVisibleFactors();
  const totalRequired = factors.filter((f) => f.required).length;
  const answeredRequired = factors.filter((f) => {
    if (!f.required) return false;
    const hasAnswer = f.name === 'min_price'
      ? (localAnswers.min_price !== undefined && localAnswers.min_price !== '') ||
        (localAnswers.max_price !== undefined && localAnswers.max_price !== '')
      : f.type === 'multiselect'
      ? Array.isArray(localAnswers[f.name]) && localAnswers[f.name].length > 0
      : localAnswers[f.name] !== undefined && localAnswers[f.name] !== '';
    return hasAnswer;
  }).length;

  return (
    <div
      className={cn(
        "h-full bg-warm-light flex flex-col shrink-0 transition-all duration-300 ease-in-out overflow-hidden border-warm-grey/70 z-20",
        isSidebarOpen ? "w-80 border-r opacity-100" : "w-0 border-none opacity-0"
      )}
    >
      <div className="w-80 h-full flex flex-col">
        {/* Header */}
        <div className="h-20 px-6 border-b border-warm-grey/70 flex justify-between items-center bg-warm-light">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-onyx-muted/80 font-medium">Specifications</div>
            <h2 className="font-medium text-lg text-onyx flex items-center gap-2 mt-2">
              <span className="p-2 bg-white border border-warm-grey/70 rounded-lg text-onyx-muted">
                <SlidersHorizontal size={16} />
              </span>
              Requirements
            </h2>
            <p className="text-xs text-onyx-muted/80 mt-1">
              {row ? (totalRequired > 0 ? `${answeredRequired}/${totalRequired} required` : 'Refine your requirements') : 'No request selected'}
            </p>
          </div>
          <div className="flex items-center gap-1">
            {row && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleManualRefresh}
                className={cn("h-8 w-8 p-0 text-onyx-muted hover:text-onyx", isRefreshing && "animate-spin")}
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
                  <div className="w-12 h-12 bg-warm-light text-onyx-muted rounded-full flex items-center justify-center mx-auto mb-4">
                    <Loader2 className="animate-spin" size={24} />
                  </div>
                  <p className="text-onyx font-medium text-sm">Analyzing request...</p>
                  <p className="text-xs text-onyx-muted mt-2">
                    Extracting key buying criteria.
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
              {visibleFactors
                .filter((factor) => factor.name !== 'max_price') // Handled by min_price price range component
                .map(factor => {
                const isSaving = savingFields[factor.name] || (factor.name === 'min_price' && savingFields['max_price']);
                const hasAnswer = factor.name === 'min_price'
                  ? (localAnswers.min_price !== undefined && localAnswers.min_price !== '') ||
                    (localAnswers.max_price !== undefined && localAnswers.max_price !== '')
                  : factor.type === 'multiselect'
                  ? Array.isArray(localAnswers[factor.name]) && localAnswers[factor.name].length > 0
                  : localAnswers[factor.name] !== undefined && localAnswers[factor.name] !== '';
                
                // Convert snake_case name to Title Case Label
                const label = factor.name === 'min_price'
                  ? 'Price Range ($)'
                  : factor.name.split('_').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                
                return (
                  <div key={factor.name} className="group">
                    <label className="flex items-center justify-between text-xs font-semibold text-onyx-muted mb-2 uppercase tracking-wider">
                      <span className="flex items-center gap-2">
                        {label}
                        {factor.required && (
                          <span className="text-[9px] font-bold text-onyx-muted bg-warm-light px-1.5 py-0.5 rounded">
                            REQ
                          </span>
                        )}
                      </span>
                      <div className="h-4 w-4">
                        {isSaving ? (
                          <Loader2 className="animate-spin text-status-success" size={16} />
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
                            className="w-full px-4 py-3 bg-white border border-gray-300 rounded-xl text-sm text-gray-900 focus:border-blue-500 transition-colors outline-none appearance-none cursor-pointer hover:border-gray-400"
                          >
                            <option value="" disabled>Select...</option>
                            {factor.options.map((opt: string) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-gray-500">
                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </div>
                      ) : factor.type === 'multiselect' && factor.options ? (
                        <div className="space-y-2">
                          {factor.options.map((opt: string) => {
                            const currentValue = localAnswers[factor.name];
                            const selectedOptions = Array.isArray(currentValue) ? currentValue : [];
                            const isSelected = selectedOptions.includes(opt);

                            return (
                              <label
                                key={opt}
                                className={cn(
                                  "flex items-center gap-3 px-4 py-3 bg-white border rounded-xl text-sm cursor-pointer transition-all hover:border-blue-400",
                                  isSelected ? "border-blue-500 bg-blue-50" : "border-gray-300"
                                )}
                              >
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => handleMultiSelectToggle(factor.name, opt)}
                                  className="w-4 h-4 text-blue-500 border-gray-300 rounded focus:ring-blue-500"
                                />
                                <span className={cn("flex-1", isSelected && "font-medium text-blue-900")}>
                                  {opt}
                                </span>
                              </label>
                            );
                          })}
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
                                  "flex-1 py-2 px-4 rounded-lg text-xs font-semibold border transition-all duration-200",
                                  isSelected 
                                    ? "bg-onyx text-white border-onyx" 
                                    : "bg-white border-warm-grey text-onyx hover:border-onyx-muted"
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
          <div className="p-4 bg-warm-light/50 border-t border-warm-grey/70">
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

