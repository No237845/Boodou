/** Petit stockage clé/valeur : SecureStore (chiffré par l'OS) sur téléphone, localStorage sur web.
 *  N'y vont que la langue choisie et le jeton d'un acteur connecté. Jamais un
 *  code de suivi ni un récit : sur un téléphone partagé, rien ne doit trahir
 *  qu'un signalement a été fait. */

import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

const storage = {
  async get(key: string): Promise<string | null> {
    try {
      if (Platform.OS === "web") return globalThis.localStorage?.getItem(key) ?? null;
      return await SecureStore.getItemAsync(key);
    } catch {
      return null;
    }
  },
  async set(key: string, value: string): Promise<void> {
    try {
      if (Platform.OS === "web") globalThis.localStorage?.setItem(key, value);
      else await SecureStore.setItemAsync(key, value);
    } catch {
      /* stockage indisponible : l'app fonctionne quand même, sans mémoire */
    }
  },
  async remove(key: string): Promise<void> {
    try {
      if (Platform.OS === "web") globalThis.localStorage?.removeItem(key);
      else await SecureStore.deleteItemAsync(key);
    } catch {
      /* idem */
    }
  },
};

export default storage;
