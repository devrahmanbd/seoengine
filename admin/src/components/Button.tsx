import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
}

export const Button: React.FC<ButtonProps> = ({
  size = 'md',
  variant = 'primary',
  className = '',
  children,
  ...props
}) => {
  const sizeClasses = {
    sm: 'h-[32px] px-3 text-sm',
    md: 'h-[38px] px-4 text-sm',
    lg: 'h-[44px] px-5 text-base',
  };

  const variantClasses = {
    primary: 'bg-primary text-white hover:-translate-y-[1px] shadow-sm',
    secondary: 'bg-surface text-textPrimary border border-border hover:-translate-y-[1px]',
    ghost: 'bg-transparent text-textSecondary hover:bg-border/50 hover:text-textPrimary',
    danger: 'bg-error text-white hover:-translate-y-[1px] shadow-sm',
  };

  return (
    <button
      className={`inline-flex items-center justify-center font-medium rounded-btn transition-all duration-200 disabled:opacity-50 disabled:pointer-events-none ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};
