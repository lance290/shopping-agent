import { ProviderStatusSnapshot } from '../store';
import { cn } from '../../utils/cn';
import { Check, AlertTriangle, XCircle, Clock, BatteryWarning } from 'lucide-react';

interface ProviderStatusBadgeProps {
  status: ProviderStatusSnapshot;
  className?: string;
}

export default function ProviderStatusBadge({ status, className }: ProviderStatusBadgeProps) {
  const { provider_id, status: statusCode, result_count, latency_ms } = status;

  let icon = <Check size={12} />;
  let colorClass = "bg-status-success/10 text-status-success border-status-success/20";
  let label = "OK";

  switch (statusCode) {
    case 'ok':
      icon = <Check size={12} />;
      colorClass = "bg-status-success/10 text-status-success border-status-success/20";
      label = "OK";
      break;
    case 'timeout':
      icon = <Clock size={12} />;
      colorClass = "bg-status-warning/10 text-status-warning border-status-warning/20";
      label = "Timeout";
      break;
    case 'rate_limited':
      icon = <BatteryWarning size={12} />;
      colorClass = "bg-status-warning/10 text-status-warning border-status-warning/20";
      label = "Rate Limit";
      break;
    case 'exhausted':
      icon = <BatteryWarning size={12} />;
      colorClass = "bg-status-error/10 text-status-error border-status-error/20";
      label = "Quota";
      break;
    case 'error':
      icon = <XCircle size={12} />;
      colorClass = "bg-status-error/10 text-status-error border-status-error/20";
      label = "Error";
      break;
  }

  // Format provider name (e.g. google_cse -> Google CSE)
  const ACRONYMS = new Set(['cse', 'api', 'ai', 'id', 'url', 'http', 'https']);
  const providerName = provider_id
    .split('_')
    .map(word => ACRONYMS.has(word.toLowerCase()) 
      ? word.toUpperCase() 
      : word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return (
    <div 
      className={cn(
        "flex items-center gap-1.5 px-2 py-1 rounded-full border text-[10px] font-medium whitespace-nowrap",
        colorClass,
        className
      )}
      title={`${providerName}: ${statusCode} (${latency_ms}ms) - ${result_count} results`}
    >
      {icon}
      <span>{providerName}</span>
      {result_count > 0 && (
        <span className="opacity-75 border-l border-current pl-1 ml-0.5">
          {result_count}
        </span>
      )}
    </div>
  );
}
