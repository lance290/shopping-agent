import { useEffect, useState } from 'react';
import { parseChoiceAnswers, parseChoiceFactors, Row, useShoppingStore } from '../store';
import { Check, Loader2, RefreshCw, SlidersHorizontal, Trash2 } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { cn } from '../../utils/cn';
import { fetchSingleRowFromDb, runSearchApiWithStatus, saveChoiceAnswerToDb } from '../utils/api';

interface RequestTileProps {
  row: Row;
  onClick?: () => void;
}

export default function RequestTile({ row, onClick }: RequestTileProps) {
  const {
    setActiveRowId,
    requestDeleteRow,
    updateRow,
    setRowResults,
    setIsSearching,
  } = useShoppingStore();
  const factors = parseChoiceFactors(row);
  const [localAnswers, setLocalAnswers] = useState<Record<string, any>>({});
  const [savingFields, setSavingFields] = useState<Record<string, boolean>>({});
  const [pollCount, setPollCount] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [didAutoRegenerate, setDidAutoRegenerate] = useState(false);

  useEffect(() => {
    setLocalAnswers(parseChoiceAnswers(row));
    setPollCount(0);
    setDidAutoRegenerate(false);
  }, [row.id]);

  const isGenericFallbackFactors = (list: any[]) => {
    if (!Array.isArray(list) || list.length === 0) return false;
    const names = list.map((f) => String(f?.name || '').toLowerCase()).filter(Boolean);
    const generic = ['max_budget', 'preferred_brand', 'condition', 'shipping_speed', 'notes'];
    return generic.every((n) => names.includes(n));
  };

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    if (!didAutoRegenerate && isGenericFallbackFactors(factors)) {
      timeoutId = setTimeout(async () => {
        try {
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
          setDidAutoRegenerate(true);
        }
      }, 250);
    }

    return () => clearTimeout(timeoutId);
  }, [didAutoRegenerate, row.id, updateRow, factors]);

  useEffect(() => {
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
  }, [row.choice_answers]);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    if (factors.length === 0 && pollCount < 4) {
      timeoutId = setTimeout(async () => {
        const freshRow = await fetchSingleRowFromDb(row.id);
        if (freshRow) {
          updateRow(row.id, freshRow);
        }
        setPollCount(prev => prev + 1);
      }, 2000);
    }

    return () => clearTimeout(timeoutId);
  }, [factors.length, pollCount, row.id, updateRow]);

  const handleManualRefresh = async () => {
    console.log('[RequestTile] handleManualRefresh called for row:', row.id);
    setIsRefreshing(true);
    setIsSearching(true);
    setPollCount(0);
    try {
      console.log('[RequestTile] Regenerating choice factors...');
      await fetch(`/api/rows?id=${row.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ regenerate_choice_factors: true }),
      });
      
      // Also trigger a search to refresh offers
      console.log('[RequestTile] Triggering search...');
      const searchResponse = await runSearchApiWithStatus(row.title, row.id);
      console.log('[RequestTile] Search response:', searchResponse.results?.length, 'results');
      if (searchResponse.results) {
        setRowResults(row.id, searchResponse.results, searchResponse.providerStatuses);
      }
      
      const freshRow = await fetchSingleRowFromDb(row.id);
      if (freshRow) {
        updateRow(row.id, freshRow);
      }
    } catch (err) {
      console.error('[RequestTile] handleManualRefresh error:', err);
    } finally {
      setIsRefreshing(false);
      setIsSearching(false);
    }
  };

  const handleAnswerChange = async (factorName: string, value: string | number | boolean | string[]) => {
    const newAnswers: Record<string, any> = { ...localAnswers };
    const shouldClear = value === '' || (typeof value === 'number' && Number.isNaN(value)) || (Array.isArray(value) && value.length === 0);
    if (shouldClear) {
      delete newAnswers[factorName];
    } else {
      newAnswers[factorName] = value;
    }
    setLocalAnswers(newAnswers);
    setSavingFields(prev => ({ ...prev, [factorName]: true }));

    const success = await saveChoiceAnswerToDb(row.id, factorName, value, newAnswers);
    if (success) {
      updateRow(row.id, { choice_answers: JSON.stringify(newAnswers) });
      setIsSearching(true);
      const res = await runSearchApiWithStatus(row.title, row.id);
      setRowResults(row.id, res.results, res.providerStatuses);
      const freshRow = await fetchSingleRowFromDb(row.id);
      if (freshRow) {
        updateRow(row.id, freshRow);
      }
      setIsSearching(false);
    }

    setTimeout(() => {
      setSavingFields(prev => ({ ...prev, [factorName]: false }));
    }, 400);
  };

  const handleMultiSelectToggle = async (factorName: string, option: string) => {
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
    setLocalAnswers(prev => ({ ...prev, [factorName]: value }));
  };

  const isPriceRangeFactor = (factor: any) => {
    const name = String(factor?.name || '').toLowerCase();
    return factor?.type === 'number' && (name.includes('price') || name.includes('budget'));
  };
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setActiveRowId(row.id);
    if (onClick) onClick();
  };

  return (
    <Card
      variant="hover"
      className="min-w-[290px] max-w-[320px] h-[450px] flex flex-col p-4 bg-warm-light border border-warm-grey/70 cursor-default group"
      onClick={handleClick}
    >
      {/* Header */}
      <div className="flex justify-between items-start gap-3 mb-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-onyx-muted font-semibold">Options</div>
          <div className="mt-2 p-2 bg-white border border-warm-grey/60 rounded-lg text-onyx-muted">
            <SlidersHorizontal size={16} />
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              handleManualRefresh();
            }}
            className={cn(
              "h-8 w-8 p-0 text-onyx-muted hover:text-onyx",
              isRefreshing && "animate-spin"
            )}
            title="Refresh options"
          >
            <RefreshCw size={16} />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              requestDeleteRow(row.id);
            }}
            className="h-8 w-8 p-0 text-onyx-muted hover:text-status-error hover:bg-status-error/5 opacity-0 group-hover:opacity-100 transition-all"
            title="Archive row"
          >
            <Trash2 size={16} />
          </Button>
        </div>
      </div>

      {/* Title */}
      <h3 className="text-base font-semibold text-onyx mb-3 line-clamp-2 leading-snug">
        {row.title}
      </h3>
      
      {/* Choice Factors */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-4 custom-scrollbar">
        {factors.length === 0 ? (
          <div className="text-center py-6 text-onyx-muted/80 text-xs space-y-2">
            <Loader2 className="w-4 h-4 animate-spin mx-auto" />
            <p>Analyzing request…</p>
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handleManualRefresh();
              }}
              className="text-agent-blurple hover:bg-agent-blurple/10"
            >
              Refresh
            </Button>
          </div>
        ) : (
          factors
            .filter((factor) => factor.name !== 'max_price') // Handled by min_price price range component
            .map((factor) => {
            const isSaving = savingFields[factor.name] || (factor.name === 'min_price' && savingFields['max_price']);
            const hasAnswer = factor.name === 'min_price'
              ? (localAnswers.min_price !== undefined && localAnswers.min_price !== '') ||
                (localAnswers.max_price !== undefined && localAnswers.max_price !== '')
              : factor.type === 'multiselect'
              ? Array.isArray(localAnswers[factor.name]) && localAnswers[factor.name].length > 0
              : localAnswers[factor.name] !== undefined && localAnswers[factor.name] !== '';
            const label = factor.name === 'min_price'
              ? 'Price Range ($)'
              : String(factor?.label || '')
                ? String(factor.label)
                : factor.name
                    .split('_')
                    .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
                    .join(' ');

            return (
              <div key={factor.name} className="space-y-2">
                <label className="flex items-center justify-between text-[10px] uppercase tracking-wider text-onyx-muted font-semibold">
                  <span>{label}</span>
                  {isSaving ? (
                    <Loader2 className="w-3 h-3 animate-spin text-agent-blurple" />
                  ) : hasAnswer ? (
                    <Check className="w-3 h-3 text-status-success" />
                  ) : null}
                </label>

                {factor.type === 'select' && factor.options ? (
                  <div className="relative">
                    <select
                      value={localAnswers[factor.name] || ''}
                      onChange={(e) => handleAnswerChange(factor.name, e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none appearance-none cursor-pointer"
                    >
                      <option value="" disabled>Select...</option>
                      {factor.options.map((opt: string) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-onyx-muted">
                      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                ) : factor.type === 'multiselect' && factor.options ? (
                  <div className="space-y-1.5">
                    {factor.options.map((opt: string) => {
                      const currentValue = localAnswers[factor.name];
                      const selectedOptions = Array.isArray(currentValue) ? currentValue : [];
                      const isSelected = selectedOptions.includes(opt);

                      return (
                        <label
                          key={opt}
                          className={cn(
                            "flex items-center gap-2 px-3 py-2 bg-white border rounded-lg text-xs cursor-pointer transition-all hover:border-agent-blurple",
                            isSelected ? "border-agent-blurple bg-agent-blurple/5" : "border-warm-grey/60"
                          )}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleMultiSelectToggle(factor.name, opt)}
                            className="w-3 h-3 text-agent-blurple border-warm-grey rounded focus:ring-agent-blurple"
                          />
                          <span className={cn("flex-1", isSelected && "font-medium text-agent-blurple")}>
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
                            "flex-1 py-2 px-3 rounded-lg text-[11px] font-semibold border transition-all duration-200",
                            isSelected
                              ? "bg-onyx text-white border-onyx"
                              : "bg-white border-warm-grey/60 text-gray-900 hover:border-onyx-muted"
                          )}
                        >
                          {opt}
                        </button>
                      );
                    })}
                  </div>
                ) : isPriceRangeFactor(factor) ? (
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      value={localAnswers.min_price ?? ''}
                      onChange={(e) => handleTextChange('min_price', e.target.value === '' ? '' : Number(e.target.value))}
                      onBlur={(e) => handleAnswerChange('min_price', e.target.value === '' ? '' : Number(e.target.value))}
                      placeholder="Min"
                      className="text-xs py-2"
                    />
                    <Input
                      type="number"
                      value={localAnswers.max_price ?? ''}
                      onChange={(e) => handleTextChange('max_price', e.target.value === '' ? '' : Number(e.target.value))}
                      onBlur={(e) => handleAnswerChange('max_price', e.target.value === '' ? '' : Number(e.target.value))}
                      placeholder="Max"
                      className="text-xs py-2"
                    />
                  </div>
                ) : (
                  <Input
                    type={factor.type === 'number' ? 'number' : 'text'}
                    value={localAnswers[factor.name] || ''}
                    onChange={(e) => handleTextChange(factor.name, factor.type === 'number' ? Number(e.target.value) : e.target.value)}
                    onBlur={(e) => handleAnswerChange(factor.name, factor.type === 'number' ? Number(e.target.value) : e.target.value)}
                    placeholder="..."
                    className="text-xs"
                  />
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-warm-grey/70 text-center text-[10px] text-onyx-muted uppercase tracking-wider">
        Auto-saved
      </div>
    </Card>
  );
}
