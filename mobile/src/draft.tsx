/** Brouillon d'un signalement, le temps des 4 écrans. En mémoire seulement :
 *  quitter l'app l'efface, c'est voulu. */

import React, { createContext, useContext, useMemo, useState } from "react";

import type { ActorRole, ReportType } from "./api";

export type Draft = {
  type?: ReportType;
  subtype?: string;
  subtypeLabel?: string;
  region?: string;
  commune?: string;
  assignee_id?: number | null;
  assigneeName?: string;
  target_role?: ActorRole | null;
  description?: string;
};

type DraftCtx = { draft: Draft; update: (patch: Partial<Draft>) => void; reset: () => void };

const Ctx = createContext<DraftCtx>({ draft: {}, update: () => {}, reset: () => {} });

export function DraftProvider({ children }: { children: React.ReactNode }) {
  const [draft, setDraft] = useState<Draft>({});
  const value = useMemo<DraftCtx>(
    () => ({ draft, update: (patch) => setDraft((d) => ({ ...d, ...patch })), reset: () => setDraft({}) }),
    [draft],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useDraft = () => useContext(Ctx);
