'use client';

import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Copy, Check, Mail, Building2, User } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { parseChoiceAnswers, useShoppingStore } from '../store';
import { saveOutreachToDb } from '../utils/api';

interface VendorContactModalProps {
  isOpen: boolean;
  onClose: () => void;
  rowId: number;
  rowTitle: string;
  rowChoiceAnswers?: string;
  vendorName: string;
  vendorCompany: string;
  vendorEmail: string;
}

export default function VendorContactModal({
  isOpen,
  onClose,
  rowId,
  rowTitle,
  rowChoiceAnswers,
  vendorName,
  vendorCompany,
  vendorEmail,
}: VendorContactModalProps) {
  const [copied, setCopied] = useState(false);
  const [mounted, setMounted] = useState(false);
  const updateRow = useShoppingStore((s) => s.updateRow);

  const existingAnswers = useMemo(() => {
    if (typeof rowChoiceAnswers === 'string' && rowChoiceAnswers.trim().length > 0) {
      try {
        return JSON.parse(rowChoiceAnswers);
      } catch {
        return {};
      }
    }
    return parseChoiceAnswers({ choice_answers: rowChoiceAnswers } as any);
  }, [rowChoiceAnswers]);

  const safetyStatus = (existingAnswers as any)?.safety_status || 'safe';
  const safetyReason = (existingAnswers as any)?.safety_reason || '';
  const [confirmedSafe, setConfirmedSafe] = useState(false);

  const existingOutreach = (existingAnswers as any)?.outreach || {};

  const defaultOutreach = useMemo(() => {
    const personaName = typeof existingOutreach?.persona_name === 'string' ? existingOutreach.persona_name : 'Betty';
    const personaRole = typeof existingOutreach?.persona_role === 'string' ? existingOutreach.persona_role : 'Executive Assistant, BuyAnything';
    const fields = typeof existingOutreach?.fields === 'object' && existingOutreach.fields ? existingOutreach.fields : {};
    
    // Attempt to extract defaults from row answers if not explicit in outreach fields
    const answers = existingAnswers as Record<string, any>;
    const extract = (...keys: string[]) => {
      for (const k of keys) {
        if (answers[k]) return String(answers[k]);
      }
      return '';
    };

    const from = fields.from_airport || extract('from', 'origin', 'departure', 'from_airport', 'departure_airport');
    const to = fields.to_airport || extract('to', 'destination', 'arrival', 'to_airport', 'arrival_airport');
    const date = fields.date || extract('date', 'dates', 'when', 'departure_date', 'travel_date');
    const pax = typeof fields.passengers === 'number' ? fields.passengers : extract('passengers', 'pax', 'travelers', 'people', 'seats');

    const subjectTemplate = typeof existingOutreach?.subject_template === 'string'
      ? existingOutreach.subject_template
      : 'Charter request — {from} to {to} on {date}';

    const bodyTemplate = typeof existingOutreach?.body_template === 'string'
      ? existingOutreach.body_template
      : `Hi {provider},\n\nI’m reaching out on behalf of my boss. We’re looking to arrange a private charter:\nRoute: {from} → {to}\nDate: {date}\nWheels up: {time}\nPassengers: {pax}\n\nAre you able to quote this? If so, what availability/pricing do you have?\n\nThanks,\n{persona_name}\n{persona_role}`;

    return {
      persona_name: personaName,
      persona_role: personaRole,
      subject_template: subjectTemplate,
      body_template: bodyTemplate,
      fields: {
        from_airport: from,
        to_airport: to,
        date,
        time_mode: fields.time_mode || 'window',
        time_fixed: fields.time_fixed || '',
        time_earliest: fields.time_earliest || '',
        time_latest: fields.time_latest || '',
        passengers: pax ? Number(pax) || pax : '',
        notes: fields.notes || '',
      },
    };
  }, [existingOutreach, existingAnswers]);

  const [personaName, setPersonaName] = useState<string>('Betty');
  const [personaRole, setPersonaRole] = useState<string>('Executive Assistant, BuyAnything');
  const [subjectTemplateRaw, setSubjectTemplateRaw] = useState<string>('');
  const [bodyTemplateRaw, setBodyTemplateRaw] = useState<string>('');
  const [fromAirport, setFromAirport] = useState<string>('');
  const [toAirport, setToAirport] = useState<string>('');
  const [date, setDate] = useState<string>('');
  const [timeMode, setTimeMode] = useState<'fixed' | 'window'>('window');
  const [timeFixed, setTimeFixed] = useState<string>('');
  const [timeEarliest, setTimeEarliest] = useState<string>('');
  const [timeLatest, setTimeLatest] = useState<string>('');
  const [passengers, setPassengers] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const d = defaultOutreach;
    const f = d.fields;

    setPersonaName(d.persona_name || 'Betty');
    setPersonaRole(d.persona_role || 'Executive Assistant, BuyAnything');
    setFromAirport(f.from_airport || '');
    setToAirport(f.to_airport || '');
    setDate(f.date || '');
    setTimeMode((f.time_mode === 'fixed' ? 'fixed' : 'window') as any);
    setTimeFixed(f.time_fixed || '');
    setTimeEarliest(f.time_earliest || '');
    setTimeLatest(f.time_latest || '');
    setPassengers(String(f.passengers ?? ''));
    setNotes(f.notes || '');

    // Store raw templates for re-rendering
    setSubjectTemplateRaw(d.subject_template || 'Charter request — {from} to {to} on {date}');
    setBodyTemplateRaw(d.body_template || `Hi {provider},\n\nI'm reaching out on behalf of my boss. We're looking to arrange a private charter:\nRoute: {from} → {to}\nDate: {date}\nWheels up: {time}\nPassengers: {pax}\n\nAre you able to quote this? If so, what availability/pricing do you have?\n\nThanks,\n{persona_name}\n{persona_role}`);

  }, [isOpen, defaultOutreach]);

  // Re-render templates whenever fields change
  const renderTemplate = (tpl: string) => {
    const time = timeMode === 'fixed'
      ? (timeFixed || '')
      : ((timeEarliest || timeLatest) ? `${timeEarliest || '??'}-${timeLatest || '??'}` : '');

    return tpl
      .replaceAll('{provider}', vendorCompany)
      .replaceAll('{from}', (fromAirport || '').toUpperCase())
      .replaceAll('{to}', (toAirport || '').toUpperCase())
      .replaceAll('{date}', date || '')
      .replaceAll('{time}', time)
      .replaceAll('{pax}', passengers || '')
      .replaceAll('{persona_name}', personaName)
      .replaceAll('{persona_role}', personaRole)
      .replaceAll('{row_title}', rowTitle);
  };

  const subjectRendered = renderTemplate(subjectTemplateRaw);
  const bodyRendered = renderTemplate(bodyTemplateRaw);

  if (!isOpen || !mounted) return null;

  const handleCopyEmail = async () => {
    try {
      await navigator.clipboard.writeText(vendorEmail);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy email:', err);
    }
  };

  const handleEmailClick = () => {
    const subject = subjectRendered.trim();
    let body = bodyRendered.trim();
    if (notes && notes.trim().length > 0) {
      body = `${body}\n\nNotes:\n${notes.trim()}`;
    }

    const params = new URLSearchParams();
    if (subject) params.set('subject', subject);
    if (body) params.set('body', body);
    window.location.href = `mailto:${encodeURIComponent(vendorEmail)}?${params.toString()}`;
  };

  const handleSaveTemplate = async () => {
    setSaving(true);
    const outreach = {
      persona_name: personaName,
      persona_role: personaRole,
      subject_template: subjectTemplateRaw,
      body_template: bodyTemplateRaw,
      fields: {
        from_airport: fromAirport,
        to_airport: toAirport,
        date,
        time_mode: timeMode,
        time_fixed: timeFixed,
        time_earliest: timeEarliest,
        time_latest: timeLatest,
        passengers: passengers ? Number(passengers) : null,
        notes,
      },
    };

    const ok = await saveOutreachToDb(rowId, outreach, existingAnswers as any);
    if (ok) {
      const nextAnswers = { ...(existingAnswers as any), outreach };
      updateRow(rowId, { choice_answers: JSON.stringify(nextAnswers) });
    }
    setSaving(false);
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Contact Provider</h2>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {safetyStatus === 'blocked' && (
          <div className="bg-red-50 border-b border-red-200 px-6 py-4">
            <div className="flex gap-3">
              <div className="text-red-600 font-semibold">Request Blocked</div>
            </div>
            <div className="text-sm text-red-700 mt-1">
              {safetyReason || "This request violates our safety policies and cannot be processed."}
            </div>
          </div>
        )}

        {safetyStatus === 'needs_review' && (
          <div className="bg-amber-50 border-b border-amber-200 px-6 py-4">
            <div className="text-amber-800 font-medium mb-2">Safety Review Required</div>
            <div className="text-sm text-amber-700 mb-3">
              {safetyReason || "This request involves a sensitive category. Please confirm this is a legitimate request."}
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input 
                type="checkbox" 
                checked={confirmedSafe}
                onChange={(e) => setConfirmedSafe(e.target.checked)}
                className="rounded border-amber-400 text-amber-600 focus:ring-amber-500"
              />
              <span className="text-sm text-amber-900 font-medium">I confirm this request is legal and non-exploitative.</span>
            </label>
          </div>
        )}

        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <div className="text-[10px] uppercase tracking-wider text-onyx-muted font-semibold">Message</div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="text-xs text-onyx-muted mb-1">From (EA name)</div>
                <input
                  value={personaName}
                  onChange={(e) => setPersonaName(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
              <div>
                <div className="text-xs text-onyx-muted mb-1">Role</div>
                <input
                  value={personaRole}
                  onChange={(e) => setPersonaRole(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
            </div>

            <div>
              <div className="text-xs text-onyx-muted mb-1">Subject</div>
              <input
                value={subjectRendered}
                readOnly
                className="w-full px-3 py-2 bg-gray-50 border border-warm-grey/60 rounded-lg text-xs text-gray-900 outline-none"
              />
            </div>

            <div>
              <div className="text-xs text-onyx-muted mb-1">Email body</div>
              <textarea
                value={bodyRendered}
                readOnly
                rows={6}
                className="w-full px-3 py-2 bg-gray-50 border border-warm-grey/60 rounded-lg text-xs text-gray-900 outline-none resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="text-xs text-onyx-muted mb-1">From (airport code)</div>
                <input
                  value={fromAirport}
                  onChange={(e) => setFromAirport(e.target.value.toUpperCase())}
                  placeholder="BNA"
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
              <div>
                <div className="text-xs text-onyx-muted mb-1">To (airport code)</div>
                <input
                  value={toAirport}
                  onChange={(e) => setToAirport(e.target.value.toUpperCase())}
                  placeholder="TEB"
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="text-xs text-onyx-muted mb-1">Date</div>
                <input
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  placeholder="2026-02-10"
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
              <div>
                <div className="text-xs text-onyx-muted mb-1">Passengers</div>
                <input
                  value={passengers}
                  onChange={(e) => setPassengers(e.target.value)}
                  placeholder="4"
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <div className="text-xs text-onyx-muted mb-1">Time mode</div>
                <select
                  value={timeMode}
                  onChange={(e) => setTimeMode(e.target.value as any)}
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                >
                  <option value="window">Window</option>
                  <option value="fixed">Fixed</option>
                </select>
              </div>
              <div>
                <div className="text-xs text-onyx-muted mb-1">Earliest</div>
                <input
                  disabled={timeMode !== 'window'}
                  value={timeEarliest}
                  onChange={(e) => setTimeEarliest(e.target.value)}
                  placeholder="09:00"
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none disabled:opacity-50"
                />
              </div>
              <div>
                <div className="text-xs text-onyx-muted mb-1">Latest</div>
                <input
                  disabled={timeMode !== 'window'}
                  value={timeLatest}
                  onChange={(e) => setTimeLatest(e.target.value)}
                  placeholder="12:00"
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none disabled:opacity-50"
                />
              </div>
            </div>

            {timeMode === 'fixed' && (
              <div>
                <div className="text-xs text-onyx-muted mb-1">Wheels up (fixed)</div>
                <input
                  value={timeFixed}
                  onChange={(e) => setTimeFixed(e.target.value)}
                  placeholder="10:30"
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
            )}

            <div>
              <div className="text-xs text-onyx-muted mb-1">Notes (optional)</div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none resize-none"
              />
            </div>
          </div>

          <div className="flex items-center gap-3 text-ink">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <Building2 size={20} className="text-blue-600" />
            </div>
            <div>
              <div className="text-sm text-ink-muted">Company</div>
              <div className="font-semibold">{vendorCompany}</div>
            </div>
          </div>

          <div className="flex items-center gap-3 text-ink">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <User size={20} className="text-blue-600" />
            </div>
            <div>
              <div className="text-sm text-ink-muted">Contact</div>
              <div className="font-semibold">{vendorName}</div>
            </div>
          </div>

          <div className="flex items-center gap-3 text-ink">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <Mail size={20} className="text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-ink-muted">Email</div>
              <div className="font-semibold truncate">{vendorEmail}</div>
            </div>
          </div>
        </div>

        <div className="px-6 pb-6 flex gap-3">
          <Button
            variant="secondary"
            onClick={handleCopyEmail}
            className="flex-1 gap-2"
          >
            {copied ? (
              <>
                <Check size={16} className="text-green-600" />
                Copied!
              </>
            ) : (
              <>
                <Copy size={16} />
                Copy Email
              </>
            )}
          </Button>
          <Button
            variant="secondary"
            onClick={handleSaveTemplate}
            className="flex-1 gap-2"
            disabled={saving}
          >
            Save for this row
          </Button>
          <Button
            variant="primary"
            onClick={handleEmailClick}
            className="flex-1 gap-2"
            disabled={safetyStatus === 'blocked' || (safetyStatus === 'needs_review' && !confirmedSafe)}
          >
            <Mail size={16} />
            Open Email App
          </Button>
        </div>
      </div>
    </div>,
    document.body
  );
}
