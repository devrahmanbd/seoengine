import React from 'react';
import { NavLink } from 'react-router-dom';

export const Navbar: React.FC = () => {
  const navItems = [
    { to: '/management', label: 'Management' },
    { to: '/results', label: 'Results' },
    { to: '/growth', label: 'Growth' },
    { to: '/ai-logs', label: 'AI Logs' },
    { to: '/backend', label: 'Backend' },
  ];

  return (
    <nav className="sticky top-0 z-40 h-[56px] w-full bg-surface/80 backdrop-blur border-b border-border flex items-center px-6">
      <div className="flex items-center gap-8 w-full max-w-7xl mx-auto">
        <div className="font-display font-semibold text-lg text-textPrimary tracking-tight">
          ZenSEO AI
        </div>

        <div className="flex items-center gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-btn text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-background text-primary'
                    : 'text-textSecondary hover:bg-background hover:text-textPrimary'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
};
