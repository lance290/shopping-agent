'use client';

import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Copy, Check, Mail, Building2, User } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { parseChoiceAnswers, useShoppingStore } from '../store';
import { saveOutreachToDb } from '../utils/api';
import { getMe } from '../utils/auth';

interface VendorContactModalProps {
  isOpen: boolean;
  onClose: () => void;
  rowId: number;
  rowTitle: string;
  rowChoiceAnswers?: string;
  serviceCategory?: string;
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
  serviceCategory,
  vendorName,
  vendorCompany,
  vendorEmail,
}: VendorContactModalProps) {
  const isAviation = serviceCategory === 'private_aviation';
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

  const defaultOutreach = useMemo(() => {
    const existingOutreach = (existingAnswers as any)?.outreach || {};
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
    const timeExtracted = fields.time_fixed || extract('wheels_up', 'wheels_up_time', 'departure_time', 'time', 'wheels_up_time_leg1');
    const tripType = fields.trip_type || extract('trip_type') || '';
    const returnFrom = fields.return_from || extract('return_from', 'return_origin', 'return_departure');
    const returnTo = fields.return_to || extract('return_to', 'return_destination', 'return_arrival');
    const returnDate = fields.return_date || extract('return_date', 'return_dates');
    const returnTime = fields.return_time || extract('return_time', 'return_wheels_up', 'return_departure_time');
    const returnPax = fields.return_passengers || extract('return_passengers', 'return_pax', 'pax_return');
    const passengerNames = fields.passenger_names || extract('passenger_names', 'passengers_outbound', 'attendees', 'guest_list');
    const returnPassengerNames = fields.return_passenger_names || extract('return_passenger_names', 'passengers_return', 'return_attendees', 'return_guest_list');
    const replyToEmail = fields.reply_to_email || extract('reply_to_email', 'reply_to', 'email') || '';
    const aircraftClass = fields.aircraft_class || extract('aircraft_class', 'aircraft_type', 'aircraft', 'jet_size', 'jet_type', 'aircraft_category');
    const requirements = fields.requirements || extract('requirements', 'special_requirements', 'wifi', 'connectivity', 'notes_for_vendor');

    const subjectTemplate = typeof existingOutreach?.subject_template === 'string'
      ? existingOutreach.subject_template
      : 'Quote request — {from} to {to} on {date}';

    const bodyTemplate = typeof existingOutreach?.body_template === 'string'
      ? existingOutreach.body_template
      : null; // Will use getDefaultBodyTemplate() at init time

    return {
      persona_name: personaName,
      persona_role: personaRole,
      subject_template: subjectTemplate,
      body_template: bodyTemplate,
      fields: {
        from_airport: from,
        to_airport: to,
        date,
        time_mode: timeExtracted ? 'fixed' : (fields.time_mode || 'window'),
        time_fixed: timeExtracted || fields.time_fixed || '',
        time_earliest: fields.time_earliest || '',
        time_latest: fields.time_latest || '',
        passengers: pax ? Number(pax) || pax : '',
        notes: fields.notes || '',
        trip_type: tripType,
        return_from: returnFrom,
        return_to: returnTo,
        return_date: returnDate,
        return_time: returnTime,
        return_passengers: returnPax,
        passenger_names: passengerNames,
        return_passenger_names: returnPassengerNames,
        reply_to_email: replyToEmail,
        aircraft_class: aircraftClass,
        requirements: requirements,
      },
    };
  }, [existingAnswers]);

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
  const [bodyEdited, setBodyEdited] = useState<string | null>(null); // null = use template
  const [tripType, setTripType] = useState<'one-way' | 'round-trip'>('one-way');
  const [returnFrom, setReturnFrom] = useState<string>('');
  const [returnTo, setReturnTo] = useState<string>('');
  const [returnDate, setReturnDate] = useState<string>('');
  const [returnTime, setReturnTime] = useState<string>('');
  const [returnPassengers, setReturnPassengers] = useState<string>('');
  const [passengerNames, setPassengerNames] = useState<string>('');
  const [returnPassengerNames, setReturnPassengerNames] = useState<string>('');
  const [replyToEmail, setReplyToEmail] = useState<string>('');
  const [aircraftClass, setAircraftClass] = useState<string>('');
  const [requirements, setRequirements] = useState<string>('');
  const [copiedBody, setCopiedBody] = useState(false);

  const getDefaultBodyTemplate = (tt: string) => {
    if (isAviation && tt === 'round-trip') {
      return `Hi {provider},

I'm reaching out on behalf of my client regarding a charter quote:

LEG 1 — OUTBOUND
Route: {from} → {to}
Date: {date}
Wheels up: {time}
Passengers: {pax}
{passenger_names}

LEG 2 — RETURN
Route: {return_from} → {return_to}
Date: {return_date}
Wheels up: {return_time}
Passengers: {return_pax}
{return_passenger_names}

AIRCRAFT
Category: {aircraft_class}
Requirements: {requirements}

Please include in your quote:
• All-in price (incl. taxes, fuel, landing/handling, FBO, crew overnight)
• Tail number + operator (Part 135 certificate holder)
• Wi-Fi system type and whether Starlink is installed
• Cancellation/change policy
• Quote validity window

Please send your quote to: {reply_to_email}

Thanks,
{persona_name}
{persona_role}`;
    }
    if (isAviation) {
      return `Hi {provider},

I'm reaching out on behalf of my client regarding a charter quote:

Route: {from} → {to}
Date: {date}
Wheels up: {time}
Passengers: {pax}
{passenger_names}

AIRCRAFT
Category: {aircraft_class}
Requirements: {requirements}

Please include in your quote:
• All-in price (incl. taxes, fuel, landing/handling, FBO, crew overnight)
• Tail number + operator (Part 135 certificate holder)
• Wi-Fi system type and whether Starlink is installed
• Cancellation/change policy
• Quote validity window

Please send your quote to: {reply_to_email}

Thanks,
{persona_name}
{persona_role}`;
    }
    if (tt === 'round-trip') {
      return `Hi {provider},

I'm reaching out on behalf of my client regarding a quote:

LEG 1 — OUTBOUND
Route: {from} → {to}
Date: {date}
Departure: {time}
Passengers: {pax}
{passenger_names}

LEG 2 — RETURN
Route: {return_from} → {return_to}
Date: {return_date}
Departure: {return_time}
Passengers: {return_pax}
{return_passenger_names}

Please include in your quote:
• All-in price
• Cancellation/change policy
• Quote validity window

Please send your quote to: {reply_to_email}

Thanks,
{persona_name}
{persona_role}`;
    }
    return `Hi {provider},

I'm reaching out on behalf of my client regarding a quote:
Route: {from} → {to}
Date: {date}
Departure: {time}
Passengers: {pax}
{passenger_names}

Please include in your quote:
• All-in price
• Cancellation/change policy
• Quote validity window

Please send your quote to: {reply_to_email}

Thanks,
{persona_name}
{persona_role}`;
  };

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const d = defaultOutreach;
    const f = d.fields;
    const resolvedTripType = f.trip_type === 'round-trip' ? 'round-trip' : 'one-way';

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
    setTripType(resolvedTripType);
    setReturnFrom(f.return_from || '');
    setReturnTo(f.return_to || '');
    setReturnDate(f.return_date || '');
    setReturnTime(f.return_time || '');
    setReturnPassengers(String(f.return_passengers ?? ''));
    setPassengerNames(f.passenger_names || '');
    setReturnPassengerNames(f.return_passenger_names || '');
    setAircraftClass(f.aircraft_class || '');
    setRequirements(f.requirements || '');

    // Default reply-to to logged-in user's email if not already set
    if (f.reply_to_email) {
      setReplyToEmail(f.reply_to_email);
    } else {
      getMe().then(user => {
        if (user?.email) setReplyToEmail(user.email);
      }).catch(() => {});
    }

    // Store raw templates for re-rendering
    setSubjectTemplateRaw(d.subject_template || 'Quote request — {from} to {to} on {date}');
    setBodyTemplateRaw(d.body_template || getDefaultBodyTemplate(resolvedTripType));
    setBodyEdited(null); // Reset to template mode when modal opens

  // eslint-disable-next-line react-hooks/exhaustive-deps
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
      .replaceAll('{passenger_names}', passengerNames ? `Names: ${passengerNames}` : '')
      .replaceAll('{return_from}', (returnFrom || toAirport || '').toUpperCase())
      .replaceAll('{return_to}', (returnTo || fromAirport || '').toUpperCase())
      .replaceAll('{return_date}', returnDate || '')
      .replaceAll('{return_time}', returnTime || '')
      .replaceAll('{return_pax}', returnPassengers || passengers || '')
      .replaceAll('{return_passenger_names}', returnPassengerNames ? `Names: ${returnPassengerNames}` : '')
      .replaceAll('{reply_to_email}', replyToEmail || '')
      .replaceAll('{aircraft_class}', aircraftClass || '')
      .replaceAll('{requirements}', requirements || '')
      .replaceAll('{persona_name}', personaName)
      .replaceAll('{persona_role}', personaRole)
      .replaceAll('{row_title}', rowTitle);
  };

  const subjectRendered = renderTemplate(subjectTemplateRaw);
  const bodyRendered = bodyEdited !== null ? bodyEdited : renderTemplate(bodyTemplateRaw);

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
        trip_type: tripType,
        return_from: returnFrom,
        return_to: returnTo,
        return_date: returnDate,
        return_time: returnTime,
        return_passengers: returnPassengers ? Number(returnPassengers) : null,
        passenger_names: passengerNames,
        return_passenger_names: returnPassengerNames,
        reply_to_email: replyToEmail,
        aircraft_class: aircraftClass,
        requirements: requirements,
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

      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden max-h-[85vh] flex flex-col">
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

        <div className="p-6 space-y-4 overflow-y-auto flex-1">
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
                onChange={(e) => setBodyEdited(e.target.value)}
                rows={14}
                className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none resize-y"
              />
            </div>

            <div>
              <div className="text-xs text-onyx-muted mb-1">Trip type</div>
              <select
                value={tripType}
                onChange={(e) => {
                  const tt = e.target.value as 'one-way' | 'round-trip';
                  setTripType(tt);
                  if (bodyEdited === null) setBodyTemplateRaw(getDefaultBodyTemplate(tt));
                }}
                className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
              >
                <option value="one-way">One-way</option>
                <option value="round-trip">Round-trip</option>
              </select>
            </div>

            <div className="text-[10px] uppercase tracking-wider text-onyx-muted font-semibold mt-2">{isAviation ? 'Leg 1 — Outbound' : 'Details'}</div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="text-xs text-onyx-muted mb-1">{isAviation ? 'From (airport)' : 'Origin'}</div>
                <input
                  value={fromAirport}
                  onChange={(e) => setFromAirport(e.target.value.toUpperCase())}
                  placeholder={isAviation ? 'BNA' : 'Origin'}
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
              <div>
                <div className="text-xs text-onyx-muted mb-1">{isAviation ? 'To (airport)' : 'Destination'}</div>
                <input
                  value={toAirport}
                  onChange={(e) => setToAirport(e.target.value.toUpperCase())}
                  placeholder={isAviation ? 'FWA' : 'Destination'}
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <div className="text-xs text-onyx-muted mb-1">Date</div>
                <input
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  placeholder="2026-02-13"
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
              <div>
                <div className="text-xs text-onyx-muted mb-1">{isAviation ? 'Wheels up' : 'Time'}</div>
                <input
                  value={timeFixed}
                  onChange={(e) => { setTimeFixed(e.target.value); setTimeMode('fixed'); }}
                  placeholder="2:00 PM CT"
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
              <div>
                <div className="text-xs text-onyx-muted mb-1">{isAviation ? 'Passengers' : 'Attendees'}</div>
                <input
                  value={passengers}
                  onChange={(e) => setPassengers(e.target.value)}
                  placeholder="2"
                  className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                />
              </div>
            </div>

            <div>
              <div className="text-xs text-onyx-muted mb-1">{isAviation ? 'Passenger names' : 'Attendee names'}</div>
              <input
                value={passengerNames}
                onChange={(e) => setPassengerNames(e.target.value)}
                placeholder={isAviation ? 'e.g. Wendy Connors, Margaret Oppelt' : 'Names (comma-separated)'}
                className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
              />
            </div>

            {tripType === 'round-trip' && (
              <>
                <div className="text-[10px] uppercase tracking-wider text-onyx-muted font-semibold mt-3 pt-3 border-t border-warm-grey/40">{isAviation ? 'Leg 2 — Return' : 'Return'}</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <div className="text-xs text-onyx-muted mb-1">{isAviation ? 'From (airport)' : 'Origin'}</div>
                    <input
                      value={returnFrom}
                      onChange={(e) => setReturnFrom(e.target.value.toUpperCase())}
                      placeholder={toAirport || (isAviation ? 'FWA' : 'Return origin')}
                      className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                    />
                  </div>
                  <div>
                    <div className="text-xs text-onyx-muted mb-1">{isAviation ? 'To (airport)' : 'Destination'}</div>
                    <input
                      value={returnTo}
                      onChange={(e) => setReturnTo(e.target.value.toUpperCase())}
                      placeholder={fromAirport || (isAviation ? 'BNA' : 'Return dest')}
                      className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <div className="text-xs text-onyx-muted mb-1">Return date</div>
                    <input
                      value={returnDate}
                      onChange={(e) => setReturnDate(e.target.value)}
                      placeholder="2026-02-15"
                      className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                    />
                  </div>
                  <div>
                    <div className="text-xs text-onyx-muted mb-1">{isAviation ? 'Wheels up' : 'Time'}</div>
                    <input
                      value={returnTime}
                      onChange={(e) => setReturnTime(e.target.value)}
                      placeholder="2:30 PM ET"
                      className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                    />
                  </div>
                  <div>
                    <div className="text-xs text-onyx-muted mb-1">{isAviation ? 'Passengers' : 'Attendees'}</div>
                    <input
                      value={returnPassengers}
                      onChange={(e) => setReturnPassengers(e.target.value)}
                      placeholder={passengers || '3'}
                      className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                    />
                  </div>
                </div>
                <div>
                  <div className="text-xs text-onyx-muted mb-1">{isAviation ? 'Return passenger names' : 'Return attendee names'}</div>
                  <input
                    value={returnPassengerNames}
                    onChange={(e) => setReturnPassengerNames(e.target.value)}
                    placeholder={isAviation ? 'e.g. Timothy Connors, Wendy Connors, Margaret Oppelt' : 'Names (comma-separated)'}
                    className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                  />
                </div>
              </>
            )}

            {isAviation && (
              <div className="pt-2 border-t border-warm-grey/40">
                <div className="text-[10px] uppercase tracking-wider text-onyx-muted font-semibold mb-2">Aircraft</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <div className="text-xs text-onyx-muted mb-1">Aircraft category</div>
                    <input
                      value={aircraftClass}
                      onChange={(e) => setAircraftClass(e.target.value)}
                      placeholder="e.g. Light jet"
                      className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                    />
                  </div>
                  <div>
                    <div className="text-xs text-onyx-muted mb-1">Requirements</div>
                    <input
                      value={requirements}
                      onChange={(e) => setRequirements(e.target.value)}
                      placeholder="e.g. Wi-Fi (Starlink preferred)"
                      className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
                    />
                  </div>
                </div>
              </div>
            )}

            <div className="pt-2 border-t border-warm-grey/40">
              <div className="text-xs text-onyx-muted mb-1">Replies to (email)</div>
              <input
                value={replyToEmail}
                onChange={(e) => setReplyToEmail(e.target.value)}
                placeholder="your@email.com"
                className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none"
              />
            </div>

            <div>
              <div className="text-xs text-onyx-muted mb-1">Notes (optional)</div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-white border border-warm-grey/60 rounded-lg text-xs text-gray-900 focus:border-agent-blurple transition-colors outline-none resize-y"
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
            variant="secondary"
            onClick={async () => {
              const subject = subjectRendered.trim();
              let body = bodyRendered.trim();
              if (notes?.trim()) body = `${body}\n\nNotes:\n${notes.trim()}`;
              await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
              setCopiedBody(true);
              setTimeout(() => setCopiedBody(false), 2000);
            }}
            className="flex-1 gap-2"
          >
            {copiedBody ? (
              <><Check size={16} className="text-green-600" />Copied!</>
            ) : (
              <><Copy size={16} />Copy Body</>
            )}
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
