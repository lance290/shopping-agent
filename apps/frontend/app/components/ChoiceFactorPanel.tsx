import { useState, useEffect } from 'react';
import { parseChoiceFactors, parseChoiceAnswers, Row, useShoppingStore } from '../store';
import { saveChoiceAnswerToDb } from '../utils/api';
import { Loader2, Check, X, AlertCircle } from 'lucide-react';

interface ChoiceFactorPanelProps {
  row: Row;
  isOpen: boolean;
  onClose: () => void;
}

export default function ChoiceFactorPanel({ row, isOpen, onClose }: ChoiceFactorPanelProps) {
  const { updateRow } = useShoppingStore();
  const factors = parseChoiceFactors(row);
  // We need to keep local state in sync with row prop when it changes
  const [localAnswers, setLocalAnswers] = useState<Record<string, any>>({});
  const [savingFields, setSavingFields] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (isOpen) {
      setLocalAnswers(parseChoiceAnswers(row));
    }
  }, [row, isOpen]);

  if (!isOpen) return null;

  const handleAnswerChange = async (factorName: string, value: string | number | boolean) => {
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
    <div className="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div 
        className={`absolute inset-0 bg-gray-500/30 backdrop-blur-sm transition-opacity duration-300 ease-in-out ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`} 
        onClick={onClose}
      />

      {/* Panel */}
      <div className={`fixed inset-y-0 right-0 flex max-w-full pl-10 pointer-events-none ${isOpen ? 'translate-x-0' : 'translate-x-full'} transition-transform duration-300 ease-in-out sm:pl-16`}>
        <div className="w-screen max-w-md pointer-events-auto">
          <div className="flex h-full flex-col bg-white shadow-xl">
            {/* Header */}
            <div className="px-6 py-6 border-b border-gray-100 flex items-start justify-between bg-gray-50/50">
              <div>
                <h2 className="text-xl font-semibold text-gray-900" id="slide-over-title">Product Specifications</h2>
                <p className="text-sm text-gray-500 mt-1">Review and edit the constraints for "{row.title}".</p>
              </div>
              <div className="ml-3 flex h-7 items-center">
                <button
                  type="button"
                  className="rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  onClick={onClose}
                >
                  <span className="sr-only">Close panel</span>
                  <X size={24} aria-hidden="true" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="relative flex-1 px-6 py-6 overflow-y-auto custom-scrollbar">
              {factors.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Loader2 className="animate-spin" size={24} />
                  </div>
                  <p className="text-gray-900 font-medium">Extracting specifications...</p>
                  <p className="text-sm text-gray-500 mt-2">
                    The agent is identifying the key attributes for this request.
                  </p>
                </div>
              ) : (
                <div className="space-y-8">
                  {factors.map(factor => {
                    const isSaving = savingFields[factor.name];
                    const hasAnswer = localAnswers[factor.name] !== undefined && localAnswers[factor.name] !== '';
                    
                    // Convert snake_case name to Title Case Label
                    const label = factor.name.split('_').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                    
                    return (
                      <div key={factor.name} className="group">
                        <label className="flex items-center justify-between text-sm font-medium text-gray-900 mb-2">
                          <span className="flex items-center gap-2">
                            {label}
                            {factor.required && (
                              <span className="text-[10px] uppercase tracking-wider font-bold text-orange-600 bg-orange-50 px-1.5 py-0.5 rounded">
                                Required
                              </span>
                            )}
                          </span>
                          <div className="h-4 w-4">
                            {isSaving ? (
                              <Loader2 className="animate-spin text-blue-500" size={16} />
                            ) : hasAnswer ? (
                              <Check className="text-green-500" size={16} />
                            ) : null}
                          </div>
                        </label>
                        
                        <div className="relative">
                          {factor.type === 'select' && factor.options ? (
                            <div className="relative">
                              <select
                                value={localAnswers[factor.name] || ''}
                                onChange={(e) => handleAnswerChange(factor.name, e.target.value)}
                                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow outline-none appearance-none cursor-pointer hover:border-gray-300"
                              >
                                <option value="" disabled>Select an option...</option>
                                {factor.options.map((opt: string) => (
                                  <option key={opt} value={opt}>{opt}</option>
                                ))}
                              </select>
                              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-500">
                                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                              </div>
                            </div>
                          ) : factor.type === 'boolean' ? (
                            <div className="flex gap-3">
                              {['Yes', 'No'].map((opt) => {
                                const boolVal = opt === 'Yes';
                                const isSelected = localAnswers[factor.name] === boolVal;
                                return (
                                  <button
                                    key={opt}
                                    onClick={() => handleAnswerChange(factor.name, boolVal)}
                                    className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium border transition-all duration-200 ${
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
                              placeholder={`Enter ${label.toLowerCase()}...`}
                              className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow outline-none hover:border-gray-300 placeholder-gray-400"
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
            <div className="flex-shrink-0 px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-between items-center">
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <AlertCircle size={14} />
                <span>Auto-saved</span>
              </div>
              <button
                onClick={onClose}
                className="px-6 py-2.5 bg-gray-900 text-white rounded-lg hover:bg-gray-800 text-sm font-medium transition-all shadow-sm active:transform active:scale-95"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

