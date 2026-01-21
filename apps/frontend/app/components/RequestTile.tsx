import { parseChoiceAnswers, Row, useShoppingStore } from '../store';
import { Trash2, SlidersHorizontal } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';

interface RequestTileProps {
  row: Row;
  onClick?: () => void;
}

export default function RequestTile({ row, onClick }: RequestTileProps) {
  const { setActiveRowId, setSidebarOpen, requestDeleteRow } = useShoppingStore();
  const answers = parseChoiceAnswers(row);

  const normalizePrice = (v: any): number | undefined => {
    if (v === null || v === '' || v === undefined) return undefined;
    if (typeof v === 'number' && Number.isNaN(v)) return undefined;
    const n = typeof v === 'string' ? Number(v) : v;
    if (typeof n === 'number' && !Number.isNaN(n)) return n;
    return undefined;
  };

  const minPrice = normalizePrice(answers.min_price ?? answers.budget_min);
  const maxPrice = normalizePrice(answers.max_price ?? answers.budget_max ?? row.budget_max);

  const constraints = Object.entries(answers).filter(([k]) => ![
    'min_price',
    'max_price',
    'budget_min',
    'budget_max',
  ].includes(k));
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setActiveRowId(row.id);
    setSidebarOpen(true);
    if (onClick) onClick();
  };

  return (
    <Card 
      variant="hover"
      className="min-w-[260px] max-w-[280px] h-full flex flex-col p-5 bg-gradient-to-br from-white to-warm-light/50 border-warm-grey cursor-pointer group"
      onClick={handleClick}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
         <div className="p-2 bg-agent-blurple/10 rounded-lg text-agent-blurple">
           <SlidersHorizontal size={18} />
         </div>

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

      {/* Title */}
      <h3 className="font-serif text-lg font-medium text-onyx mb-4 line-clamp-2 leading-tight">
        {row.title}
      </h3>
      
      {/* Key Specs / Constraints */}
      <div className="space-y-3 flex-1">
        {(minPrice !== undefined || maxPrice !== undefined) && (
          <div className="flex justify-between text-sm items-center pb-2 border-b border-warm-grey/50">
            <span className="text-onyx-muted font-medium">Budget</span>
            <span className="font-bold text-onyx font-mono">
              {minPrice !== undefined && maxPrice !== undefined
                ? `${row.currency} ${minPrice}–${maxPrice}`
                : maxPrice !== undefined
                  ? `≤ ${row.currency} ${maxPrice}`
                  : `≥ ${row.currency} ${minPrice}`}
            </span>
          </div>
        )}
        
        {constraints.slice(0, 4).map(([key, value]) => (
          <div key={key} className="flex justify-between text-sm items-start gap-3">
            <span className="text-onyx-muted capitalize shrink-0 text-xs">{key.replace(/_/g, ' ')}</span>
            <span className="font-medium text-onyx text-right truncate text-xs bg-warm-light px-2 py-0.5 rounded-md border border-warm-grey/50">
              {String(value)}
            </span>
          </div>
        ))}
        
        {constraints.length > 4 && (
          <div className="text-xs text-agent-blurple font-medium pt-2 text-center">
            +{constraints.length - 4} more specs
          </div>
        )}

        {constraints.length === 0 && minPrice === undefined && maxPrice === undefined && (
          <div className="text-sm text-onyx-muted italic text-center pt-4">
            No constraints set
          </div>
        )}
      </div>
      
      <div className="mt-4 pt-4 border-t border-warm-grey/50 text-center">
        <span className="text-xs font-medium text-agent-blurple group-hover:underline">
          Edit Requirements →
        </span>
      </div>
    </Card>
  );
}
