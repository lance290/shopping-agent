'use client';

import { useState, useEffect } from 'react';
import { Loader2, Check, Search } from 'lucide-react';
import type { ChoiceFactorFormBlock } from '../../sdui/types';
import { useShoppingStore } from '../../store';
import { saveChoiceAnswerToDb, runSearchApiWithStatus, fetchSingleRowFromDb } from '../../utils/api';

export function ChoiceFactorForm({ factors }: ChoiceFactorFormBlock) {
  const activeRowId = useShoppingStore((s) => s.activeRowId);
  const rows = useShoppingStore((s) => s.rows);
  const updateRow = useShoppingStore((s) => s.updateRow);
  const setRowResults = useShoppingStore((s) => s.setRowResults);
  const setIsSearching = useShoppingStore((s) => s.setIsSearching);

  const row = rows.find((r) => r.id === activeRowId);

  // Local form state — seeded from existing choice_answers
  const [values, setValues] = useState<Record<string, string | number | boolean>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [searching, setSearching] = useState(false);

  // Seed from existing choice_answers when row changes
  useEffect(() => {
    if (!row?.choice_answers) return;
    try {
      const existing = typeof row.choice_answers === 'string'
        ? JSON.parse(row.choice_answers)
        : row.choice_answers;
      if (existing && typeof existing === 'object') {
        setValues((prev) => ({ ...existing, ...prev }));
      }
    } catch { /* ignore */ }
  }, [row?.id, row?.choice_answers]);

  if (!factors || factors.length === 0 || !row) return null;

  const handleChange = (name: string, value: string | number | boolean) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    setSaved((prev) => ({ ...prev, [name]: false }));
  };

  const handleBlur = async (name: string) => {
    const value = values[name];
    if (value === undefined || value === '') return;

    setSaving((prev) => ({ ...prev, [name]: true }));
    const allAnswers = { ...values };
    const success = await saveChoiceAnswerToDb(row.id, name, value, allAnswers);
    if (success) {
      updateRow(row.id, { choice_answers: JSON.stringify(allAnswers) });
      setSaved((prev) => ({ ...prev, [name]: true }));
    }
    setSaving((prev) => ({ ...prev, [name]: false }));
  };

  const handleSubmitAll = async () => {
    // Persist all values
    const allAnswers = { ...values };
    for (const factor of factors) {
      const val = allAnswers[factor.name];
      if (val !== undefined && val !== '') {
        await saveChoiceAnswerToDb(row.id, factor.name, val, allAnswers);
      }
    }
    updateRow(row.id, { choice_answers: JSON.stringify(allAnswers) });

    // Trigger search
    setSearching(true);
    setIsSearching(true);
    try {
      const res = await runSearchApiWithStatus(row.title, row.id);
      setRowResults(row.id, res.results, res.providerStatuses);
      const freshRow = await fetchSingleRowFromDb(row.id);
      if (freshRow) updateRow(row.id, freshRow);
    } finally {
      setSearching(false);
      setIsSearching(false);
    }
  };

  const formatLabel = (name: string) =>
    name.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

  return (
    <div className="space-y-3 bg-gold/5 rounded-lg p-4">
      <p className="text-sm font-medium text-ink">Help us narrow your options:</p>
      {factors.map((factor) => (
        <div key={factor.name} className="flex flex-col gap-1">
          <label className="text-xs font-medium text-ink-muted flex items-center gap-1.5">
            {factor.label || formatLabel(factor.name)}
            {factor.required && <span className="text-red-500">*</span>}
            {saving[factor.name] && <Loader2 size={10} className="animate-spin text-gold" />}
            {saved[factor.name] && <Check size={10} className="text-green-500" />}
          </label>
          {factor.type === 'select' && factor.options ? (
            <select
              value={(values[factor.name] as string) ?? ''}
              onChange={(e) => {
                handleChange(factor.name, e.target.value);
                // Persist selects immediately
                const val = e.target.value;
                if (val) {
                  setSaving((prev) => ({ ...prev, [factor.name]: true }));
                  const allAnswers = { ...values, [factor.name]: val };
                  saveChoiceAnswerToDb(row.id, factor.name, val, allAnswers).then((ok) => {
                    if (ok) {
                      updateRow(row.id, { choice_answers: JSON.stringify(allAnswers) });
                      setSaved((prev) => ({ ...prev, [factor.name]: true }));
                    }
                    setSaving((prev) => ({ ...prev, [factor.name]: false }));
                  });
                }
              }}
              className="rounded-lg border border-warm-grey px-2 py-1.5 text-sm bg-white focus:border-gold outline-none"
            >
              <option value="">Select...</option>
              {factor.options.map((opt: string) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          ) : factor.type === 'boolean' ? (
            <div className="flex gap-2">
              {['Yes', 'No'].map((opt) => {
                const boolVal = opt === 'Yes';
                const isSelected = values[factor.name] === boolVal;
                return (
                  <button
                    key={opt}
                    onClick={() => {
                      handleChange(factor.name, boolVal);
                      setSaving((prev) => ({ ...prev, [factor.name]: true }));
                      const allAnswers = { ...values, [factor.name]: boolVal };
                      saveChoiceAnswerToDb(row.id, factor.name, boolVal, allAnswers).then((ok) => {
                        if (ok) {
                          updateRow(row.id, { choice_answers: JSON.stringify(allAnswers) });
                          setSaved((prev) => ({ ...prev, [factor.name]: true }));
                        }
                        setSaving((prev) => ({ ...prev, [factor.name]: false }));
                      });
                    }}
                    className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold border transition-all ${
                      isSelected
                        ? 'bg-ink text-white border-ink'
                        : 'bg-white border-warm-grey text-ink hover:border-ink-muted'
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
              value={(values[factor.name] as string | number) ?? ''}
              onChange={(e) => handleChange(factor.name, factor.type === 'number' ? Number(e.target.value) : e.target.value)}
              onBlur={() => handleBlur(factor.name)}
              placeholder={factor.placeholder || ''}
              className="rounded-lg border border-warm-grey px-2 py-1.5 text-sm bg-white focus:border-gold outline-none"
            />
          )}
        </div>
      ))}
      <button
        onClick={handleSubmitAll}
        disabled={searching}
        className="w-full mt-2 py-2 px-3 bg-gold hover:bg-gold-dark text-navy text-sm font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {searching ? (
          <><Loader2 size={14} className="animate-spin" /> Searching...</>
        ) : (
          <><Search size={14} /> Update & Search</>
        )}
      </button>
    </div>
  );
}
