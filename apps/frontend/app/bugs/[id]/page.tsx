'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { fetchBugReport, BugReportResponse } from '../../utils/api';
import { Button } from '../../../components/ui/Button';
import { ArrowLeft, CheckCircle2, Clock, AlertTriangle, XCircle, FileIcon, Github, ExternalLink } from 'lucide-react';
import Link from 'next/link';

export default function BugReportStatusPage() {
  const params = useParams();
  const id = params?.id as string;
  
  const [report, setReport] = useState<BugReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const loadReport = async () => {
      try {
        const data = await fetchBugReport(id);
        if (data) {
          setReport(data);
        } else {
          setError('Bug report not found.');
        }
      } catch (err) {
        setError('Failed to load bug report.');
      } finally {
        setLoading(false);
      }
    };

    loadReport();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-warm-white flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center">
          <div className="w-12 h-12 bg-gray-200 rounded-full mb-4"></div>
          <div className="h-4 w-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-warm-white p-8 flex flex-col items-center justify-center text-center">
        <div className="p-4 bg-rose-50 rounded-full text-rose-500 mb-4">
          <AlertTriangle size={32} />
        </div>
        <h1 className="text-xl font-semibold text-onyx mb-2">Something went wrong</h1>
        <p className="text-onyx-muted mb-6">{error || 'Could not find that report.'}</p>
        <Link href="/">
          <Button variant="secondary">Back to Home</Button>
        </Link>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'captured': return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'sent': return 'text-indigo-600 bg-indigo-50 border-indigo-200';
      case 'pr_created': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'preview_ready': return 'text-pink-600 bg-pink-50 border-pink-200';
      case 'shipped': return 'text-green-600 bg-green-50 border-green-200';
      case 'closed': return 'text-gray-600 bg-gray-100 border-gray-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'captured': return <CheckCircle2 size={16} />;
      case 'sent': return <ExternalLink size={16} />;
      case 'pr_created': return <Github size={16} />;
      case 'preview_ready': return <ExternalLink size={16} />;
      case 'shipped': return <CheckCircle2 size={16} />;
      case 'closed': return <XCircle size={16} />;
      default: return <Clock size={16} />;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'captured': return 'Captured';
      case 'sent': return 'Issue Created';
      case 'pr_created': return 'Fix in Progress';
      case 'preview_ready': return 'Ready for Review';
      case 'shipped': return 'Fix Shipped';
      case 'closed': return 'Closed';
      default: return status;
    }
  };

  return (
    <div className="min-h-screen bg-warm-white p-4 md:p-8">
      <div className="max-w-2xl mx-auto">
        <Link href="/" className="inline-flex items-center text-onyx-muted hover:text-onyx mb-6 transition-colors">
          <ArrowLeft size={16} className="mr-2" />
          Back to Board
        </Link>

        <div className="bg-white rounded-2xl shadow-sm border border-warm-grey overflow-hidden">
          {/* Header */}
          <div className="px-6 py-6 border-b border-warm-grey/50 bg-warm-light/30">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h1 className="text-2xl font-semibold text-onyx">Bug Report #{report.id}</h1>
                <p className="text-sm text-onyx-muted mt-1">
                  Submitted on {new Date(report.created_at).toLocaleDateString()} at {new Date(report.created_at).toLocaleTimeString()}
                </p>
              </div>
              <div className={`px-3 py-1 rounded-full text-sm font-medium border flex items-center gap-2 ${getStatusColor(report.status)}`}>
                {getStatusIcon(report.status)}
                <span className="capitalize">{getStatusLabel(report.status)}</span>
              </div>
            </div>
            
            {/* Actions / Links */}
            <div className="flex flex-wrap gap-3 mt-4">
                {report.github_issue_url && (
                    <a href={report.github_issue_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-medium transition-colors">
                        <Github size={14} className="mr-1.5" />
                        View Issue
                    </a>
                )}
                {report.github_pr_url && (
                    <a href={report.github_pr_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center px-3 py-1.5 bg-orange-50 hover:bg-orange-100 text-orange-700 border border-orange-200 rounded-lg text-xs font-medium transition-colors">
                        <Github size={14} className="mr-1.5" />
                        View Pull Request
                    </a>
                )}
                {report.preview_url && (
                    <a href={report.preview_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center px-3 py-1.5 bg-pink-50 hover:bg-pink-100 text-pink-700 border border-pink-200 rounded-lg text-xs font-medium transition-colors">
                        <ExternalLink size={14} className="mr-1.5" />
                        Preview Fix
                    </a>
                )}
            </div>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">

            
            <div>
              <h3 className="text-sm font-medium text-onyx-muted uppercase tracking-wider mb-2">Description</h3>
              <p className="text-onyx whitespace-pre-wrap leading-relaxed">{report.notes}</p>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div>
                <h3 className="text-xs font-medium text-onyx-muted uppercase tracking-wider mb-2">Severity</h3>
                <span className="inline-block px-2 py-1 bg-gray-100 rounded text-sm text-onyx capitalize">
                  {report.severity}
                </span>
              </div>
              <div>
                <h3 className="text-xs font-medium text-onyx-muted uppercase tracking-wider mb-2">Category</h3>
                <span className="inline-block px-2 py-1 bg-gray-100 rounded text-sm text-onyx capitalize">
                  {report.category}
                </span>
              </div>
            </div>

            {report.attachments && report.attachments.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-onyx-muted uppercase tracking-wider mb-3">Attachments</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {report.attachments.map((path: string, i: number) => (
                    <a 
                      key={i} 
                      href={path} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="block aspect-square rounded-lg border border-warm-grey overflow-hidden hover:border-blue-400 transition-colors bg-gray-50 relative group"
                    >
                      {/* Very basic preview attempt based on extension */}
                      {path.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
                        <img src={path} alt="Attachment" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex flex-col items-center justify-center text-onyx-muted p-2 text-center">
                          <FileIcon size={24} className="mb-2" />
                          <span className="text-[10px] truncate w-full px-1">{path.split('/').pop()}</span>
                        </div>
                      )}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          {/* Footer / Timeline Stub */}
          <div className="px-6 py-4 bg-gray-50 border-t border-warm-grey/50">
             <h3 className="text-xs font-medium text-onyx-muted uppercase tracking-wider mb-3">Activity</h3>
             <div className="flex gap-3">
                <div className="relative pt-1">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <div className="absolute top-3 left-1 w-px h-full bg-gray-200 -ml-px"></div>
                </div>
                <div className="pb-4">
                    <p className="text-sm text-onyx">Report captured</p>
                    <p className="text-xs text-onyx-muted">{new Date(report.created_at).toLocaleString()}</p>
                </div>
             </div>
             {/* Dynamic timeline would go here later */}
          </div>
        </div>
      </div>
    </div>
  );
}
