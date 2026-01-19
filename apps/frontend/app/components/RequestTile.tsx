import { parseChoiceAnswers, Row, useShoppingStore } from '../store';
import { Edit2, Trash2 } from 'lucide-react';

interface RequestTileProps {
  row: Row;
  onClick?: () => void;
}

export default function RequestTile({ row, onClick }: RequestTileProps) {
  const { setActiveRowId, setSidebarOpen, requestDeleteRow } = useShoppingStore();
  const answers = parseChoiceAnswers(row);
  
  // Format constraints for display
  const constraints = Object.entries(answers);
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setActiveRowId(row.id);
    setSidebarOpen(true);
    if (onClick) onClick();
  };

  return (
    <>
      <div 
        className="min-w-[240px] max-w-[280px] bg-white border border-gray-200 rounded-xl p-4 flex-shrink-0 cursor-pointer hover:border-blue-400 hover:shadow-sm transition-all h-full flex flex-col group relative"
        onClick={handleClick}
      >
        {/* Status Badge */}
        <div className="flex justify-between items-start mb-2">
           <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
             row.status === 'sourcing' ? 'bg-blue-100 text-blue-700' :
             row.status === 'bids_arriving' ? 'bg-green-100 text-green-700' :
             'bg-gray-100 text-gray-600'
           }`}>
             {row.status.replace('_', ' ')}
           </span>

           <button
             onClick={(e) => {
               e.stopPropagation();
               requestDeleteRow(row.id);
             }}
             className="opacity-0 group-hover:opacity-100 p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 transition-all"
             title="Archive row"
             aria-label="Archive row"
           >
             <Trash2 size={14} />
           </button>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-gray-900 mb-3 line-clamp-2 leading-tight">
          {row.title}
        </h3>
        
        {/* Key Specs / Constraints */}
        <div className="space-y-2 mb-4 flex-1">
          {row.budget_max && (
            <div className="flex justify-between text-sm items-center">
              <span className="text-gray-500">Budget</span>
              <span className="font-medium text-gray-900">{row.currency} {row.budget_max}</span>
            </div>
          )}
          
          {constraints.slice(0, 4).map(([key, value]) => (
            <div key={key} className="flex justify-between text-sm items-start gap-2">
              <span className="text-gray-500 capitalize shrink-0">{key.replace(/_/g, ' ')}</span>
              <span className="font-medium text-gray-900 text-right truncate">{String(value)}</span>
            </div>
          ))}
          
          {constraints.length > 4 && (
            <div className="text-xs text-gray-400 pt-1">
              +{constraints.length - 4} more specs
            </div>
          )}
        </div>
        
        {/* Footer / Action */}
        <div className="mt-auto pt-3 border-t border-gray-100 flex items-center text-xs text-gray-500 group-hover:text-blue-600 transition-colors">
          <Edit2 size={12} className="mr-1.5" />
          Edit Requirements
        </div>
      </div>
    </>
  );
}
