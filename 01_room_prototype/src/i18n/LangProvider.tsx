import { useMemo, useState, type ReactNode } from 'react';
import { LangContext, initialLang, makeApi, saveLang } from './lang';
import type { Lang } from './strings';

export default function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const l = initialLang();
    saveLang(l);
    return l;
  });
  const api = useMemo(() => makeApi(lang, (l: Lang) => { saveLang(l); setLangState(l); }), [lang]);
  return <LangContext.Provider value={api}>{children}</LangContext.Provider>;
}
