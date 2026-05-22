import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
}

export const Card: React.FC<CardProps> = ({
  hoverEffect = false,
  className = '',
  children,
  ...props
}) => {
  return (
    <div
      className={`bg-surface rounded-modal border border-border ${
        hoverEffect ? 'transition-all duration-200 hover:-translate-y-[2px] hover:shadow-md' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
