import React from "react";
import { View } from "react-native";

import type { Suggestion } from "./api";
import { S } from "./strings";
import { space } from "./theme";
import { Banner, Button, Muted } from "./ui";

/** Bouton « Proposer une reformulation » et, une fois la proposition reçue, ce que l'assistant signale. */
export function SuggestBlock({ onPress, loading, suggestion, disabled }: { onPress: () => void; loading: boolean; suggestion: Suggestion | null; disabled?: boolean }) {
  return (
    <View style={{ marginTop: space.sm }}>
      <Button icon="sparkles-outline" title={S.actor.propose} onPress={onPress} loading={loading} disabled={disabled} />
      <Muted>{S.actor.proposeHint}</Muted>
      {suggestion ? (
        <Banner kind="info">
          {S.actor.proposed}
          {suggestion.urgency ? `\n${S.actor.urgency} : ${suggestion.urgency}.` : ""}
          {suggestion.anonymity_risks.length ? `\n⚠ ${S.actor.toRemove} : ${suggestion.anonymity_risks.join(" · ")}` : ""}
          {suggestion.missing.length ? `\n${S.actor.missing} : ${suggestion.missing.join(" · ")}` : ""}
        </Banner>
      ) : null}
    </View>
  );
}
