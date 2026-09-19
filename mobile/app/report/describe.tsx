import { router } from "expo-router";
import React, { useState } from "react";

import * as api from "@/api";
import { MAX_DESCRIPTION } from "@/config";
import { useDraft } from "@/draft";
import { errorMessage } from "@/errors";
import { useI18n } from "@/i18n";
import { Banner, Button, Field, H1, Screen, Stepper } from "@/ui";
import { VoiceInput } from "@/voice";

/** Étape 4/4 : que s'est-il passé. L'envoi se fait ici. */
export default function ReportDescribe() {
  const { t, lang } = useI18n();
  const { draft, update } = useDraft();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const text = draft.description ?? "";

  const send = async () => {
    setSending(true);
    setError(null);
    try {
      const r = await api.postReport({
        subtype: draft.subtype!,
        region: draft.region!,
        commune: draft.commune!,
        description: text.trim(),
        assignee_id: draft.assignee_id ?? null,
        target_role: draft.assignee_id != null ? null : draft.target_role ?? "ACTION_SOCIALE",
        lang: lang ?? "fr",
      });
      router.replace({ pathname: "/report/done", params: { code: r.code, subtype: draft.subtype!, region: draft.region!, type: draft.type! } });
    } catch (e) {
      setError(errorMessage(e, lang));
      setSending(false);
    }
  };

  return (
    <Screen
      footer={<Button variant="primary" icon="send-outline" title={t("report_submit")} loading={sending} disabled={text.trim().length === 0} onPress={send} />}
    >
      <Stepper step={4} total={4} label={`${t("report_step", { n: 4, total: 4 })} · ${draft.subtypeLabel} · ${draft.commune} · ${draft.assigneeName ?? t("recipient_action_sociale")}`} />
      <H1>{t("report_description")}</H1>
      <Banner kind="warn">{t("report_intro")}</Banner>
      {error ? <Banner kind="error">{error}</Banner> : null}
      <VoiceInput onText={(spoken) => update({ description: (text ? text.trimEnd() + "\n" : "") + spoken })} />
      <Field
        multiline
        value={text}
        onChangeText={(v) => update({ description: v.slice(0, MAX_DESCRIPTION) })}
        maxLength={MAX_DESCRIPTION}
        hint={`🔒 ${t("report_description_hint")}  (${text.length}/${MAX_DESCRIPTION})`}
      />
    </Screen>
  );
}
