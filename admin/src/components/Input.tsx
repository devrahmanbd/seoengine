import React, { forwardRef } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-textPrimary mb-1">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`w-full bg-background border border-border rounded-btn px-[14px] py-[10px] text-textPrimary text-sm outline-none transition-all duration-200 placeholder:text-textSecondary focus:border-primary focus:ring-[3px] focus:ring-primary/12 disabled:opacity-50 disabled:bg-border/50 ${
            error ? 'border-error focus:border-error focus:ring-error/12' : ''
          } ${className}`}
          {...props}
        />
        {error && <p className="mt-1 text-sm text-error">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
