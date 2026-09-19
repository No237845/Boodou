import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import React, { useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";

import * as api from "@/api";
import { useDraft } from "@/draft";
import { errorMessage } from "@/errors";
import { useI18n } from "@/i18n";
import { tc } from "@/strings";
import { radius, space, subtypeIcon, type, typeIcon, useTheme } from "@/theme";
import { Banner, Button, Choice, H1, IconName, Loading, Screen, Stepper } from "@/ui";

/** Étape 1/4 : de quoi s'agit-il.
 *  Deux familles bien séparées (VBG, sécurité). On touche une famille pour
 *  dérouler ses cas ; l'autre se replie. Un seul cas peut être choisi. */
export default function ReportType() {
  const { t, lang } = useI18n();
  const { draft, update } = useDraft();
  const th = useTheme();
  const [types, setTypes] = useState<api.TypeInfo[] | null>(null);
  const [open, setOpen] = useState<api.ReportType | null>(draft.type ?? null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.getTypes(lang ?? "fr").then(setTypes).catch((e) => setError(errorMessage(e, lang)));
  };
  useEffect(load, [lang]);

  return (
    <Screen
      footer={<Button variant="primary" icon="arrow-forward-outline" title={tc(lang, "next")} disabled={!draft.subtype} onPress={() => router.push("/report/where")} />}
    >
      <Stepper step={1} total={4} label={t("report_step", { n: 1, total: 4 })} />
      <H1>{t("report_type")}</H1>
      <Banner kind="lock">{t("report_intro")}</Banner>
      {error ? (
        <>
          <Banner kind="error">{error}</Banner>
          <Button icon="refresh-outline" title={tc(lang, "retry")} onPress={load} />
        </>
      ) : null}
      {!types && !error ? <Loading /> : null}

      {types?.map((ty) => {
        const isOpen = open === ty.code;
        const chosen = draft.type === ty.code ? ty.subtypes.find((s) => s.code === draft.subtype) : undefined;
        return (
          <View
            key={ty.code}
            style={{ borderWidth: 1, borderColor: isOpen || chosen ? th.primary : th.border, borderRadius: radius.lg, marginTop: space.md, backgroundColor: th.surface, overflow: "hidden" }}
          >
            {/* En-tête de la famille : toujours visible, déroule / replie. */}
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ expanded: isOpen }}
              onPress={() => setOpen(isOpen ? null : ty.code)}
              style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: space.md, padding: space.md, backgroundColor: isOpen ? th.primaryLight : th.surface, opacity: pressed ? 0.85 : 1 })}
            >
              <Ionicons name={typeIcon[ty.code] as IconName} size={26} color={th.primary} />
              <View style={{ flex: 1 }}>
                <Text style={[type.h3, { color: th.text }]}>{ty.label}</Text>
                <Text style={[type.bodySm, { color: chosen ? th.primary : th.textSecondary, fontWeight: chosen ? "600" : "400" }]}>
                  {chosen ? chosen.label : ty.subtypes.map((s) => s.label).join(" · ")}
                </Text>
              </View>
              <Ionicons name={isOpen ? "chevron-up" : "chevron-down"} size={22} color={th.textSecondary} />
            </Pressable>

            {/* Les cas de la famille, seulement quand elle est dépliée. */}
            {isOpen ? (
              <View style={{ paddingHorizontal: space.md, paddingBottom: space.md, borderTopWidth: 1, borderTopColor: th.border }}>
                {ty.subtypes.map((s) => (
                  <Choice
                    key={s.code}
                    icon={(subtypeIcon[s.code] ?? "ellipse-outline") as IconName}
                    label={s.label}
                    selected={draft.subtype === s.code}
                    onPress={() => update({ type: ty.code, subtype: s.code, subtypeLabel: s.label })}
                  />
                ))}
              </View>
            ) : null}
          </View>
        );
      })}
    </Screen>
  );
}
