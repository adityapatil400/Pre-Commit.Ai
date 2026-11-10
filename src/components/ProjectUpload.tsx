import React, { useRef, useState } from 'react';
import { Upload, FileArchive, FileCode2, X, CheckCircle2, AlertCircle } from 'lucide-react';

interface ProjectUploadProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  disabled?: boolean;
  onClearOther?: () => void;
}

export const ProjectUpload: React.FC<ProjectUploadProps> = ({
  selectedFile,
  onFileSelect,
  disabled = false,
  onClearOther,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const validateAndSetFile = (file: File) => {
    setErrorMessage(null);

    const name = file.name.toLowerCase();
    const isZip = name.endsWith('.zip') || file.type.includes('zip') || file.type.includes('compressed');
    const isPython = name.endsWith('.py');

    if (!isZip && !isPython) {
      setErrorMessage('Invalid file format. Please upload a .py Python file or a .zip project archive.');
      return;
    }

    // Max 100MB
    const maxSizeBytes = 100 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      setErrorMessage('File size exceeds the 100MB limit. Please provide a smaller archive or use GitHub repository analysis.');
      return;
    }

    onClearOther?.();
    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled) return;
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      validateAndSetFile(droppedFile);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const chosenFile = e.target.files[0];
      validateAndSetFile(chosenFile);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleChooseFilesClick = () => {
    fileInputRef.current?.click();
  };

  const handleRemoveFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    onFileSelect(null);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const isPy = selectedFile?.name.toLowerCase().endsWith('.py');

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept=".zip,.py,application/zip,application/x-zip-compressed,text/x-python"
        onChange={handleFileChange}
        className="hidden"
        id="project-zip-upload"
        aria-label="Upload Python file or ZIP project"
      />

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative w-full rounded-[18px] sm:rounded-[20px] border-[1.75px] bg-white transition-all duration-200 py-6 sm:py-7 px-6 sm:px-10 flex flex-col items-center justify-center text-center ${
          isDragOver
            ? 'border-[#278BEA] bg-blue-50/40 shadow-sm'
            : selectedFile
            ? 'border-[#202020] bg-neutral-50/50'
            : 'border-[#202020] hover:border-neutral-700'
        } ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
        style={{ minHeight: '210px' }}
      >
        {selectedFile ? (
          <div className="w-full flex flex-col items-center animate-fadeIn">
            <div className="w-11 h-11 rounded-full bg-neutral-100 flex items-center justify-center text-[#050505] mb-2.5">
              {isPy ? <FileCode2 className="w-5 h-5 stroke-[1.8] text-blue-600" /> : <FileArchive className="w-5 h-5 stroke-[1.8]" />}
            </div>

            <div className="flex items-center gap-2 max-w-full mb-1">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span className="font-semibold text-[17px] text-[#050505] truncate max-w-[280px] sm:max-w-md">
                {selectedFile.name}
              </span>
            </div>

            <span className="text-[13.5px] text-[#555555] mb-3.5">
              {formatFileSize(selectedFile.size)} • Ready for AST static analysis
            </span>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleChooseFilesClick}
                className="px-3.5 py-1.5 text-[13.5px] font-medium text-[#050505] bg-white border border-[#202020] rounded-[10px] hover:bg-neutral-50 focus-ring transition-colors"
              >
                Replace file
              </button>
              <button
                type="button"
                onClick={handleRemoveFile}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-[13.5px] font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-[10px] focus-ring transition-colors"
                aria-label="Remove selected file"
              >
                <X className="w-3.5 h-3.5" />
                Remove
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="w-11 h-11 rounded-full bg-neutral-100 flex items-center justify-center text-[#050505] mb-3 group-hover:scale-105 transition-transform" aria-hidden="true">
              <Upload className="w-5 h-5 stroke-[1.8]" />
            </div>

            <h2 className="text-[22px] sm:text-[26px] md:text-[28px] font-bold text-[#050505] tracking-tight mb-1">
              Upload your project
            </h2>

            <p className="text-[15px] sm:text-[16px] md:text-[17px] text-[#555555] font-normal mb-4">
              Drop a Python file (.py), ZIP archive, or select a folder
            </p>

            <button
              type="button"
              onClick={handleChooseFilesClick}
              className="px-5 py-2 text-[14.5px] sm:text-[15px] font-semibold text-[#050505] bg-white border-[1.5px] border-[#202020] rounded-[11px] hover:bg-neutral-50 focus-ring shadow-none transition-all active:scale-[0.98]"
            >
              Choose Files
            </button>
          </div>
        )}
      </div>

      {errorMessage && (
        <div
          role="alert"
          className="mt-2.5 flex items-center gap-2 text-[13.5px] text-red-600 bg-red-50/90 border border-red-200 px-3.5 py-2 rounded-[10px]"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
};
