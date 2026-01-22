'use client';

import { useState, useRef, ChangeEvent, useEffect } from 'react';
import { X, Bug, Upload, Image as ImageIcon, Trash2, Check, AlertCircle } from 'lucide-react';
import { useShoppingStore } from '../store';
import { Button } from '../../components/ui/Button';
import { cn } from '../../utils/cn';
import { submitBugReport } from '../utils/api';
import { getDiagnostics, redactDiagnostics, addBreadcrumb } from '../utils/diagnostics';

type Severity = 'low' | 'medium' | 'high' | 'blocking';
type Category = 'ui' | 'data' | 'auth' | 'payments' | 'performance' | 'other';

export default function ReportBugModal() {
  const isOpen = useShoppingStore((state) => state.isReportBugModalOpen);
  const close = useShoppingStore((state) => state.setReportBugModalOpen);

  // Form State
  const [notes, setNotes] = useState('');
  const [expected, setExpected] = useState('');
  const [actual, setActual] = useState('');
  const [severity, setSeverity] = useState<Severity>('low');
  const [category, setCategory] = useState<Category>('ui');
  const [includeDiagnostics, setIncludeDiagnostics] = useState(true);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedId, setSubmittedId] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      addBreadcrumb({
        type: 'ui',
        message: 'Opened Report Bug modal',
        timestamp: new Date().toISOString(),
      });
    }
  }, [isOpen]);

  // Reset form when opening/closing would be ideal, but for now we rely on component unmount if conditionally rendered?
  // Actually it is conditionally rendered in page.tsx via store flag? No, it's always rendered but returns null if !isOpen.
  // We should reset state when closing.
  const handleClose = () => {
    close(false);
    // Reset state after a delay to avoid flicker
    setTimeout(() => {
        setNotes('');
        setExpected('');
        setActual('');
        setSeverity('low');
        setCategory('ui');
        setIncludeDiagnostics(true);
        setAttachments([]);
        setIsSubmitting(false);
        setSubmittedId(null);
    }, 200);
  };

  if (!isOpen) return null;

  const isValid = notes.trim().length > 0 && attachments.length > 0;

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setAttachments(prev => [...prev, ...newFiles]);
      if (newFiles.length > 0) {
        addBreadcrumb({
          type: 'ui',
          message: `Attached ${newFiles.length} file(s)` ,
          details: newFiles.map(file => file.name),
          timestamp: new Date().toISOString(),
        });
      }
    }
    // Reset value so same file can be selected again if needed
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!isValid || isSubmitting) return;
    
    setIsSubmitting(true);
    addBreadcrumb({
      type: 'ui',
      message: 'Submitted bug report',
      timestamp: new Date().toISOString(),
    });
    
    try {
        const formData = new FormData();
        formData.append('notes', notes);
        formData.append('expected', expected);
        formData.append('actual', actual);
        formData.append('severity', severity);
        formData.append('category', category);
        formData.append('includeDiagnostics', String(includeDiagnostics));
        
        // Append attachments
        attachments.forEach(file => {
            formData.append('attachments', file);
        });
        
        // Append diagnostics blob if enabled (best-effort)
        if (includeDiagnostics) {
            try {
                const diagnosticsPayload = redactDiagnostics(getDiagnostics());
                formData.append('diagnostics', JSON.stringify(diagnosticsPayload));
            } catch (diagError) {
                console.warn('Diagnostics capture failed:', diagError);
            }
        }

        const result = await submitBugReport(formData);
        
        if (result && result.id) {
            setSubmittedId(result.id);
        } else {
            alert('Failed to submit bug report. Please try again.');
            setIsSubmitting(false);
        }
    } catch (err) {
        console.error('Submit error:', err);
        alert('An error occurred while submitting.');
        setIsSubmitting(false);
    }
  };

  const inputClasses = "w-full bg-white border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors outline-none py-2.5 px-4 text-sm text-gray-900 placeholder:text-gray-400 rounded-xl resize-y";
  const labelClasses = "block text-xs font-medium text-onyx mb-1.5";

  if (submittedId) {
      return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-warm-grey overflow-hidden flex flex-col p-8 items-center text-center animate-in zoom-in-95">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center text-green-600 mb-4">
                    <Check size={32} />
                </div>
                <h2 className="text-xl font-semibold text-onyx mb-2">Bug Reported!</h2>
                <p className="text-sm text-onyx-muted mb-6">
                    Thanks for your feedback. Your report ID is <strong className="text-onyx font-mono">{submittedId}</strong>.
                </p>
                <Button onClick={handleClose} className="w-full">
                    Done
                </Button>
            </div>
        </div>
      );
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div 
        className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-warm-grey overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-bug-title"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-warm-grey/50 flex justify-between items-center bg-warm-light/50 shrink-0">
          <div className="flex items-center gap-2 text-onyx">
            <div className="p-1.5 bg-rose-100 text-rose-600 rounded-lg">
              <Bug size={18} />
            </div>
            <div>
              <h2 id="report-bug-title" className="font-medium text-base">Report a Bug</h2>
              <p className="text-xs text-onyx-muted">Help us improve by sharing what you found.</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClose}
            className="text-onyx-muted hover:text-onyx -mr-2"
            aria-label="Close"
          >
            <X size={20} />
          </Button>
        </div>

        {/* Scrollable Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          
          {/* 1. Screenshots (Required) */}
          <div>
            <div className="flex justify-between items-baseline mb-2">
              <label className={labelClasses}>Screenshots <span className="text-rose-500">*</span></label>
              <span className="text-[10px] text-onyx-muted">{attachments.length} attached</span>
            </div>
            
            <div className="grid grid-cols-4 gap-3">
              {attachments.map((file, idx) => (
                <div key={idx} className="relative group aspect-square rounded-xl border border-warm-grey overflow-hidden bg-warm-light">
                  {file.type.startsWith('image/') ? (
                    <img 
                      src={URL.createObjectURL(file)} 
                      alt="Preview" 
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-onyx-muted">
                      <ImageIcon size={24} />
                    </div>
                  )}
                  <button
                    onClick={() => removeAttachment(idx)}
                    className="absolute top-1 right-1 p-1 bg-black/50 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-rose-500"
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
              
              <button
                onClick={() => fileInputRef.current?.click()}
                className="aspect-square rounded-xl border-2 border-dashed border-warm-grey hover:border-agent-blurple hover:bg-agent-blurple/5 transition-colors flex flex-col items-center justify-center gap-2 text-onyx-muted hover:text-agent-blurple"
              >
                <Upload size={20} />
                <span className="text-xs font-medium">Add Image</span>
              </button>
            </div>
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              multiple
              accept="image/*"
              onChange={handleFileSelect}
            />
            {attachments.length === 0 && (
              <p className="text-[11px] text-rose-500 mt-1.5 flex items-center gap-1">
                <AlertCircle size={12} /> At least one screenshot is required
              </p>
            )}
          </div>

          {/* 2. Notes (Required) */}
          <div>
            <label htmlFor="notes" className={labelClasses}>What happened? <span className="text-rose-500">*</span></label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Describe the issue... (e.g. 'I clicked the buy button but nothing happened')"
              className={cn(inputClasses, "min-h-[80px]")}
              required
            />
          </div>

          {/* 3. Optional Fields (Expected / Actual) */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="expected" className={labelClasses}>Expected behavior</label>
              <textarea
                id="expected"
                value={expected}
                onChange={(e) => setExpected(e.target.value)}
                placeholder="What should have happened?"
                className={cn(inputClasses, "min-h-[60px]")}
              />
            </div>
            <div>
              <label htmlFor="actual" className={labelClasses}>Actual behavior</label>
              <textarea
                id="actual"
                value={actual}
                onChange={(e) => setActual(e.target.value)}
                placeholder="What actually happened?"
                className={cn(inputClasses, "min-h-[60px]")}
              />
            </div>
          </div>

          {/* 4. Metadata (Severity / Category) */}
          <div className="grid grid-cols-2 gap-4 p-4 bg-warm-light/30 rounded-xl border border-warm-grey/30">
            <div>
              <label htmlFor="severity" className={labelClasses}>Severity</label>
              <select
                id="severity"
                value={severity}
                onChange={(e) => setSeverity(e.target.value as Severity)}
                className={inputClasses}
              >
                <option value="low">Low (Cosmetic)</option>
                <option value="medium">Medium (Annoying)</option>
                <option value="high">High (Broken Feature)</option>
                <option value="blocking">Blocking (Crash / Outage)</option>
              </select>
            </div>
            <div>
              <label htmlFor="category" className={labelClasses}>Category</label>
              <select
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value as Category)}
                className={inputClasses}
              >
                <option value="ui">UI / UX</option>
                <option value="data">Data / Content</option>
                <option value="auth">Auth / Login</option>
                <option value="payments">Payments</option>
                <option value="performance">Performance</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          {/* 5. Diagnostics Toggle */}
          <div className="flex items-start gap-3 p-3 bg-blue-50/50 rounded-xl border border-blue-100">
            <div className="mt-0.5">
              <input
                type="checkbox"
                id="includeDiagnostics"
                checked={includeDiagnostics}
                onChange={(e) => setIncludeDiagnostics(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-agent-blurple focus:ring-agent-blurple"
              />
            </div>
            <div>
              <label htmlFor="includeDiagnostics" className="text-sm font-medium text-onyx block">
                Include auto-captured diagnostics
              </label>
              <p className="text-xs text-onyx-muted mt-0.5">
                Attaches console logs, network errors, and recent actions. Sensitive data is redacted.
              </p>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-warm-light/30 border-t border-warm-grey/50 flex justify-end gap-3 shrink-0">
          <Button variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button 
            disabled={!isValid} 
            onClick={handleSubmit}
            className="w-32"
          >
            Submit
          </Button>
        </div>
      </div>
    </div>
  );
}
