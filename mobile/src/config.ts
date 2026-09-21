// URL du serveur Boodou. À définir dans mobile/.env :
//   EXPO_PUBLIC_API_URL=https://boodou.example.org
// En développement, l'IP de la machine qui fait tourner uvicorn sur le même
// Wi-Fi que le téléphone (pas « localhost », qui désigne le téléphone lui-même).
export const API_URL = (process.env.EXPO_PUBLIC_API_URL || "http://192.168.1.10:8000").replace(/\/$/, "");

export const LANGS: { code: string; name: string }[] = [
  { code: "fr", name: "Français" },
  { code: "mos", name: "Mooré" },
  { code: "dyu", name: "Dioula" },
  { code: "en", name: "English" },
  { code: "pt", name: "Português" },
  { code: "ar", name: "العربية" },
];

// Langues écrites de droite à gauche.
export const RTL_LANGS = ["ar"];

export const MAX_DESCRIPTION = 2000;
export const NOTE_MAX = 280;
