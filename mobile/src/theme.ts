/** Thème sobre, aligné sur le site web (app/static/style.css) : un seul accent
 *  vert profond, fond neutre, police système, bordures fines. Clair et sombre. */

import { Platform, useColorScheme } from "react-native";

export const light = {
  primary: "#0b5d3b", primaryLight: "#eef4f0", primaryDark: "#08452c", onPrimary: "#ffffff",
  urgent: "#b3261e", urgentLight: "#fde8e6",
  success: "#0b5d3b", successLight: "#eef4f0",
  warning: "#8a5a00", warningLight: "#fff4e5",
  // Ocre du logo : second accent, réservé à l'encadré urgence (jamais sur une action).
  accent: "#b8742a", accentLight: "#fbf1e4",
  text: "#1c1c1c", textSecondary: "#5f5f5f", textDisabled: "#9a9a9a",
  bg: "#fafaf7", bgSecondary: "#f1f1ee", surface: "#ffffff", border: "#dddddd", disabled: "#e6e6e6",
};
export const dark: typeof light = {
  primary: "#2e9a68", primaryLight: "#1e2a24", primaryDark: "#5cc491", onPrimary: "#ffffff",
  urgent: "#f2685e", urgentLight: "#3a1f1d",
  success: "#2e9a68", successLight: "#1e2a24",
  warning: "#e0a34a", warningLight: "#3a2c14",
  accent: "#d9944a", accentLight: "#2a2117",
  text: "#eeeeee", textSecondary: "#aaaaaa", textDisabled: "#666666",
  bg: "#141414", bgSecondary: "#1b1b1b", surface: "#1e1e1e", border: "#333333", disabled: "#2c2c2c",
};
export type Theme = typeof light;

export const useTheme = (): Theme => (useColorScheme() === "dark" ? dark : light);

export const space = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48 } as const;
export const radius = { sm: 4, md: 8, lg: 10, full: 9999 } as const;

// Police système : rien à charger, rendu natif sur chaque téléphone.
export const mono = Platform.select({ ios: "Menlo", android: "monospace", default: "monospace" });

export const type = {
  h1: { fontSize: 24, lineHeight: 31, fontWeight: "700" as const },
  h2: { fontSize: 19, lineHeight: 26, fontWeight: "700" as const },
  h3: { fontSize: 17, lineHeight: 24, fontWeight: "600" as const },
  bodyLg: { fontSize: 18, lineHeight: 27 },
  body: { fontSize: 16, lineHeight: 24 },
  bodySm: { fontSize: 14, lineHeight: 20 },
  caption: { fontSize: 12, lineHeight: 16 },
  button: { fontSize: 16, lineHeight: 22, fontWeight: "600" as const },
} as const;

// Une seule ombre, très légère : le relief vient des bordures, pas des ombres.
export const shadow = {
  sm: { shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 2, shadowOffset: { width: 0, height: 1 }, elevation: 1 },
} as const;

/** Couleur de chaque étape du suivi. */
export const statusColor = (th: Theme): Record<string, string> => ({
  RECU: th.warning, TRANSMIS: th.primary, PRIS_EN_CHARGE: th.primary, REGLE: th.textSecondary,
});
export const statusIcon: Record<string, string> = {
  RECU: "mail-unread-outline", TRANSMIS: "arrow-redo-outline", PRIS_EN_CHARGE: "people-outline", REGLE: "checkmark-circle-outline",
};

/** Icônes discrètes (contour), pour repérer les choix sans lire. */
export const typeIcon: Record<string, string> = { GBV: "shield-outline", SECURITE: "warning-outline" };
export const subtypeIcon: Record<string, string> = {
  VIOL: "alert-circle-outline", AGRESSION_SEXUELLE: "alert-circle-outline", AGRESSION_PHYSIQUE: "hand-left-outline", MARIAGE_FORCE: "people-outline",
  DENI_RESSOURCES: "lock-closed-outline", VIOLENCE_PSYCHOLOGIQUE: "sad-outline", VIOLENCE: "hand-left-outline", MENACE: "warning-outline", TERRORISME: "flash-outline",
};
export const roleIcon: Record<string, string> = {
  RELAIS: "person-outline", POINT_FOCAL: "eye-outline", ACTION_SOCIALE: "business-outline", GESTIONNAIRE: "briefcase-outline",
};
export const categoryIcon: Record<string, string> = { URGENCE: "call-outline", SANTE: "medkit-outline", JUSTICE: "shield-outline", ONG: "people-outline" };
