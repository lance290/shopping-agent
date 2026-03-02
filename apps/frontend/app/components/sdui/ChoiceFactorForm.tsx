'use client';

import type { ChoiceFactorFormBlock } from '../../sdui/types';

export function ChoiceFactorForm({ factors }: ChoiceFactorFormBlock) {
  if (!factors || factors.length === 0) return null;

  return (
    <div className="space-y-3 bg-blue-50 rounded-lg p-4">
      <p className="text-sm font-medium text-blue-800">Help us narrow your options:</p>
      {factors.map((factor, i) => (
        <div key={i} className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            {factor.label || factor.name}
            {factor.required && <span className="text-red-500 ml-0.5">*</span>}
          </label>
          {factor.type === 'select' && factor.options ? (
            <select className="rounded border border-gray-300 px-2 py-1.5 text-sm">
              <option value="">Select...</option>
              {factor.options.map((opt: string, j: number) => (
                <option key={j} value={opt}>{opt}</option>
              ))}
            </select>
          ) : factor.type === 'boolean' ? (
            <input type="checkbox" className="rounded border-gray-300" />
          ) : (
            <input
              type={factor.type === 'number' ? 'number' : 'text'}
              placeholder={factor.placeholder || ''}
              className="rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          )}
        </div>
      ))}
    </div>
  );
}
