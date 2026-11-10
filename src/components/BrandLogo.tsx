import React from 'react';

interface BrandLogoProps {
  onClick?: () => void;
  className?: string;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({ onClick, className = '' }) => {
  return (
    <button
      onClick={onClick}
      className={`group inline-flex items-center gap-3 text-left focus-ring rounded-lg py-1 px-1.5 -ml-1.5 transition-opacity hover:opacity-85 ${className}`}
      aria-label="PreCommit AI Home"
    >
      {/* Abstract overlapping thin circular outlines mark */}
      <div className="relative w-8 h-8 flex items-center justify-center flex-shrink-0" aria-hidden="true">
        <svg
          viewBox="0 0 36 36"
          className="w-8 h-8 text-[#050505] transition-transform duration-300 group-hover:scale-105"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* First circle */}
          <circle
            cx="14"
            cy="18"
            r="10.5"
            stroke="currentColor"
            strokeWidth="1.8"
            className="opacity-90"
          />
          {/* Second overlapping circle */}
          <circle
            cx="22"
            cy="18"
            r="10.5"
            stroke="currentColor"
            strokeWidth="1.8"
            className="opacity-80"
          />
          {/* Subtle inner focal node */}
          <circle
            cx="18"
            cy="18"
            r="2.5"
            fill="currentColor"
            className="opacity-40"
          />
        </svg>
      </div>

      <span className="text-[22px] sm:text-[24px] font-bold tracking-tight text-[#050505] font-sans">
        PreCommit <span className="font-semibold text-neutral-800">AI</span>
      </span>
    </button>
  );
};

