"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

type Language = "en" | "ur" | "roman_ur";

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");
  const [translations, setTranslations] = useState<Record<string, any>>({});

  useEffect(() => {
    // Load setting from backend
    fetch("http://localhost:8000/api/settings")
      .then(res => res.json())
      .then(data => {
        if (data.language && ["en", "ur", "roman_ur"].includes(data.language)) {
          setLanguageState(data.language as Language);
        }
      })
      .catch(err => console.error("Could not load language settings", err));
  }, []);

  useEffect(() => {
    // Dynamically load the language file
    import(`../locales/${language}.json`)
      .then(mod => setTranslations(mod.default))
      .catch(err => console.error(`Could not load locale ${language}`, err));
  }, [language]);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    // Persist to backend
    fetch("http://localhost:8000/api/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: lang })
    }).catch(err => console.error("Failed to save language to backend", err));
  };

  const t = (key: string) => {
    const keys = key.split(".");
    let val = translations;
    for (const k of keys) {
      if (val && typeof val === "object" && k in val) {
        val = val[k];
      } else {
        return key;
      }
    }
    return val as unknown as string;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
