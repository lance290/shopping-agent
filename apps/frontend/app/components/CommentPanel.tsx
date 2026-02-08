'use client';

import { X, Trash2, Send } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { Button } from '../../components/ui/Button';
import { cn } from '../../utils/cn';

interface CommentPanelProps {
  bidId: number;
  isOpen: boolean;
  onClose: () => void;
}

// NOTE: This component is currently unused and references removed social data state.
// Kept as stub for potential future re-implementation.
export function CommentPanel({ bidId, isOpen, onClose }: CommentPanelProps) {
  const [commentText, setCommentText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Stub data - social features removed in simplification
  const comments: Array<{ id: number; body: string; created_at: string }> = [];

  useEffect(() => {
    if (isOpen && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      // Stub - social features removed
      console.log('Comment submission not implemented:', bidId, commentText.trim());
      setCommentText('');
    } catch (error) {
      console.error('Failed to add comment:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (commentId: number) => {
    if (!window.confirm('Delete this comment?')) return;

    try {
      // Stub - social features removed
      console.log('Comment deletion not implemented:', bidId, commentId);
    } catch (error) {
      console.error('Failed to delete comment:', error);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className={cn(
          'fixed bottom-0 left-0 right-0 z-50',
          'bg-white rounded-t-2xl shadow-xl',
          'max-h-[80vh] flex flex-col',
          'md:left-auto md:right-4 md:bottom-4 md:rounded-2xl',
          'md:w-96 md:max-h-[600px]'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-warm-grey/20">
          <h3 className="text-lg font-semibold text-onyx">
            Comments ({comments.length})
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded-full hover:bg-warm-grey/10 transition-colors"
            aria-label="Close comments"
          >
            <X size={20} className="text-onyx-muted" />
          </button>
        </div>

        {/* Comments List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {comments.length === 0 ? (
            <p className="text-center text-onyx-muted py-8">
              No comments yet. Be the first to comment!
            </p>
          ) : (
            comments.map((comment) => (
              <div
                key={comment.id}
                className="bg-warm-grey/5 rounded-lg p-3 space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-onyx flex-1 whitespace-pre-wrap">
                    {comment.body}
                  </p>
                  <button
                    onClick={() => handleDelete(comment.id)}
                    className="p-1 rounded hover:bg-red-50 hover:text-red-600 transition-colors"
                    aria-label="Delete comment"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <p className="text-xs text-onyx-muted">
                  {new Date(comment.created_at).toLocaleString()}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Comment Input */}
        <form onSubmit={handleSubmit} className="p-4 border-t border-warm-grey/20">
          <div className="flex gap-2">
            <textarea
              ref={textareaRef}
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Add a comment..."
              rows={2}
              className={cn(
                'flex-1 px-3 py-2 rounded-lg resize-none',
                'border border-warm-grey/30 focus:border-agent-blurple',
                'focus:outline-none focus:ring-2 focus:ring-agent-blurple/20',
                'text-sm text-onyx placeholder:text-onyx-muted'
              )}
              disabled={isSubmitting}
            />
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={!commentText.trim() || isSubmitting}
              className="self-end"
            >
              <Send size={16} />
            </Button>
          </div>
        </form>
      </div>
    </>
  );
}
