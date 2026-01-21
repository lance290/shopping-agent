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
          'bg-white rounded-2xl border border-warm-grey/70 shadow-[0_8px_24px_rgba(0,0,0,0.06)] overflow-hidden',
          variant === 'hover' && 'card-hover',
          className
        )}
        {...props}
      />
    );
  }
);
Card.displayName = 'Card';
