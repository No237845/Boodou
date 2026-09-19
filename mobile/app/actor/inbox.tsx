import { Ionicons } from "@expo/vector-icons";
import { Redirect, router, useFocusEffect } from "expo-router";
import React, { useCallback, useState } from "react";
import { RefreshControl, ScrollView, Text, View } from "react-native";

import * as api from "@/api";
import { errorMessage } from "@/errors";
import { useI18n } from "@/i18n";
import { useSession } from "@/session";
import { S } from "@/strings";
import { mono, roleIcon, space, statusColor, statusIcon, subtypeIcon, type, useTheme } from "@/theme";
import { Banner, Button, Card, Chip, Empty, IconName, Loading, Pill, Screen } from "@/ui";

const ROLE_INTRO: Record<api.ActorRole, (a: api.Actor) => string> = {
  RELAIS: (a) => `Les signalements que des personnes de ${a.commune ?? a.region} vous ont adressés, et ceux que vous avez saisis ou transmis.`,
  POINT_FOCAL: (a) => `Tous les cas VBG de la région ${a.region} pas encore pris en charge. Relisez, reformulez, transmettez.`,
  ACTION_SOCIALE: (a) => `Les signalements adressés à l'action sociale (${a.region}) et ceux que vous avez pris en charge. Ouvrez un dossier pour le prendre en charge ou le déclarer réglé.`,
  GESTIONNAIRE: (a) => `Les signalements qui vous sont adressés (${a.region}) et ceux que vous avez pris en charge. Ouvrez un dossier pour le prendre en charge ou le déclarer réglé.`,
};

export default function Inbox() {
  const { ready, token, actor, signOut } = useSession();
  const { t } = useI18n();
  const th = useTheme();
  const colors = statusColor(th);
  const [status, setStatus] = useState<api.ReportStatus | "">("");
  const [rows, setRows] = useState<api.InboxItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      setRows(await api.inbox(token, status));
    } catch (e) {
      if (e instanceof api.ApiError && e.status === 401) {
        await signOut();
        router.replace("/actor/login");
        return;
      }
      setError(errorMessage(e, "fr"));
    }
  }, [token, status]);

  // Recharge à chaque retour sur l'écran : une fiche vient peut-être d'être transmise.
  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  if (!ready) return <Loading />;
  if (!token) return <Redirect href="/actor/login" />;

  const counts = (rows ?? []).reduce<Record<string, number>>((acc, r) => ({ ...acc, [r.status]: (acc[r.status] ?? 0) + 1 }), {});

  return (
    <Screen scroll={false} padded={false}>
      <ScrollView
        contentContainerStyle={{ padding: space.md, paddingBottom: space.xl }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}
      >
        {/* Qui je suis, où, et déconnexion. */}
        {actor ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: space.sm, paddingBottom: space.sm, borderBottomWidth: 1, borderBottomColor: th.border }}>
            <Ionicons name={roleIcon[actor.role] as IconName} size={22} color={th.primary} />
            <View style={{ flex: 1 }}>
              <Text style={[type.body, { fontWeight: "600", color: th.text }]}>{actor.name}</Text>
              <Text style={[type.caption, { color: th.textSecondary }]}>{S.roles[actor.role]} · {actor.commune ?? actor.region}</Text>
            </View>
            <Button small variant="ghost" icon="log-out-outline" title={S.actor.logout} onPress={async () => { await signOut(); router.replace("/home"); }} />
          </View>
        ) : null}
        {actor ? <Text style={[type.bodySm, { color: th.textSecondary, marginTop: space.sm }]}>{ROLE_INTRO[actor.role](actor)}</Text> : null}

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm, paddingVertical: space.sm + 4 }}>
          <Chip icon="albums-outline" selected={status === ""} label={S.actor.all} onPress={() => setStatus("")} />
          {api.STATUSES.map((st) => (
            <Chip key={st} icon={statusIcon[st] as IconName} selected={status === st} label={counts[st] && status === "" ? `${S.statuses[st]} (${counts[st]})` : S.statuses[st]} onPress={() => setStatus(st)} />
          ))}
        </ScrollView>
        {actor?.must_summarize ? <Button variant="primary" icon="add-outline" title={S.actor.newCase} onPress={() => router.push("/actor/new")} /> : null}

        {error ? <Banner kind="error">{error}</Banner> : null}
        {rows === null && !error ? <Loading /> : null}
        {rows?.length === 0 ? <Empty icon="mail-open-outline">{S.actor.empty}</Empty> : null}
        {rows?.map((r) => (
          <Card key={r.id} accent={colors[r.status]} onPress={() => router.push({ pathname: "/actor/[id]", params: { id: r.id } })}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Text style={{ fontFamily: mono, fontSize: 15, fontWeight: "700", color: th.text }}>{r.code}</Text>
              <Pill icon={statusIcon[r.status] as IconName} label={S.statuses[r.status]} color={colors[r.status]} />
            </View>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
              <Ionicons name={((r.subtype && subtypeIcon[r.subtype]) || "alert-circle") as IconName} size={16} color={th.primary} />
              <Text style={[type.bodySm, { fontWeight: "600", color: th.text, flex: 1 }]}>
                {t("type_" + r.type)}{r.subtype ? ` · ${t("subtype_" + r.subtype)}` : ""}
              </Text>
            </View>
            <Text style={[type.caption, { color: th.textSecondary }]}>
              {r.commune ?? r.region} · {new Date(r.created_at).toLocaleDateString()} · {S.actor.with} {r.assignee ?? (r.target_role ? S.roles[r.target_role] : S.actor.unassigned)}
            </Text>
            <Text numberOfLines={2} style={[type.bodySm, { color: th.text, marginTop: 2 }]}>
              {r.summary ?? r.description ?? (r.legacy ? "🔒 ancien format" : "—")}
            </Text>
          </Card>
        ))}
      </ScrollView>
    </Screen>
  );
}
