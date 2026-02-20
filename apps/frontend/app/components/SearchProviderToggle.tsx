'use client';

import { useShoppingStore } from '../store';
import { cn } from '../../utils/cn';
import { ShoppingBag, Globe, Store, Briefcase } from 'lucide-react';

const PROVIDERS = [
  { id: 'amazon', label: 'Amazon', icon: ShoppingBag, color: 'bg-orange-500/10 text-orange-700 border-orange-500/30' },
  { id: 'serpapi', label: 'Google', icon: Globe, color: 'bg-blue-500/10 text-blue-700 border-blue-500/30' },
  { id: 'ebay', label: 'eBay', icon: Store, color: 'bg-red-500/10 text-red-700 border-red-500/30' },
  { id: 'vendor_directory', label: 'Bespoke', icon: Briefcase, color: 'bg-purple-500/10 text-purple-700 border-purple-500/30' },
] as const;

export default function SearchProviderToggle() {
  const selectedProviders = useShoppingStore((s) => s.selectedProviders);
  const toggleProvider = useShoppingStore((s) => s.toggleProvider);

  const activeCount = Object.values(selectedProviders).filter(Boolean).length;

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-[10px] font-medium text-onyx-muted/60 uppercase tracking-wider mr-0.5">Search:</span>
      {PROVIDERS.map(({ id, label, icon: Icon, color }) => {
        const isActive = selectedProviders[id] ?? false;
        return (
          <button
            key={id}
            type="button"
            onClick={() => {
              if (isActive && activeCount <= 1) return;
              toggleProvider(id);
            }}
            className={cn(
              "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-all duration-150",
              isActive
                ? color
                : "bg-gray-100/60 text-gray-400 border-gray-200/60 hover:bg-gray-100"
            )}
            title={isActive ? `Disable ${label}` : `Enable ${label}`}
          >
            <Icon size={11} className={isActive ? '' : 'opacity-40'} />
            {label}
          </button>
        );
      })}
    </div>
  );
}
