import React from "react";
import { View } from "react-native";

import type { Suggestion } from "./api";
import { useI18n } from "./i18n";
import { space } from "./theme";
import { Banner, Button, Muted } from "./ui";

/** Bouton « Proposer une reformulation » et, une fois la proposition reçue, ce que l'assistant signale. */
export function SuggestBlock({ onPress, loading, suggestion, disabled }: { onPress: () => void; loading: boolean; suggestion: Suggestion | null; disabled?: boolean }) {
  const { t } = useI18n();
  return (
    <View style={{ marginTop: space.sm }}>
      <Button icon="sparkles-outline" title={t("actor_propose")} onPress={onPress} loading={loading} disabled={disabled} />
      <Muted>{t("actor_propose_hint")}</Muted>
      {suggestion ? (
        <Banner kind="info">
          {t("actor_proposed")}
          {suggestion.urgency ? `\n${t("actor_urgency")} : ${suggestion.urgency}.` : ""}
          {suggestion.anonymity_risks.length ? `\n⚠ ${t("actor_to_remove")} : ${suggestion.anonymity_risks.join(" · ")}` : ""}
          {suggestion.missing.length ? `\n${t("actor_missing")} : ${suggestion.missing.join(" · ")}` : ""}
        </Banner>
      ) : null}
    </View>
  );
}
