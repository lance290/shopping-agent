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
      className="min-w-[280px] max-w-[300px] h-full flex flex-col p-5 bg-gradient-to-b from-white via-white to-warm-light/40 border border-warm-grey/70 cursor-pointer group"
      onClick={handleClick}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
         <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-onyx-muted font-semibold">Request</div>
          <div className="mt-2 p-2 bg-white border border-warm-grey/70 rounded-lg text-onyx-muted">
           <SlidersHorizontal size={18} />
          </div>
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
      <h3 className="text-lg font-semibold text-onyx mb-4 line-clamp-2 leading-snug">
        {row.title}
      </h3>
      
      {/* Key Specs / Constraints */}
      <div className="space-y-3 flex-1">
        {(minPrice !== undefined || maxPrice !== undefined) && (
          <div className="flex justify-between text-sm items-center pb-2 border-b border-warm-grey/70">
            <span className="text-[10px] font-semibold text-onyx-muted uppercase tracking-[0.2em]">Budget</span>
            <span className="text-base font-semibold text-onyx">
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
            <span className="font-medium text-onyx text-right truncate text-xs bg-white px-2 py-0.5 rounded-md border border-warm-grey/70">
              {String(value)}
            </span>
          </div>
        ))}
        
        {constraints.length > 4 && (
          <div className="text-xs text-onyx-muted font-medium pt-2 text-center">
            +{constraints.length - 4} more specs
          </div>
        )}

        {constraints.length === 0 && minPrice === undefined && maxPrice === undefined && (
          <div className="text-sm text-onyx-muted italic text-center pt-4">
            No constraints set
          </div>
        )}
      </div>
      
      <div className="mt-4 pt-4 border-t border-warm-grey/70 text-center">
        <span className="text-xs font-semibold text-agent-blurple group-hover:underline">
          Edit requirements →
        </span>
      </div>
    </Card>
  );
}
