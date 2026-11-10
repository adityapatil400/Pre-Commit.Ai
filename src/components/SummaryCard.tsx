import React from 'react';
import { LucideIcon } from 'lucide-react';

interface SummaryCardProps {
  title: string;
  count: number;
  icon: LucideIcon;
  badgeLabel?: string;
  badgeColor?: 'red' | 'amber' | 'blue' | 'neutral';
  description: string;
  isActive?: boolean;
  onClick?: () => void;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
  title,
  count,
  icon: Icon,
  badgeLabel,
  badgeColor = 'neutral',
  description,
  isActive = false,
  onClick,
}) => {
  const getBadgeClasses = () => {
    switch (badgeColor) {
      case 'red':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'amber':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'blue':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      default:
        return 'bg-neutral-100 text-neutral-700 border-neutral-200';
    }
  };

  const getIconWrapperClasses = () => {
    switch (badgeColor) {
      case 'red':
        return 'bg-red-50 text-red-600';
      case 'amber':
        return 'bg-amber-50 text-amber-600';
      case 'blue':
        return 'bg-blue-50 text-blue-600';
      default:
        return 'bg-neutral-100 text-neutral-800';
    }
  };

  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
      className={`relative p-5 rounded-[16px] border-[1.5px] bg-white transition-all duration-200 text-left ${
        onClick ? 'cursor-pointer hover:shadow-md' : ''
      } ${
        isActive
          ? 'border-[#202020] ring-2 ring-[#050505] shadow-sm'
          : 'border-neutral-200 hover:border-neutral-400 shadow-sm'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-[10px] flex items-center justify-center ${getIconWrapperClasses()}`}>
          <Icon className="w-5 h-5 stroke-[2]" />
        </div>
        {badgeLabel && (
          <span className={`text-[12px] font-semibold px-2 py-0.5 rounded-full border ${getBadgeClasses()}`}>
            {badgeLabel}
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-2 mb-1">
        <span className="text-[32px] sm:text-[36px] font-bold tracking-tight text-[#050505] leading-none">
          {count}
        </span>
      </div>

      <h3 className="text-[15px] font-semibold text-[#050505] mb-1">
        {title}
      </h3>

      <p className="text-[13px] text-[#555555] leading-snug">
        {description}
      </p>
    </div>
  );
};

