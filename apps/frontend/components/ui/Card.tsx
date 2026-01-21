import React from 'react';
import { cn } from '../../utils/cn';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'hover';
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'bg-white/90 backdrop-blur-xl rounded-2xl border border-white/35 shadow-[0_10px_28px_rgba(0,0,0,0.08)] overflow-hidden',
          variant === 'hover' && 'card-hover',
          className
        )}
        {...props}
      />
    );
  }
);
Card.displayName = 'Card';
