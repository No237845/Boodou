import { router } from "expo-router";
import React, { useEffect, useState } from "react";

import * as api from "@/api";
import { useDraft } from "@/draft";
import { errorMessage } from "@/errors";
import { useI18n } from "@/i18n";
import { tc } from "@/strings";
import { Banner, Button, Choice, Empty, H1, Loading, Muted, Screen, Stepper } from "@/ui";

/** Étape 3/4 : à qui envoyer — un relais communautaire de la commune, ou directement l'action sociale. */
export default function ReportTo() {
  const { t, lang } = useI18n();
  const { draft, update } = useDraft();
  const [relais, setRelais] = useState<api.Relais[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.getRelais(draft.region!, draft.commune!)
      .then((rows) => {
        setRelais(rows);
        // Pas de relais ici : l'action sociale est le seul choix, on le présélectionne.
        if (rows.length === 0 && draft.assignee_id == null && !draft.target_role) update({ target_role: "ACTION_SOCIALE", assignee_id: null });
      })
      .catch((e) => setError(errorMessage(e, lang)));
  };
  useEffect(load, [draft.region, draft.commune]);

  const chosen = draft.assignee_id != null || draft.target_role === "ACTION_SOCIALE";

  return (
    <Screen footer={<Button variant="primary" icon="arrow-forward-outline" title={tc(lang, "next")} disabled={!chosen} onPress={() => router.push("/report/describe")} />}>
      <Stepper step={3} total={4} label={`${t("report_step", { n: 3, total: 4 })} · ${draft.subtypeLabel} · ${draft.commune}`} />
      <H1>{t("report_recipient")}</H1>
      <Muted>{t("report_recipient_hint")}</Muted>
      {error ? (
        <>
          <Banner kind="error">{error}</Banner>
          <Button icon="refresh-outline" title={tc(lang, "retry")} onPress={load} />
        </>
      ) : null}
      {!relais && !error ? <Loading /> : null}

      {relais?.map((a) => (
        <Choice
          key={a.id}
          icon="person-outline"
          label={a.name}
          sub={[t("recipient_relais"), a.commune, a.organisation, a.phone].filter(Boolean).join(" · ")}
          selected={draft.assignee_id === a.id}
          onPress={() => update({ assignee_id: a.id, assigneeName: a.name, target_role: null })}
        />
      ))}
      {relais && relais.length === 0 ? <Empty icon="people-outline">{t("report_no_relais")}</Empty> : null}
      {relais ? (
        <Choice
          icon="business-outline"
          label={t("recipient_action_sociale")}
          sub={t("recipient_action_sociale_hint")}
          selected={draft.target_role === "ACTION_SOCIALE"}
          onPress={() => update({ assignee_id: null, assigneeName: undefined, target_role: "ACTION_SOCIALE" })}
        />
      ) : null}
    </Screen>
  );
}
