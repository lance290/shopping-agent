import { useState } from 'react';
import { parseChoiceFactors, parseChoiceAnswers, Row } from '../store';
import ChoiceFactorPanel from './ChoiceFactorPanel';

interface RequestTileProps {
  row: Row;
  onClick?: () => void;
}

export default function RequestTile({ row, onClick }: RequestTileProps) {
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const factors = parseChoiceFactors(row);
  const answers = parseChoiceAnswers(row);
  
  // Show answered factors as highlights
  const answeredFactors = factors.filter(f => answers[f.name] !== undefined);
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsPanelOpen(true);
    if (onClick) onClick();
  };

  return (
    <>
      <div 
        className="min-w-[200px] bg-blue-50 border-2 border-blue-200 rounded-lg p-3 flex-shrink-0 cursor-pointer hover:border-blue-400 h-full"
        onClick={handleClick}
      >
        <div className="text-xs text-blue-600 font-medium mb-1 uppercase tracking-wider">Looking For</div>
        <div className="font-medium text-sm text-gray-900 mb-2 line-clamp-2">{row.title}</div>
        
        {row.budget_max && (
          <div className="text-xs text-gray-600 mb-2">
            <span className="font-medium">Budget:</span> {row.currency} {row.budget_max}
          </div>
        )}
        
        {answeredFactors.length > 0 && (
          <div className="mt-2 space-y-1 border-t border-blue-100 pt-2">
            {answeredFactors.slice(0, 3).map(factor => (
              <div key={factor.name} className="text-xs text-gray-600 truncate">
                <span className="font-medium text-gray-700">{factor.label}:</span>{' '}
                {String(answers[factor.name])}
              </div>
            ))}
            {answeredFactors.length > 3 && (
              <div className="text-xs text-gray-400">
                +{answeredFactors.length - 3} more
              </div>
            )}
          </div>
        )}
        
        {answeredFactors.length === 0 && factors.length > 0 && (
          <div className="text-xs text-orange-600 mt-2 font-medium">
            {factors.filter(f => f.required).length} questions pending
          </div>
        )}
        
        <div className="text-xs text-blue-400 mt-auto pt-2">
          Click to refine
        </div>
      </div>
      
      <ChoiceFactorPanel 
        row={row} 
        isOpen={isPanelOpen} 
        onClose={() => setIsPanelOpen(false)} 
      />
    </>
  );
}
