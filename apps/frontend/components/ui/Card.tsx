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
          'bg-warm-light rounded-[12px] border border-warm-grey/60 overflow-hidden',
          variant === 'hover' && 'card-hover transition-transform duration-300 ease-out hover:scale-[1.005]',
          className
        )}
        {...props}
      />
    );
  }
);
Card.displayName = 'Card';
