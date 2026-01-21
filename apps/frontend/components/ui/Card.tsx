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
          'bg-white rounded-xl border border-warm-grey/50 overflow-hidden',
          variant === 'hover' && 'card-hover transition-transform duration-300 ease-out hover:scale-[1.01]',
          className
        )}
        {...props}
      />
    );
  }
);
Card.displayName = 'Card';
