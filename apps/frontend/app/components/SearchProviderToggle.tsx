'use client';

import { useShoppingStore } from '../store';
import { cn } from '../../utils/cn';
import { ShoppingBag, Globe, Store, Briefcase } from 'lucide-react';

const PROVIDERS = [
  { id: 'amazon', label: 'Amazon', icon: ShoppingBag, activeColor: 'bg-orange-100 text-orange-700 border-orange-300' },
  { id: 'serpapi', label: 'Google', icon: Globe, activeColor: 'bg-blue-100 text-blue-700 border-blue-300' },
  { id: 'ebay', label: 'eBay', icon: Store, activeColor: 'bg-red-100 text-red-700 border-red-300' },
  { id: 'vendor_directory', label: 'Bespoke', icon: Briefcase, activeColor: 'bg-purple-100 text-purple-700 border-purple-300' },
] as const;

export default function SearchProviderToggle() {
  const selectedProviders = useShoppingStore((s) => s.selectedProviders);
  const toggleProvider = useShoppingStore((s) => s.toggleProvider);

  const activeCount = Object.values(selectedProviders).filter(Boolean).length;

  return (
    <div className="grid grid-cols-2 gap-1.5">
      {PROVIDERS.map(({ id, label, icon: Icon, activeColor }) => {
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
              "inline-flex items-center justify-center gap-1 px-2 py-1 rounded-full text-[11px] font-semibold border transition-all duration-150",
              isActive
                ? activeColor
                : "bg-gray-100 text-gray-400 border-gray-200 hover:bg-gray-200"
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
