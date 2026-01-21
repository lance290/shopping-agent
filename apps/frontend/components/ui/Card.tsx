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
          'bg-white rounded-xl border border-warm-grey shadow-sm overflow-hidden',
          variant === 'hover' && 'card-hover',
          className
        )}
        {...props}
      />
    );
  }
);
Card.displayName = 'Card';
