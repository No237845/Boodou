import { useLocalSearchParams } from "expo-router";
import React, { useEffect, useState } from "react";
import { ScrollView } from "react-native";

import * as api from "@/api";
import { errorMessage } from "@/errors";
import { useI18n } from "@/i18n";
import { ResourceList } from "@/resources-list";
import { tc } from "@/strings";
import { space } from "@/theme";
import { Banner, Button, Chip, H1, Loading, Screen } from "@/ui";

/** Annuaire filtré : type ou catégorie viennent de l'accueil, la région se choisit ici. */
export default function Resources() {
  const { t, lang } = useI18n();
  const { type, category } = useLocalSearchParams<{ type?: api.ReportType; category?: string }>();
  const [regions, setRegions] = useState<string[]>([]);
  const [region, setRegion] = useState<string>("");
  const [rows, setRows] = useState<api.Resource[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getRegions().then((r) => setRegions(r.map((x) => x.name))).catch(() => {});
  }, []);

  const load = () => {
    setError(null);
    setRows(null);
    api.getResources({ type, category, region: region || undefined }).then(setRows).catch((e) => setError(errorMessage(e, lang)));
  };
  useEffect(load, [type, category, region]);

  return (
    <Screen>
      <H1>{t("resources_title")}</H1>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm, paddingVertical: space.xs }}>
        <Chip icon="globe-outline" selected={!region} label={t("resources_all_regions")} onPress={() => setRegion("")} />
        {regions.map((r) => (
          <Chip key={r} selected={region === r} label={r} onPress={() => setRegion(r)} />
        ))}
      </ScrollView>
      {error ? (
        <>
          <Banner kind="error">{error}</Banner>
          <Button icon="refresh-outline" title={tc(lang, "retry")} onPress={load} />
        </>
      ) : null}
      {rows === null && !error ? <Loading /> : null}
      {rows ? <ResourceList resources={rows} /> : null}
    </Screen>
  );
}
