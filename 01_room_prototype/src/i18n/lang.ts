import { createContext, useContext } from 'react';
import { STRINGS, format, joinList, type Key, type Lang } from './strings';

const STORAGE_KEY = 'chisensor_lang';

/** Initial language: #en / #zh in the URL, then the saved choice, then the browser language. */
export function initialLang(): Lang {
  const hash = typeof location !== 'undefined' ? location.hash.replace('#', '') : '';
  if (hash === 'zh' || hash === 'en') return hash;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'zh' || saved === 'en') return saved;
  } catch { /* storage blocked */ }
  return typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('zh') ? 'zh' : 'en';
}

export function saveLang(lang: Lang) {
  try { localStorage.setItem(STORAGE_KEY, lang); } catch { /* storage blocked */ }
  if (typeof document !== 'undefined') document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
}

export interface LangApi {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: Key, params?: Record<string, string | number>) => string;
  list: (items: string[]) => string;
}

export function makeApi(lang: Lang, setLang: (l: Lang) => void): LangApi {
  return {
    lang,
    setLang,
    t: (key, params) => format(STRINGS[lang][key] ?? STRINGS.en[key] ?? key, params),
    list: (items) => joinList(lang, items),
  };
}

export const LangContext = createContext<LangApi>(makeApi('en', () => {}));
export const useLang = () => useContext(LangContext);
