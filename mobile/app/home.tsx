import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import React, { useEffect, useState } from "react";
import { Image, Linking, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as api from "@/api";
import { useDraft } from "@/draft";
import { useI18n } from "@/i18n";
import { useSession } from "@/session";
import { tc } from "@/strings";
import { radius, space, type, useTheme } from "@/theme";
import { ActionCard, Banner, Button, Caption, H1, Screen } from "@/ui";

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
          <Image source={require("../assets/logo.png")} style={{ width: 34, height: 24 }} resizeMode="contain" accessible={false} />
          <Text style={[type.h3, { color: th.text }]}>{t("app_name")}</Text>
        </View>
        <Pressable onPress={() => router.push("/lang")} accessibilityRole="button" style={{ flexDirection: "row", alignItems: "center", gap: 4, borderWidth: 1, borderColor: th.border, paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.full }}>
          <Ionicons name="language-outline" size={14} color={th.textSecondary} />
          <Text style={[type.caption, { color: th.text }]}>{lang?.toUpperCase()}</Text>
        </Pressable>
      </View>

      <H1>{t("tagline")}</H1>

      {/* Urgence d'abord, au-dessus de tout : un chiffre se lit dans toutes les langues. */}
      {emergency.length > 0 ? (
        <View style={{ backgroundColor: th.accentLight, borderWidth: 1, borderColor: th.accent, borderRadius: radius.lg, padding: 12, marginBottom: space.sm }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginBottom: space.sm }}>
            <Ionicons name="call-outline" size={18} color={th.accent} />
            <Text style={[type.h3, { color: th.accent, fontSize: 16 }]}>{t("home_emergency")}</Text>
          </View>
          <View style={{ flexDirection: "row", gap: space.sm }}>
            {emergency.map((r) => (
              <Pressable
                key={r.name}
                accessibilityRole="button"
                accessibilityLabel={`${r.phone} ${r.name}`}
                onPress={() => Linking.openURL(`tel:${r.phone}`)}
                style={({ pressed }) => ({ flex: 1, minHeight: 64, alignItems: "center", justifyContent: "center", padding: 6, borderRadius: radius.md, borderWidth: 1, borderColor: th.border, backgroundColor: th.surface, opacity: pressed ? 0.8 : 1 })}
              >
                <Text style={{ fontSize: 28, lineHeight: 32, fontWeight: "700", color: th.accent }}>{r.phone}</Text>
                <Text style={[type.caption, { color: th.textSecondary, textAlign: "center" }]} numberOfLines={2}>{r.name}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      ) : null}

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

      <Banner kind="lock">{t("anon_banner")}</Banner>

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
