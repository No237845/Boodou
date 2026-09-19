/** Client de l'API Boodou (app/routers/api.py). Un seul point d'entrée réseau. */

import * as FileSystem from "expo-file-system/legacy";

import { API_URL } from "./config";

export type ReportType = "GBV" | "SECURITE";
export type ActorRole = "RELAIS" | "POINT_FOCAL" | "ACTION_SOCIALE" | "GESTIONNAIRE";
export type ReportStatus = "RECU" | "TRANSMIS" | "PRIS_EN_CHARGE" | "REGLE";
export const STATUSES: ReportStatus[] = ["RECU", "TRANSMIS", "PRIS_EN_CHARGE", "REGLE"];

export type TypeInfo = { code: ReportType; label: string; subtypes: { code: string; label: string }[] };
export type Region = { name: string; communes: string[] };
export type Relais = { id: number; name: string; organisation: string | null; commune: string | null; phone: string | null };
export type Resource = {
  name: string; category: "URGENCE" | "SANTE" | "JUSTICE" | "ONG"; phone: string | null;
  region: string; city: string | null; hours: string | null; notes: string | null;
};
export type Track = { code: string; status: ReportStatus; created_at: string; status_at: string | null; partner_note: string | null };
export type Actor = {
  id: number; username: string; name: string; role: ActorRole; organisation: string | null;
  region: string; commune: string | null; can_forward_to: ActorRole[]; can_set_status: boolean; must_summarize: boolean; ai_available: boolean;
};
export type InboxItem = {
  code: string; id: string; type: ReportType; subtype: string | null; region: string; commune: string | null;
  channel: string; lang: string; created_at: string; status: ReportStatus; status_at: string | null;
  partner_note: string | null; assignee: string | null; target_role: ActorRole | null;
  description: string | null; summary: string | null; summary_by: string | null; summary_at: string | null; legacy: boolean;
};
export type Event = { kind: "CREATED" | "FORWARDED" | "STATUS"; at: string; by: string | null; by_id: number | null; to: string | null; to_role: ActorRole | null; status: ReportStatus | null; note: string | null };
export type InboxDetail = InboxItem & { events: Event[] };

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

async function call<T>(path: string, init: RequestInit = {}, token?: string | null): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json", ...(init.headers as Record<string, string>) };
  if (init.body) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  let res: Response;
  try {
    res = await fetch(API_URL + path, { ...init, headers });
  } catch {
    throw new ApiError(0, "network");
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, typeof body.detail === "string" ? body.detail : "error");
  return body as T;
}

// --------------------------------------------------------------------------- public

export const getTypes = (lang: string) => call<TypeInfo[]>(`/api/types?lang=${lang}`);
export const getRegions = () => call<Region[]>("/api/regions");
export const getRelais = (region: string, commune: string) =>
  call<Relais[]>(`/api/relais?region=${encodeURIComponent(region)}&commune=${encodeURIComponent(commune)}`);
export const getResources = (params: { type?: ReportType; subtype?: string; region?: string; category?: string }) => {
  const q = Object.entries(params).filter(([, v]) => v).map(([k, v]) => `${k}=${encodeURIComponent(v!)}`).join("&");
  return call<Resource[]>(`/api/resources${q ? "?" + q : ""}`);
};
export const track = (code: string) => call<Track>(`/api/reports/${encodeURIComponent(code)}`);
export const getFeatures = () => call<{ speech: boolean }>("/api/features");

/** Envoie un enregistrement (uri local) et rend le texte transcrit. L'audio n'est pas conservé côté serveur.
 *  Passe par l'upload natif d'Expo : `fetch` + FormData avec un fichier échoue en « Network request failed »
 *  sur une partie des téléphones Android. */
export async function transcribe(uri: string, lang: string): Promise<string> {
  const name = uri.split("/").pop() || "audio.m4a";
  const mimeType = name.endsWith(".3gp") ? "audio/3gpp" : "audio/mp4";
  let res: FileSystem.FileSystemUploadResult;
  try {
    res = await FileSystem.uploadAsync(API_URL + "/api/transcribe", uri, {
      httpMethod: "POST",
      uploadType: FileSystem.FileSystemUploadType.MULTIPART,
      fieldName: "audio",
      mimeType,
      parameters: { lang },
      headers: { Accept: "application/json" },
    });
  } catch (e) {
    throw new ApiError(0, e instanceof Error ? e.message : "network");
  }
  let body: { text?: string; detail?: string } = {};
  try {
    body = JSON.parse(res.body || "{}");
  } catch {
    /* corps non JSON : traité comme une erreur ci-dessous */
  }
  if (res.status < 200 || res.status >= 300) throw new ApiError(res.status, typeof body.detail === "string" ? body.detail : "error");
  return String(body.text ?? "");
}

export type NewReport = {
  subtype: string; region: string; commune: string; description: string;
  assignee_id?: number | null; target_role?: ActorRole | null; lang: string; summary?: string;
};
export const postReport = (payload: NewReport, token?: string | null) =>
  call<{ code: string }>("/api/reports", { method: "POST", body: JSON.stringify({ ...payload, channel: "MOBILE" }) }, token);

// --------------------------------------------------------------------------- acteurs

export const login = (username: string, password: string) =>
  call<{ token: string; actor: Actor }>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
export const logout = (token: string) => call<void>("/api/auth/logout", { method: "POST" }, token);
export const me = (token: string) => call<Actor>("/api/me", {}, token);
export const inbox = (token: string, status?: ReportStatus | "") =>
  call<InboxItem[]>(`/api/inbox${status ? "?status=" + status : ""}`, {}, token);
export const inboxItem = (token: string, id: string) => call<InboxDetail>(`/api/inbox/${id}`, {}, token);
export const targets = (token: string) => call<Relais[]>("/api/targets", {}, token);
export const forward = (token: string, id: string, body: { to_actor_id?: number; to_role?: ActorRole; summary?: string; note?: string }) =>
  call<InboxItem>(`/api/inbox/${id}/forward`, { method: "POST", body: JSON.stringify(body) }, token);
export type Suggestion = { summary: string; urgency: string; anonymity_risks: string[]; missing: string[] };
/** Proposition de reformulation pour un récit en cours de saisie (rien n'est enregistré). */
export const reformulate = (token: string, body: { text: string; region?: string; commune?: string; subtype?: string }) =>
  call<Suggestion>("/api/ai/reformulate", { method: "POST", body: JSON.stringify(body) }, token);
/** Proposition de reformulation du récit d'un signalement reçu (rien n'est enregistré). */
export const suggestSummary = (token: string, id: string) =>
  call<Suggestion>(`/api/inbox/${id}/suggest-summary`, { method: "POST", body: "{}" }, token);
export const updateSummary = (token: string, id: string, summary: string) =>
  call<InboxItem>(`/api/inbox/${id}/summary`, { method: "POST", body: JSON.stringify({ summary }) }, token);
export const setStatus = (token: string, id: string, body: { status: ReportStatus; note?: string }) =>
  call<InboxItem>(`/api/inbox/${id}/status`, { method: "POST", body: JSON.stringify(body) }, token);
