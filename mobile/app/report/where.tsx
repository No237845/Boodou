import { router } from "expo-router";
import React, { useEffect, useState } from "react";
import { View } from "react-native";

import * as api from "@/api";
import { useDraft } from "@/draft";
import { errorMessage } from "@/errors";
import { useI18n } from "@/i18n";
import { tc } from "@/strings";
import { Banner, Button, Chip, Choice, H1, Loading, Muted, Screen, SectionTitle, Stepper } from "@/ui";

/** Étape 2/4 : région (puces) puis commune (liste). */
export default function ReportWhere() {
  const { t, lang } = useI18n();
  const { draft, update } = useDraft();
  const [regions, setRegions] = useState<api.Region[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.getRegions().then(setRegions).catch((e) => setError(errorMessage(e, lang)));
  };
  useEffect(load, []);

  const region = regions?.find((r) => r.name === draft.region);

  return (
    <Screen
      footer={<Button variant="primary" icon="arrow-forward-outline" title={tc(lang, "next")} disabled={!draft.region || !draft.commune} onPress={() => router.push("/report/to")} />}
    >
      <Stepper step={2} total={4} label={`${t("report_step", { n: 2, total: 4 })} · ${draft.subtypeLabel ?? ""}`} />
      {error ? (
        <>
          <Banner kind="error">{error}</Banner>
          <Button icon="refresh-outline" title={tc(lang, "retry")} onPress={load} />
        </>
      ) : null}
      {!regions && !error ? <Loading /> : null}

      {regions ? (
        <>
          <H1>{t("report_region")}</H1>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {regions.map((r) => (
              <Chip
                key={r.name}
                label={r.name}
                selected={draft.region === r.name}
                onPress={() => update({ region: r.name, commune: undefined, assignee_id: undefined, assigneeName: undefined })}
              />
            ))}
          </View>

          {region ? (
            <>
              <SectionTitle icon="location-outline">{t("report_commune")}</SectionTitle>
              <Muted>{t("report_commune_hint")}</Muted>
              {region.communes.map((c) => (
                <Choice key={c} icon="location-outline" label={c} selected={draft.commune === c} onPress={() => update({ commune: c, assignee_id: undefined, assigneeName: undefined })} />
              ))}
            </>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}
