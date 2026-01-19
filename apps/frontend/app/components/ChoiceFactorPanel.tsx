import { parseChoiceFactors, parseChoiceAnswers, Row } from '../store';

interface ChoiceFactorPanelProps {
  row: Row;
  isOpen: boolean;
  onClose: () => void;
}

export default function ChoiceFactorPanel({ row, isOpen, onClose }: ChoiceFactorPanelProps) {
  const factors = parseChoiceFactors(row);
  const answers = parseChoiceAnswers(row);
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div 
        className="bg-white rounded-lg p-6 max-w-md w-full max-h-[80vh] overflow-y-auto shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Requirements: {row.title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        
        {factors.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No specific choice factors identified yet.</p>
            <p className="text-sm mt-2">The agent is still analyzing your request.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {factors.map(factor => (
              <div key={factor.name} className="border-b border-gray-100 pb-3 last:border-0">
                <div className="flex justify-between items-baseline">
                  <div>
                    <div className="font-medium text-sm text-gray-800">{factor.label}</div>
                    {factor.required && !answers[factor.name] && (
                      <span className="text-[10px] text-orange-600 font-medium">Required</span>
                    )}
                  </div>
                  <div className="text-sm text-right ml-4">
                    {answers[factor.name] !== undefined 
                      ? <span className="text-blue-600 font-medium">{String(answers[factor.name])}</span>
                      : <span className="text-gray-400 italic">Not answered</span>
                    }
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        
        <div className="mt-6 pt-4 border-t border-gray-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
