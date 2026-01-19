import { useState, useEffect, useRef } from 'react';
import { parseChoiceFactors, parseChoiceAnswers, useShoppingStore } from '../store';
import { saveChoiceAnswerToDb, fetchRowsFromDb } from '../utils/api';
import { Loader2, Check, AlertCircle, ChevronLeft, RefreshCw } from 'lucide-react';

export default function ChoiceFactorPanel() {
  const { rows, activeRowId, updateRow, setRows, isSidebarOpen, setSidebarOpen } = useShoppingStore();
  
  const row = rows.find(r => r.id === activeRowId);
  const factors = row ? parseChoiceFactors(row) : [];
  
  // Local state
  const [localAnswers, setLocalAnswers] = useState<Record<string, any>>({});
  const [savingFields, setSavingFields] = useState<Record<string, boolean>>({});
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pollCount, setPollCount] = useState(0);

  // Sync local state when active row changes
  useEffect(() => {
    if (row) {
      setLocalAnswers(parseChoiceAnswers(row));
      // Reset poll count when switching rows
      setPollCount(0);
    } else {
      setLocalAnswers({});
    }
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
      const freshRows = await fetchRowsFromDb();
      setRows(freshRows);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleAnswerChange = async (factorName: string, value: string | number | boolean) => {
    if (!row) return;

    // 1. Optimistic local update
    const newAnswers = { ...localAnswers, [factorName]: value };
    setLocalAnswers(newAnswers);
    setSavingFields(prev => ({ ...prev, [factorName]: true }));

    // 2. Persist to DB
    const success = await saveChoiceAnswerToDb(row.id, factorName, value);
    
    // 3. Update global store if successful
    if (success) {
      updateRow(row.id, { choice_answers: JSON.stringify(newAnswers) });
    }
    
    // 4. Clear saving state
    setTimeout(() => {
      setSavingFields(prev => ({ ...prev, [factorName]: false }));
    }, 500);
  };

  return (
    <div 
      className={`h-full bg-white flex flex-col shrink-0 transition-all duration-300 ease-in-out overflow-hidden border-gray-200 ${
        isSidebarOpen ? 'w-80 border-r opacity-100' : 'w-0 border-none opacity-0'
      }`}
    >
      <div className="w-80 h-full flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50/50">
          <div>
            <h2 className="font-semibold text-gray-900">Specifications</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {row ? 'Edit requirements' : 'No request selected'}
            </p>
          </div>
          <div className="flex items-center gap-1">
            {row && (
              <button
                onClick={handleManualRefresh}
                className={`p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors ${isRefreshing ? 'animate-spin' : ''}`}
                title="Refresh specs"
              >
                <RefreshCw size={16} />
              </button>
            )}
            <button 
              onClick={() => setSidebarOpen(false)}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title="Collapse sidebar"
            >
              <ChevronLeft size={20} />
            </button>
          </div>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
          {!row ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-gray-400 space-y-3">
               <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                 <AlertCircle size={20} />
               </div>
               <p className="text-sm">Select a request from the board to edit its specifications.</p>
            </div>
          ) : factors.length === 0 ? (
            <div className="text-center py-12">
              {pollCount < 5 ? (
                <>
                  <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Loader2 className="animate-spin" size={20} />
                  </div>
                  <p className="text-gray-900 font-medium text-sm">Extracting specs...</p>
                  <p className="text-xs text-gray-500 mt-2">
                    Identifying key attributes...
                  </p>
                </>
              ) : (
                <div className="space-y-4">
                   <div className="w-10 h-10 bg-gray-100 text-gray-400 rounded-full flex items-center justify-center mx-auto mb-2">
                    <AlertCircle size={20} />
                  </div>
                  <div>
                    <p className="text-gray-900 font-medium text-sm">No specifications found</p>
                    <p className="text-xs text-gray-500 mt-1 px-4">
                      The agent didn't identify specific attributes for this item yet.
                    </p>
                  </div>
                  <button 
                    onClick={handleManualRefresh}
                    className="text-xs text-blue-600 font-medium hover:underline"
                  >
                    Try Refreshing
                  </button>
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
                    <label className="flex items-center justify-between text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                      <span className="flex items-center gap-2">
                        {label}
                        {factor.required && (
                          <span className="text-[9px] font-bold text-orange-600 bg-orange-50 px-1 py-0.5 rounded">
                            REQ
                          </span>
                        )}
                      </span>
                      <div className="h-3 w-3">
                        {isSaving ? (
                          <Loader2 className="animate-spin text-blue-500" size={12} />
                        ) : hasAnswer ? (
                          <Check className="text-green-500" size={12} />
                        ) : null}
                      </div>
                    </label>
                    
                    <div className="relative">
                      {factor.type === 'select' && factor.options ? (
                        <div className="relative">
                          <select
                            value={localAnswers[factor.name] || ''}
                            onChange={(e) => handleAnswerChange(factor.name, e.target.value)}
                            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-sm text-gray-900 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-shadow outline-none appearance-none cursor-pointer hover:border-gray-300"
                          >
                            <option value="" disabled>Select...</option>
                            {factor.options.map((opt: string) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
                            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
                                className={`flex-1 py-1.5 px-3 rounded-md text-xs font-medium border transition-all duration-200 ${
                                  isSelected 
                                    ? 'bg-blue-600 border-blue-600 text-white shadow-sm' 
                                    : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300'
                                }`}
                              >
                                {opt}
                              </button>
                            );
                          })}
                        </div>
                      ) : (
                        <input
                          type={factor.type === 'number' ? 'number' : 'text'}
                          value={localAnswers[factor.name] || ''}
                          onChange={(e) => handleAnswerChange(factor.name, factor.type === 'number' ? Number(e.target.value) : e.target.value)}
                          placeholder={`...`}
                          className="w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-sm text-gray-900 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-shadow outline-none hover:border-gray-300 placeholder-gray-400"
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
          <div className="p-3 bg-gray-50 border-t border-gray-100">
            <div className="flex items-center justify-center gap-1.5 text-xs text-gray-500">
              <Check size={12} className="text-green-600" />
              <span>Changes saved automatically</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

