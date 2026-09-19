import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import React from "react";

import { DraftProvider } from "@/draft";
import { I18nProvider, useI18n } from "@/i18n";
import { SessionProvider } from "@/session";
import { useTheme } from "@/theme";

function Navigator() {
  const th = useTheme();
  const { t } = useI18n();
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: th.bg },
        headerTintColor: th.text,
        headerTitleStyle: { fontWeight: "600", fontSize: 17 },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: th.bg },
        headerBackButtonDisplayMode: "minimal",
      }}
    >
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="lang" options={{ headerShown: false }} />
      <Stack.Screen name="home" options={{ headerShown: false }} />
      <Stack.Screen name="report/type" options={{ title: t("report_title") }} />
      <Stack.Screen name="report/where" options={{ title: t("report_title") }} />
      <Stack.Screen name="report/to" options={{ title: t("report_title") }} />
      <Stack.Screen name="report/describe" options={{ title: t("report_title") }} />
      <Stack.Screen name="report/done" options={{ title: t("confirm_title"), headerBackVisible: false, gestureEnabled: false }} />
      <Stack.Screen name="track" options={{ title: t("track_title") }} />
      <Stack.Screen name="resources" options={{ title: t("resources_title") }} />
      <Stack.Screen name="actor/login" options={{ title: "Espace acteurs" }} />
      <Stack.Screen name="actor/inbox" options={{ title: "Signalements", headerBackVisible: false }} />
      <Stack.Screen name="actor/[id]" options={{ title: "Signalement" }} />
      <Stack.Screen name="actor/new" options={{ title: "Saisir un cas" }} />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <I18nProvider>
      <SessionProvider>
        <DraftProvider>
          <StatusBar style="auto" />
          <Navigator />
        </DraftProvider>
      </SessionProvider>
    </I18nProvider>
  );
}
