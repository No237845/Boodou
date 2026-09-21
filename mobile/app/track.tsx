import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Text, View } from "react-native";

import * as api from "@/api";
import { errorMessage } from "@/errors";
import { useI18n } from "@/i18n";
import { mono, space, statusColor, statusIcon, type, useTheme } from "@/theme";
import { Banner, Button, Card, CodeBox, Field, H1, IconBadge, IconName, P, Screen } from "@/ui";

/** Suivi par code. Volontairement : ni type, ni région, ni récit — seulement l'état.
 *  Le code n'est pas mémorisé dans l'app. */
export default function Track() {
  const { t, lang } = useI18n();
  const th = useTheme();
  const colors = statusColor(th);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<api.Track | null>(null);

  const lookup = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.track(code.trim(), lang ?? "fr"));
    } catch (e) {
      setError(errorMessage(e, lang));
    } finally {
      setBusy(false);
    }
  };

  const fmt = (iso: string) => new Date(iso).toLocaleDateString();
  const current = result ? api.STATUSES.indexOf(result.status) : -1;

  return (
    <Screen>
      {!result ? <IconBadge icon="search-outline" color={th.primary} /> : null}
      <H1 style={{ textAlign: result ? "left" : "center" }}>{t("track_title")}</H1>
      <P style={{ textAlign: result ? "left" : "center" }}>{t("track_intro")}</P>
      {error ? <Banner kind="error">{error}</Banner> : null}
      <Field
        label={t("track_code_label")}
        icon="key-outline"
        value={code}
        onChangeText={setCode}
        autoCapitalize="characters"
        autoCorrect={false}
        placeholder="XXXXX-XXXXX"
        maxLength={16}
        hint={t("track_code_hint")}
        style={{ fontFamily: mono, fontSize: 20, fontWeight: "700", letterSpacing: 2 }}
      />
      <Button variant="primary" icon="search-outline" title={t("track_submit")} loading={busy} disabled={code.trim().length < 10} onPress={lookup} />

      {result ? (
        <Card style={{ marginTop: space.lg }}>
          <CodeBox code={result.code} />
          {/* Frise verticale : les étapes passées en couleur, l'étape actuelle en gras, les suivantes grisées. */}
          {api.STATUSES.map((st, i) => {
            const done = i < current;
            const on = i === current;
            const color = on || done ? colors[st] : th.border;
            return (
              <View key={st} style={{ flexDirection: "row", gap: space.md }}>
                <View style={{ alignItems: "center", width: 36 }}>
                  <View style={{ width: 32, height: 32, borderRadius: 16, backgroundColor: on ? color : th.surface, alignItems: "center", justifyContent: "center", borderWidth: 1.5, borderColor: color }}>
                    <Ionicons name={(done ? "checkmark" : statusIcon[st]) as IconName} size={16} color={on ? "#fff" : done ? color : th.textDisabled} />
                  </View>
                  {i < api.STATUSES.length - 1 ? <View style={{ width: 2, flex: 1, minHeight: 20, backgroundColor: done ? colors[st] : th.border }} /> : null}
                </View>
                <View style={{ flex: 1, paddingBottom: space.md }}>
                  <Text style={[type.h3, { color: on || done ? th.text : th.textDisabled, marginTop: 6 }]}>{t("status_" + st)}</Text>
                  {on ? <Text style={[type.bodySm, { color: th.textSecondary }]}>{t("status_" + st + "_help")}</Text> : null}
                </View>
              </View>
            );
          })}
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <Ionicons name="calendar-outline" size={14} color={th.textSecondary} />
            <Text style={[type.caption, { color: th.textSecondary }]}>
              {t("track_sent_on")} {fmt(result.created_at)}
              {result.status_at ? `  ·  ${t("track_updated_on")} ${fmt(result.status_at)}` : ""}
            </Text>
          </View>
          {result.partner_note ? (
            <Banner kind="success" title={t("track_partner_note")}>{result.partner_note}</Banner>
          ) : null}
        </Card>
      ) : null}
    </Screen>
  );
}
