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
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200" onClick={onClose}>
      <div 
        className="bg-white rounded-xl w-full max-w-lg max-h-[85vh] flex flex-col shadow-2xl animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-center bg-gray-50/50 rounded-t-xl">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Product Specifications</h2>
            <p className="text-sm text-gray-500 mt-1">Review and edit the constraints for this request.</p>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6 overflow-y-auto custom-scrollbar flex-1">
          {factors.length === 0 ? (
            <div className="text-center py-12 px-4">
              <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <Loader2 className="animate-spin" size={24} />
              </div>
              <p className="text-gray-900 font-medium">Extracting specifications...</p>
              <p className="text-sm text-gray-500 mt-2 max-w-xs mx-auto">
                The agent is identifying the key attributes for "{row.title}".
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {factors.map(factor => {
                const isSaving = savingFields[factor.name];
                const hasAnswer = localAnswers[factor.name] !== undefined && localAnswers[factor.name] !== '';
                
                // Convert snake_case name to Title Case Label (e.g. "screen_size" -> "Screen Size")
                const label = factor.name.split('_').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                
                return (
                  <div key={factor.name} className="group">
                    <label className="flex items-center justify-between text-sm font-medium text-gray-700 mb-2">
                      <span className="flex items-center gap-2">
                        {label}
                        {factor.required && (
                          <span className="text-[10px] uppercase tracking-wider font-bold text-orange-500 bg-orange-50 px-1.5 py-0.5 rounded">
                            Required
                          </span>
                        )}
                      </span>
                      {isSaving ? (
                        <Loader2 className="animate-spin text-blue-500" size={14} />
                      ) : hasAnswer ? (
                        <Check className="text-green-500" size={14} />
                      ) : null}
                    </label>
                    
                    <div className="relative">
                      {factor.type === 'select' && factor.options ? (
                        <select
                          value={localAnswers[factor.name] || ''}
                          onChange={(e) => handleAnswerChange(factor.name, e.target.value)}
                          className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all outline-none appearance-none hover:bg-white"
                        >
                          <option value="" disabled>Select an option...</option>
                          {factor.options.map((opt: string) => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                      ) : factor.type === 'boolean' ? (
                        <div className="flex gap-3">
                          {['Yes', 'No'].map((opt) => {
                            const boolVal = opt === 'Yes';
                            const isSelected = localAnswers[factor.name] === boolVal;
                            return (
                              <button
                                key={opt}
                                onClick={() => handleAnswerChange(factor.name, boolVal)}
                                className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium border transition-all ${
                                  isSelected 
                                    ? 'bg-blue-50 border-blue-200 text-blue-700' 
                                    : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
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
                          placeholder={factor.type === 'number' ? '0' : 'Type your answer...'}
                          className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all outline-none hover:bg-white"
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
        <div className="px-6 py-4 bg-gray-50 rounded-b-xl border-t border-gray-100 flex justify-between items-center">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <AlertCircle size={14} />
            <span>Changes are saved automatically</span>
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2.5 bg-gray-900 text-white rounded-lg hover:bg-gray-800 text-sm font-medium transition-colors shadow-sm active:transform active:scale-95"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

