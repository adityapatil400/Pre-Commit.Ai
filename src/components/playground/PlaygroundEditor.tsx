import React, { useRef, useEffect } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { PlaygroundIssue } from '../../types/playground';

export const WELCOME_COMMENT = '# Welcome to PreCommit AI Playground By Aditya Patil!';

interface PlaygroundEditorProps {
  code: string;
  onChange: (value: string) => void;
  language?: string;
  path?: string;
  theme?: 'vs-dark' | 'vs';
  issues?: PlaygroundIssue[];
  targetLine?: number | null;
  onCursorChange?: (line: number, column: number) => void;
  isWelcomeActive?: boolean;
  onWelcomeClear?: () => void;
}

export const PlaygroundEditor: React.FC<PlaygroundEditorProps> = ({
  code,
  onChange,
  language = 'python',
  path = 'main.py',
  theme = 'vs-dark',
  issues = [],
  targetLine,
  onCursorChange,
  isWelcomeActive = false,
  onWelcomeClear,
}) => {
  const editorRef = useRef<any>(null);
  const monacoRef = useRef<any>(null);

  const isWelcomeActiveRef = useRef(isWelcomeActive);
  isWelcomeActiveRef.current = isWelcomeActive;

  const onWelcomeClearRef = useRef(onWelcomeClear);
  onWelcomeClearRef.current = onWelcomeClear;

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;

    // Track cursor movements for status bar
    editor.onDidChangeCursorPosition((e) => {
      onCursorChange?.(e.position.lineNumber, e.position.column);
    });

    // Remove welcome comment as soon as user starts typing
    editor.onKeyDown((e) => {
      if (isWelcomeActiveRef.current) {
        // Ignore modifier-only keys: Shift, Ctrl, Alt, Meta
        // Ignore standalone arrow navigation keys
        const isModifier =
          e.ctrlKey ||
          e.metaKey ||
          e.altKey ||
          e.keyCode === monaco.KeyCode.Shift ||
          e.keyCode === monaco.KeyCode.Ctrl ||
          e.keyCode === monaco.KeyCode.Alt ||
          e.keyCode === monaco.KeyCode.Meta;

        const isArrow =
          e.keyCode === monaco.KeyCode.LeftArrow ||
          e.keyCode === monaco.KeyCode.RightArrow ||
          e.keyCode === monaco.KeyCode.UpArrow ||
          e.keyCode === monaco.KeyCode.DownArrow;

        if (!isModifier && !isArrow) {
          isWelcomeActiveRef.current = false;
          onWelcomeClearRef.current?.();

          // If Backspace or Delete pressed, simply clear editor to empty
          if (e.keyCode === monaco.KeyCode.Backspace || e.keyCode === monaco.KeyCode.Delete) {
            e.preventDefault();
            editor.setValue('');
            return;
          }

          // For any character key or Enter:
          // Clear current welcome comment range so the typed character inserts cleanly into line 1
          const model = editor.getModel();
          if (model) {
            const fullRange = model.getFullModelRange();
            editor.executeEdits('welcome-clear', [
              {
                range: fullRange,
                text: '',
              },
            ]);
          }
        }
      }
    });

    // Handle paste event when welcome comment is active
    editor.onDidPaste(() => {
      if (isWelcomeActiveRef.current) {
        isWelcomeActiveRef.current = false;
        onWelcomeClearRef.current?.();
      }
    });

    // Configure authentic VS Code editor options
    editor.updateOptions({
      tabSize: 4,
      insertSpaces: true,
      fontSize: 13.5,
      lineHeight: 22,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, Menlo, monospace",
      minimap: { enabled: true, side: 'right', scale: 1 },
      scrollBeyondLastLine: false,
      automaticLayout: true,
      formatOnPaste: true,
      formatOnType: true,
      bracketPairColorization: { enabled: true },
      suggest: {
        snippetsPreventQuickSuggestions: false,
      },
      renderLineHighlight: 'all',
      cursorBlinking: 'smooth',
      cursorSmoothCaretAnimation: 'on',
      smoothScrolling: true,
      folding: true,
      foldingHighlight: true,
      lineNumbers: 'on',
    });
  };

  // Scroll and reveal line when targetLine changes
  useEffect(() => {
    if (editorRef.current && targetLine && targetLine > 0) {
      editorRef.current.revealLineInCenter(targetLine);
      editorRef.current.setPosition({ lineNumber: targetLine, column: 1 });
      editorRef.current.focus();
    }
  }, [targetLine]);

  // Set error/warning markers on the Monaco model
  useEffect(() => {
    if (!editorRef.current || !monacoRef.current) return;

    const monaco = monacoRef.current;
    const model = editorRef.current.getModel();
    if (!model) return;

    // Do not set error markers if welcome comment is active
    if (isWelcomeActive || code.trim() === WELCOME_COMMENT) {
      monaco.editor.setModelMarkers(model, 'precommit-ai', []);
      return;
    }

    const markers = issues.map((iss) => {
      let severity = monaco.MarkerSeverity.Warning;
      if (iss.severity === 'Critical' || iss.severity === 'High' || iss.type === 'Syntax Error') {
        severity = monaco.MarkerSeverity.Error;
      } else if (iss.severity === 'Low') {
        severity = monaco.MarkerSeverity.Info;
      }

      const line = Math.max(1, iss.line || 1);
      const col = Math.max(1, iss.column || 1);

      return {
        startLineNumber: line,
        startColumn: col,
        endLineNumber: line,
        endColumn: col + Math.max(1, (iss.problematic_code || '').length),
        message: `[${iss.type}] ${iss.description}\nSuggestion: ${iss.suggestion}`,
        severity,
      };
    });

    monaco.editor.setModelMarkers(model, 'precommit-ai', markers);
  }, [issues, isWelcomeActive, code, path]);

  const handleEditorChange = (val: string | undefined) => {
    const newVal = val || '';
    if (isWelcomeActiveRef.current) {
      if (newVal !== WELCOME_COMMENT) {
        isWelcomeActiveRef.current = false;
        onWelcomeClearRef.current?.();

        let cleanVal = newVal;
        if (cleanVal.includes(WELCOME_COMMENT)) {
          cleanVal = cleanVal.replace(WELCOME_COMMENT, '').trimStart();
        }
        onChange(cleanVal);
        return;
      }
    }
    onChange(newVal);
  };

  return (
    <div className="w-full h-full bg-[#1e1e1e] overflow-hidden">
      <Editor
        height="100%"
        path={path}
        language={language}
        value={code}
        onChange={handleEditorChange}
        theme={theme}
        onMount={handleEditorDidMount}
        saveViewState={true}
        options={{
          renderWhitespace: 'selection',
          cursorBlinking: 'smooth',
          cursorSmoothCaretAnimation: 'on',
          smoothScrolling: true,
          folding: true,
          foldingHighlight: true,
          renderLineHighlight: 'all',
          lineNumbers: 'on',
        }}
      />
    </div>
  );
};
