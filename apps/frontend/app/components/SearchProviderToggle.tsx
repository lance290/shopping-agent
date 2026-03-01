'use client';

import { useShoppingStore } from '../store';
import { cn } from '../../utils/cn';
import { ShoppingBag, Store, Search, Briefcase, Check, X, ShoppingCart, Ticket } from 'lucide-react';

const PROVIDERS = [
  { id: 'amazon', label: 'Amazon', icon: ShoppingBag, color: 'text-orange-600' },
  { id: 'ebay', label: 'eBay', icon: Store, color: 'text-red-600' },
  { id: 'kroger', label: 'Kroger', icon: ShoppingCart, color: 'text-blue-700' },
  { id: 'ticketmaster', label: 'Tickets', icon: Ticket, color: 'text-sky-600' },
  { id: 'serpapi', label: 'Google', icon: Search, color: 'text-blue-600' },
  { id: 'vendor_directory', label: 'Bespoke', icon: Briefcase, color: 'text-purple-600' },
] as const;

export default function SearchProviderToggle() {
  const selectedProviders = useShoppingStore((s) => s.selectedProviders);
  const toggleProvider = useShoppingStore((s) => s.toggleProvider);

  const activeCount = Object.values(selectedProviders).filter(Boolean).length;

  return (
    <div className="flex items-center gap-1 flex-wrap">
      <span className="text-[10px] text-gray-400 mr-0.5">Sources:</span>
      {PROVIDERS.map(({ id, label, icon: Icon, color }) => {
        const isActive = selectedProviders[id] ?? false;
        return (
          <button
            key={id}
            type="button"
            role="switch"
            aria-checked={isActive}
            onClick={() => {
              if (isActive && activeCount <= 1) return;
              toggleProvider(id);
            }}
            className={cn(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium transition-all duration-150",
              isActive
                ? "bg-white border border-gray-200 shadow-sm"
                : "bg-transparent border border-transparent text-gray-400 hover:bg-gray-50"
            )}
            title={isActive ? `${label} ON — click to disable` : `${label} OFF — click to enable`}
          >
            {isActive ? (
              <Check size={10} className="text-green-500 shrink-0" strokeWidth={3} />
            ) : (
              <X size={10} className="text-red-400 shrink-0" strokeWidth={3} />
            )}
            <Icon size={11} className={cn(isActive ? color : 'text-gray-400')} />
            <span className={cn(isActive ? 'text-gray-700' : 'text-gray-400')}>{label}</span>
          </button>
        );
      })}
    </div>
  );
}
