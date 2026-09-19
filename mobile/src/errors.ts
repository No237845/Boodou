import { ApiError } from "./api";
import { translate } from "./i18n";
import { S, tc } from "./strings";

/** Message lisible pour une erreur d'appel API, dans la langue de l'usager. */
export function errorMessage(e: unknown, lang: string | null): string {
  const l = lang ?? "fr";
  if (e instanceof ApiError) {
    if (e.status === 0) return tc(l, "network");
    if (e.status === 429) return translate(l, "track_too_many");
    if (e.status === 401) return S.actor.bad_credentials;
    // Les clés d'erreur du serveur (report_error_*, track_*) sont traduites côté locales.
    if (e.detail === "report_error_summary_required") return S.actor.summaryMissing;
    if (e.detail === "ai_unavailable" || e.status === 503) return S.actor.aiUnavailable;
    if (e.detail.startsWith("report_error_") || e.detail.startsWith("track_")) {
      return translate(l, e.detail, { max: 2000 });
    }
    if (e.detail === "not_found") return translate(l, "track_not_found");
  }
  return tc(l, "server");
}
