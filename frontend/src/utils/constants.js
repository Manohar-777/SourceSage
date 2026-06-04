export const SEVERITY_COLORS = {
  critical: 'var(--error)',
  warning: 'var(--warning)',
  info: 'var(--accent-primary)',
  suggestion: 'var(--success)',
};

export const SEVERITY_BG_COLORS = {
  critical: 'var(--error-glow)',
  warning: 'var(--warning-glow)',
  info: 'var(--accent-glow)',
  suggestion: 'var(--success-glow)',
};

export const SEVERITY_LABELS = {
  critical: 'Critical',
  warning: 'Warning',
  info: 'Info',
  suggestion: 'Suggestion',
};

export const SEVERITY_ORDER = {
  critical: 0,
  warning: 1,
  info: 2,
  suggestion: 3,
};

export const CATEGORY_ICONS = {
  security: '🔒',
  performance: '⚡',
  'best-practice': '✅',
  'code-quality': '💎',
  'error-handling': '🛡️',
  documentation: '📝',
  maintainability: '🔧',
  accessibility: '♿',
  testing: '🧪',
  style: '🎨',
  bug: '🐛',
  other: '📌',
};

export const DEFAULT_LANGUAGES = [
  'python', 'javascript', 'typescript', 'java', 'go', 'rust',
  'c', 'cpp', 'csharp', 'ruby', 'php', 'swift', 'kotlin',
];

export const MAX_RECENT_REPOS = 5;

export const ANALYSIS_STATES = {
  IDLE: 'idle',
  CLONING: 'cloning',
  ANALYZING: 'analyzing',
  COMPLETE: 'complete',
  ERROR: 'error',
};
