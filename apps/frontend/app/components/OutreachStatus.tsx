'use client';

import { useState, useEffect } from 'react';
import { Mail, Clock, CheckCircle2, Users, Loader2 } from 'lucide-react';

interface OutreachStatusProps {
  rowId: number;
  status: string | null; // none, in_progress, complete
  outreachCount: number;
}

interface OutreachDetails {
  total_sent: number;
  opened: number;
  clicked: number;
  quoted: number;
  vendors: Array<{
    name: string;
    company: string;
    email: string;
    status: string;
  }>;
}

export function OutreachStatus({ rowId, status, outreachCount }: OutreachStatusProps) {
  const [details, setDetails] = useState<OutreachDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (status === 'in_progress' || status === 'complete') {
      loadDetails();
    }
  }, [rowId, status]);

  async function loadDetails() {
    setLoading(true);
    try {
      const res = await fetch(`/api/outreach/${rowId}`);
      if (res.ok) {
        const data = await res.json();
        setDetails(data);
      }
    } catch (err) {
      console.error('Failed to load outreach details:', err);
    } finally {
      setLoading(false);
    }
  }

  if (!status || status === 'none') return null;

  const statusConfig = {
    in_progress: {
      icon: <Loader2 className="animate-spin" size={16} />,
      label: 'Contacting vendors...',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      textColor: 'text-blue-700',
    },
    complete: {
      icon: <CheckCircle2 size={16} />,
      label: 'Vendors contacted',
      bgColor: 'bg-emerald-50',
      borderColor: 'border-emerald-200',
      textColor: 'text-emerald-700',
    },
  };

  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.in_progress;

  return (
    <div className={`${config.bgColor} ${config.borderColor} border rounded-lg p-3 mb-4`}>
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <span className={config.textColor}>{config.icon}</span>
          <span className={`font-medium ${config.textColor}`}>{config.label}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Users size={14} />
          <span>{outreachCount} vendors</span>
        </div>
      </div>

      {expanded && details && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          {/* Stats */}
          <div className="flex gap-4 mb-3 text-sm">
            <div className="flex items-center gap-1 text-gray-600">
              <Mail size={12} />
              <span>{details.total_sent} sent</span>
            </div>
            <div className="flex items-center gap-1 text-gray-600">
              <Clock size={12} />
              <span>{details.quoted} quoted</span>
            </div>
          </div>

          {/* Vendor list */}
          <div className="space-y-2">
            {details.vendors.map((vendor, idx) => (
              <div 
                key={idx}
                className="flex items-center justify-between text-sm bg-white/50 rounded px-2 py-1"
              >
                <span className="font-medium text-gray-800">{vendor.company}</span>
                <VendorStatusBadge status={vendor.status} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function VendorStatusBadge({ status }: { status: string }) {
  const configs: Record<string, { label: string; className: string }> = {
    pending: { label: 'Pending', className: 'bg-gray-100 text-gray-600' },
    sent: { label: 'Sent', className: 'bg-blue-100 text-blue-700' },
    opened: { label: 'Opened', className: 'bg-yellow-100 text-yellow-700' },
    clicked: { label: 'Clicked', className: 'bg-orange-100 text-orange-700' },
    quoted: { label: 'Quoted!', className: 'bg-emerald-100 text-emerald-700' },
  };

  const config = configs[status] || configs.pending;

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${config.className}`}>
      {config.label}
    </span>
  );
}
