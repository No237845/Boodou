/** Traductions : les mêmes fichiers que le web et le bot (../app/locales), via metro.config.js.
 *  Une clé absente retombe sur le français, comme côté serveur. */

import storage from "./storage";
import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import fr from "../../app/locales/fr.json";
import en from "../../app/locales/en.json";
import { I18nManager } from "react-native";

import { RTL_LANGS } from "./config";
import mos from "../../app/locales/mos.json";
import pt from "../../app/locales/pt.json";
import ar from "../../app/locales/ar.json";
import dyu from "../../app/locales/dyu.json";

type Dict = Record<string, unknown>;
const DICTS: Record<string, Dict> = { fr, en, mos, dyu, pt, ar };

export function translate(lang: string, key: string, params: Record<string, string | number> = {}): string {
  const raw = (DICTS[lang]?.[key] ?? DICTS.fr[key] ?? key) as string;
  return typeof raw === "string" ? raw.replace(/\{(\w+)\}/g, (_, k) => String(params[k] ?? `{${k}}`)) : key;
}

/** Vrai quand la langue courante s'écrit de droite à gauche. */
export const useRTL = () => RTL_LANGS.includes(useI18n().lang ?? "");

type I18n = { lang: string | null; ready: boolean; setLang: (l: string) => void; t: (key: string, params?: Record<string, string | number>) => string };

const Ctx = createContext<I18n>({ lang: null, ready: false, setLang: () => {}, t: (k) => k });

const STORAGE_KEY = "lang";

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    storage.get(STORAGE_KEY).then((v) => {
      setLangState(v);
      setReady(true);
    });
  }, []);

  const value = useMemo<I18n>(
    () => ({
      lang,
      ready,
      setLang: (l) => {
        setLangState(l);
        storage.set(STORAGE_KEY, l);
        // Mise en page miroir pour l'arabe : React Native ne l'applique qu'au
        // prochain lancement de l'app. D'ici là, les textes sont déjà alignés à
        // droite (voir `useRTL` dans ui.tsx).
        I18nManager.allowRTL(true);
        if (I18nManager.isRTL !== RTL_LANGS.includes(l)) I18nManager.forceRTL(RTL_LANGS.includes(l));
      },
      t: (key, params) => translate(lang ?? "fr", key, params),
    }),
    [lang, ready],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useI18n = () => useContext(Ctx);
