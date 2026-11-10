import React, { useState } from 'react';
import { X, AlertCircle } from 'lucide-react';

interface GitHubRepositoryInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  onClearOther?: () => void;
  isInvalidExternal?: boolean;
  externalError?: string | null;
}

// GitHub repo regex validation: https://github.com/owner/repo
const GITHUB_REPO_REGEX = /^https?:\/\/(www\.)?github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$/;

export const GitHubRepositoryInput: React.FC<GitHubRepositoryInputProps> = ({
  value,
  onChange,
  disabled = false,
  onClearOther,
  isInvalidExternal = false,
  externalError = null,
}) => {
  const [hasBlurred, setHasBlurred] = useState(false);

  const trimmed = value.trim();
  const isValidFormat = trimmed === '' || GITHUB_REPO_REGEX.test(trimmed);
  const showError = (hasBlurred && trimmed !== '' && !isValidFormat) || Boolean(externalError) || isInvalidExternal;

  const errorMessage = externalError || 'Please enter a valid GitHub repository URL (e.g. https://github.com/username/repository)';

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    onChange(val);
    if (val.trim() !== '') {
      onClearOther?.();
    }
  };

  const handleClear = () => {
    onChange('');
    setHasBlurred(false);
  };

  const handleBlur = () => {
    if (trimmed !== '') {
      setHasBlurred(true);
    }
  };

  return (
    <div className="w-full">
      <label htmlFor="github-repo-url" className="sr-only">
        GitHub Repository URL
      </label>

      {/* Input container matching upload panel width */}
      <div
        className={`relative flex items-center w-full bg-white rounded-[12px] sm:rounded-[14px] border-[1.75px] transition-all duration-150 ${
          showError
            ? 'border-red-500 bg-red-50/20'
            : 'border-[#202020] focus-within:border-[#278BEA] focus-within:ring-2 focus-within:ring-[#278BEA]/20'
        } ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
        style={{ minHeight: '50px' }}
      >
        {/* GitHub Icon */}
        <div className="pl-4 pr-3 text-[#050505] flex items-center justify-center pointer-events-none" aria-hidden="true">
          <svg
            className="w-5 h-5 fill-current"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            />
          </svg>
        </div>

        {/* Input element */}
        <input
          id="github-repo-url"
          name="githubRepoUrl"
          type="url"
          autoComplete="url"
          spellCheck="false"
          value={value}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={disabled}
          placeholder="https://github.com/username/repository"
          aria-invalid={showError ? 'true' : undefined}
          aria-describedby={showError ? 'github-url-error' : undefined}
          className="w-full h-full py-3 pr-10 text-[15px] sm:text-[16px] text-[#050505] placeholder-[#555555] bg-transparent outline-none font-sans"
        />

        {/* Clear Button */}
        {value.length > 0 && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-3.5 p-1 rounded-full text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 focus-ring"
            aria-label="Clear repository URL"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Validation error message */}
      {showError && (
        <div
          id="github-url-error"
          role="alert"
          className="mt-2 flex items-center gap-2 text-[13.5px] text-red-600 px-1 font-medium"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
};
