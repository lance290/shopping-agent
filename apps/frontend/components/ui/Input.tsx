import React from 'react';
import { cn } from '../../utils/cn';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, icon, ...props }, ref) => {
    return (
      <div className="relative flex items-center w-full">
        {icon && (
          <div className="absolute left-4 text-onyx-muted pointer-events-none">
            {icon}
          </div>
        )}
        <input
          ref={ref}
          className={cn(
            'w-full bg-white/90 border border-warm-grey/40 focus:border-agent-blurple/60 focus:ring-2 focus:ring-agent-blurple/15 transition-colors outline-none py-3 px-4 text-sm text-ink placeholder:text-ink-muted/60 rounded-xl',
            icon && 'pl-11',
            className
          )}
          {...props}
        />
      </div>
    );
  }
);
Input.displayName = 'Input';
