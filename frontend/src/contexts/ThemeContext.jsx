import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const ThemeContext = createContext(undefined);

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    try {
      const saved = localStorage.getItem('sourcesage-theme');
      return ['dark', 'light', 'cyberpunk', 'sage'].includes(saved) ? saved : 'dark';
    } catch {
      return 'dark';
    }
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('sourcesage-theme', theme);
    } catch {
      // localStorage unavailable
    }

    // Update meta theme-color
    const metaTheme = document.querySelector('meta[name="theme-color"]');
    if (metaTheme) {
      const colors = {
        dark: '#0a0e1a',
        light: '#f8fafc',
        cyberpunk: '#0f051d',
        sage: '#0b1611',
      };
      metaTheme.setAttribute('content', colors[theme] || '#0a0e1a');
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setThemeState(prev => {
      const list = ['dark', 'light', 'cyberpunk', 'sage'];
      const nextIdx = (list.indexOf(prev) + 1) % list.length;
      return list[nextIdx];
    });
  }, []);

  const setTheme = useCallback((newTheme) => {
    if (['dark', 'light', 'cyberpunk', 'sage'].includes(newTheme)) {
      setThemeState(newTheme);
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export default ThemeContext;
