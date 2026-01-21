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
            'w-full bg-warm-light border-b-2 border-transparent focus:border-onyx transition-colors outline-none py-3 px-4 text-onyx placeholder:text-onyx-muted/50',
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
