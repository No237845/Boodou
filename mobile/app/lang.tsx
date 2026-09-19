import { router } from "expo-router";
import React from "react";
import { View } from "react-native";

import { LANGS } from "@/config";
import { useI18n } from "@/i18n";
import { space, useTheme } from "@/theme";
import { Choice, H1, IconBadge, Muted, Screen } from "@/ui";

// Salutation dans chaque langue : quelqu'un qui ne lit pas le français
// reconnaît la sienne au premier coup d'œil.
const GREETING: Record<string, string> = { fr: "Bonjour", mos: "Ne y windga", dyu: "I ni sɔgɔma", en: "Hello" };
const PROMPT: Record<string, string> = { fr: "Choisissez votre langue", mos: "Yãk y buud-gomde", dyu: "I ka kan sugandi", en: "Choose your language" };

export default function Lang() {
  const { setLang } = useI18n();
  const th = useTheme();
  return (
    <Screen>
      <View style={{ marginTop: space.xxl }}>
        <IconBadge icon="shield-checkmark-outline" color={th.primary} />
        <H1 style={{ textAlign: "center" }}>Boodou</H1>
        {LANGS.map((l) => (
          <Muted key={l.code} style={{ textAlign: "center", marginVertical: 0 }}>{PROMPT[l.code]}</Muted>
        ))}
      </View>
      <View style={{ marginTop: space.xl }}>
        {LANGS.map((l) => (
          <Choice
            key={l.code}
            label={l.name}
            sub={GREETING[l.code]}
            onPress={() => {
              setLang(l.code);
              router.replace("/home");
            }}
          />
        ))}
      </View>
    </Screen>
  );
}
