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
            'w-full bg-white border border-warm-grey/80 focus:border-agent-blurple focus:ring-2 focus:ring-agent-blurple/20 transition-colors outline-none py-3 px-4 text-sm text-onyx placeholder:text-onyx-muted/60 rounded-xl',
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
