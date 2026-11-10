import React from 'react';

export const OrDivider: React.FC = () => {
  return (
    <div className="relative flex items-center justify-center my-4 sm:my-5 w-full">
      <div className="flex-grow border-t border-[#A0A0A0]/50" />
      <span className="flex-shrink mx-4 text-[13px] font-medium tracking-wider text-[#555555] uppercase select-none">
        OR
      </span>
      <div className="flex-grow border-t border-[#A0A0A0]/50" />
    </div>
  );
};
