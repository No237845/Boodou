import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import React, { useEffect, useState } from "react";
import { Linking, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "@/api";
import { useDraft } from "@/draft";
import { useI18n } from "@/i18n";
import { useSession } from "@/session";
import { tc } from "@/strings";
import { mono, radius, space, type, useTheme } from "@/theme";
import { ActionCard, Banner, Button, Caption, H1, Screen, SectionTitle } from "@/ui";

export default function Home() {
  const { t, lang } = useI18n();
  const { actor } = useSession();
  const { reset } = useDraft();
  const th = useTheme();
  const insets = useSafeAreaInsets();
  const [emergency, setEmergency] = useState<api.Resource[]>([]);

  useEffect(() => {
    // Les numéros d'urgence : affichés si le serveur répond, sinon on ne bloque rien.
    api.getResources({ category: "URGENCE" }).then(setEmergency).catch(() => {});
  }, []);

  return (
    <Screen>
      {/* Barre de marque, comme l'en-tête du site : nom à gauche, langue à droite. */}
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingTop: insets.top, paddingBottom: space.sm, borderBottomWidth: 1, borderBottomColor: th.border }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: space.sm }}>
          <Ionicons name="shield-checkmark-outline" size={22} color={th.primary} />
          <Text style={[type.h3, { color: th.text }]}>{t("app_name")}</Text>
        </View>
        <Pressable onPress={() => router.push("/lang")} accessibilityRole="button" style={{ flexDirection: "row", alignItems: "center", gap: 4, borderWidth: 1, borderColor: th.border, paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.full }}>
          <Ionicons name="language-outline" size={14} color={th.textSecondary} />
          <Text style={[type.caption, { color: th.text }]}>{lang?.toUpperCase()}</Text>
        </Pressable>
      </View>

      <H1>{t("tagline")}</H1>
      <Banner kind="lock">{t("anon_banner")}</Banner>

      <ActionCard
        hero
        icon="megaphone-outline"
        title={t("home_report")}
        sub={t("home_report_sub")}
        onPress={() => {
          reset();
          router.push("/report/type");
        }}
      />
      <ActionCard icon="heart-outline" title={t("home_help_gbv")} sub={t("home_help_gbv_sub")} onPress={() => router.push({ pathname: "/resources", params: { type: "GBV" } })} />
      <ActionCard icon="shield-outline" title={t("home_help_security")} sub={t("home_help_security_sub")} onPress={() => router.push({ pathname: "/resources", params: { category: "JUSTICE" } })} />
      <ActionCard icon="chatbubbles-outline" title={t("home_talk")} sub={t("home_talk_sub")} onPress={() => router.push({ pathname: "/resources", params: { category: "ONG" } })} />
      <ActionCard icon="search-outline" title={t("home_track")} sub={t("home_track_sub")} onPress={() => router.push("/track")} />

      {emergency.length > 0 ? (
        <View style={{ backgroundColor: th.warningLight, borderRadius: radius.lg, padding: space.md, marginTop: space.lg }}>
          <SectionTitle icon="call-outline">{t("home_emergency")}</SectionTitle>
          {emergency.map((r) => (
            <Pressable key={r.name} accessibilityRole="button" onPress={() => Linking.openURL(`tel:${r.phone}`)} style={{ flexDirection: "row", alignItems: "center", gap: space.sm, paddingVertical: 6 }}>
              <Text style={{ fontFamily: mono, fontSize: 22, fontWeight: "700", color: th.primary, minWidth: 44 }}>{r.phone}</Text>
              <Text style={[type.body, { color: th.text, flex: 1 }]}>{r.name}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}

      <View style={{ marginTop: space.xl, alignItems: "center" }}>
        <Button
          variant="ghost"
          icon="people-outline"
          title={actor ? `${tc(lang, "actors")} · ${actor.name}` : tc(lang, "actors")}
          onPress={() => router.push(actor ? "/actor/inbox" : "/actor/login")}
        />
        <Caption style={{ textAlign: "center" }}>{tc(lang, "actors_sub")}</Caption>
        <Caption style={{ textAlign: "center", marginTop: space.lg }}>{t("home_whatsapp")}</Caption>
      </View>
    </Screen>
  );
}
