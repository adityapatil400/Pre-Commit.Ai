import React from 'react';
import { Loader2, ArrowRight } from 'lucide-react';

interface AnalyzeButtonProps {
  onClick: () => void;
  disabled?: boolean;
  isLoading?: boolean;
  loadingText?: string;
  className?: string;
}

export const AnalyzeButton: React.FC<AnalyzeButtonProps> = ({
  onClick,
  disabled = false,
  isLoading = false,
  loadingText = 'Analyzing Project...',
  className = '',
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      className={`relative w-full py-3.5 px-6 rounded-[12px] sm:rounded-[14px] bg-[#000000] text-[#FFFFFF] font-semibold text-[16px] sm:text-[17px] flex items-center justify-center gap-2.5 transition-all duration-200 select-none ${
        disabled
          ? 'opacity-40 cursor-not-allowed bg-neutral-900'
          : 'hover:bg-neutral-800 active:scale-[0.99] cursor-pointer shadow-sm hover:shadow'
      } focus-ring ${className}`}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>{loadingText}</span>
        </>
      ) : (
        <>
          <span>Analyze Code</span>
          <ArrowRight className="w-5 h-5 stroke-[2.2] transition-transform duration-200 group-hover:translate-x-1" />
        </>
      )}
    </button>
  );
};
