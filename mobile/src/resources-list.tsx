import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Linking, Text, View } from "react-native";

import type { Resource } from "./api";
import { useI18n } from "./i18n";
import { categoryIcon, space, type, useTheme } from "./theme";
import { Button, Card, Empty, IconName, SectionTitle } from "./ui";

const ORDER: Resource["category"][] = ["URGENCE", "SANTE", "JUSTICE", "ONG"];

/** Ressources groupées par catégorie, dans l'ordre du web. Le bouton d'appel est vert : l'aide est là. */
export function ResourceList({ resources }: { resources: Resource[] }) {
  const { t } = useI18n();
  const th = useTheme();
  if (resources.length === 0) return <Empty icon="search-outline">{t("resources_none")}</Empty>;
  return (
    <>
      {ORDER.filter((c) => resources.some((r) => r.category === c)).map((cat) => (
        <View key={cat}>
          <SectionTitle icon={categoryIcon[cat] as IconName}>{t("cat_" + cat)}</SectionTitle>
          {resources
            .filter((r) => r.category === cat)
            .map((r, i) => (
              <Card key={r.name + i}>
                <Text style={[type.h3, { color: th.text, marginTop: 0 }]}>{r.name}</Text>
                <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
                  <Ionicons name="location-outline" size={14} color={th.textSecondary} />
                  <Text style={[type.bodySm, { color: th.textSecondary }]}>
                    {r.city || (r.region === "*" ? t("resources_national") : r.region)}
                    {r.hours ? `  ·  ${r.hours}` : ""}
                  </Text>
                </View>
                {r.notes ? <Text style={[type.bodySm, { color: th.text, marginTop: space.xs }]}>{r.notes}</Text> : null}
                {r.phone ? (
                  <Button variant="primary" icon="call-outline" title={`${t("resources_call")}  ${r.phone}`} onPress={() => Linking.openURL(`tel:${r.phone}`)} style={{ marginTop: space.sm }} />
                ) : null}
              </Card>
            ))}
        </View>
      ))}
    </>
  );
}
