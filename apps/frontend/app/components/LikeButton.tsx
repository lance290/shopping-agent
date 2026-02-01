'use client';

import { Heart } from 'lucide-react';
import { useState, useEffect } from 'react';
import { cn } from '../../utils/cn';

interface LikeButtonProps {
  bidId: number;
  isLiked: boolean;
  likeCount: number;
  onToggle: () => void;
  className?: string;
}

export function LikeButton({
  bidId,
  isLiked,
  likeCount,
  onToggle,
  className,
}: LikeButtonProps) {
  const [isAnimating, setIsAnimating] = useState(false);

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    setIsAnimating(true);
    onToggle();

    // Reset animation after it completes
    setTimeout(() => setIsAnimating(false), 300);
  };

  return (
    <button
      onClick={handleClick}
      aria-pressed={isLiked}
      aria-label={isLiked ? 'Unlike this offer' : 'Like this offer'}
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 rounded-md transition-all duration-200',
        'hover:bg-warm-grey/10 active:scale-95',
        isLiked ? 'text-red-500' : 'text-onyx-muted',
        className
      )}
    >
      <Heart
        size={16}
        className={cn(
          'transition-all duration-200',
          isLiked && 'fill-current',
          isAnimating && 'scale-125'
        )}
      />
      {likeCount > 0 && (
        <span className="text-xs font-medium">
          {likeCount}
        </span>
      )}
    </button>
  );
}
