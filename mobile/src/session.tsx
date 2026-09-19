/** Session d'un acteur connecté (relais, point focal…). Jeton en SecureStore. */

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import * as api from "./api";
import storage from "./storage";

type Session = {
  ready: boolean;
  token: string | null;
  actor: api.Actor | null;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const Ctx = createContext<Session>({ ready: false, token: null, actor: null, signIn: async () => {}, signOut: async () => {} });

const KEY = "actor_token";

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [actor, setActor] = useState<api.Actor | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      const saved = await storage.get(KEY);
      if (saved) {
        try {
          setActor(await api.me(saved));
          setToken(saved);
        } catch (e) {
          // Jeton expiré ou compte désactivé : on oublie. Pas de réseau : on garde
          // le jeton, l'acteur réessaiera depuis la boîte de réception.
          if (e instanceof api.ApiError && e.status === 401) await storage.remove(KEY);
          else setToken(saved);
        }
      }
      setReady(true);
    })();
  }, []);

  const value = useMemo<Session>(
    () => ({
      ready,
      token,
      actor,
      signIn: async (username, password) => {
        const r = await api.login(username.trim(), password);
        await storage.set(KEY, r.token);
        setToken(r.token);
        setActor(r.actor);
      },
      signOut: async () => {
        if (token) api.logout(token).catch(() => {});
        await storage.remove(KEY);
        setToken(null);
        setActor(null);
      },
    }),
    [ready, token, actor],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useSession = () => useContext(Ctx);
