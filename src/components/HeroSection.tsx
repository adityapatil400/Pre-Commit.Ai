import React from 'react';

export const HeroSection: React.FC = () => {
  return (
    <section className="text-center pt-2 sm:pt-4 pb-4 sm:pb-6 max-w-4xl mx-auto px-2 sm:px-4 w-full">
      {/* Decorative overlapping circular rings emblem from specification ASCII diagram */}
      <div className="flex justify-center items-center mb-2 sm:mb-3" aria-hidden="true">
        <div className="flex items-center -space-x-2.5 opacity-70 hover:opacity-100 transition-opacity">
          <div className="w-4 sm:w-5 h-4 sm:h-5 rounded-full border-[1.5px] border-[#050505]"></div>
          <div className="w-4 sm:w-5 h-4 sm:h-5 rounded-full border-[1.5px] border-[#050505]"></div>
          <div className="w-4 sm:w-5 h-4 sm:h-5 rounded-full border-[1.5px] border-[#050505]"></div>
          <div className="w-4 sm:w-5 h-4 sm:h-5 rounded-full border-[1.5px] border-[#050505]"></div>
        </div>
      </div>

      {/* Eyebrow text */}
      <p className="text-[14px] sm:text-[17px] md:text-[19px] font-normal text-[#555555] tracking-tight mb-2 sm:mb-2.5">
        AI-powered Python code analysis
      </p>

      {/* Main headline - Responsive font sizing & natural wrapping */}
      <h1 className="text-[25px] sm:text-[42px] md:text-[52px] lg:text-[60px] font-extrabold text-[#050505] tracking-tight leading-[1.15] sm:leading-[1.1] max-w-[780px] mx-auto px-2">
        Catch Bugs &amp; Leakages <br className="sm:hidden" />
        Before <br className="hidden sm:inline" />
        They Commit.
      </h1>
    </section>
  );
};
