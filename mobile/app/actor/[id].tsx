import { Ionicons } from "@expo/vector-icons";
import { Redirect, router, useLocalSearchParams } from "expo-router";
import React, { useEffect, useState } from "react";
import { Text, View } from "react-native";

import * as api from "@/api";
import { MAX_DESCRIPTION, NOTE_MAX } from "@/config";
import { errorMessage } from "@/errors";
import { useI18n } from "@/i18n";
import { useSession } from "@/session";
import { S } from "@/strings";
import { SuggestBlock } from "@/suggestion";
import { mono, radius, roleIcon, space, statusColor, statusIcon, subtypeIcon, type, useTheme } from "@/theme";
import { Banner, Button, Card, Choice, Field, IconName, Loading, Muted, Pill, Screen, SectionTitle } from "@/ui";

type Target = { key: string; label: string; sub?: string; icon: IconName; to_actor_id?: number; to_role?: api.ActorRole };

function Quote({ children }: { children: string }) {
  const th = useTheme();
  return (
    <View style={{ backgroundColor: th.bgSecondary, borderRadius: radius.md, padding: space.md, borderLeftWidth: 3, borderLeftColor: th.primary }}>
      <Text selectable style={[type.body, { color: th.text }]}>{children}</Text>
    </View>
  );
}

export default function ReportDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { token, actor } = useSession();
  const { t } = useI18n();
  const th = useTheme();
  const colors = statusColor(th);
  const [report, setReport] = useState<api.InboxDetail | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const [to, setTo] = useState<Target | null>(null);
  const [summary, setSummary] = useState("");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<api.ReportStatus>("RECU");
  const [partnerNote, setPartnerNote] = useState("");
  const [busy, setBusy] = useState<"forward" | "status" | "summary" | "suggest" | null>(null);
  const [suggestion, setSuggestion] = useState<api.Suggestion | null>(null);

  const propose = async () => {
    setBusy("suggest");
    setError(null);
    try {
      const s = await api.suggestSummary(token!, id!);
      setSummary(s.summary);
      setSuggestion(s);
    } catch (e) {
      setError(errorMessage(e, "fr"));
    } finally {
      setBusy(null);
    }
  };
  const canSuggest = !!actor?.ai_available && !!report?.description;

  const load = async () => {
    if (!token || !actor) return;
    setError(null);
    try {
      const [r, people] = await Promise.all([api.inboxItem(token, id!), api.targets(token)]);
      setReport(r);
      setSummary(r.summary ?? "");
      setStatus(r.status);
      setPartnerNote(r.partner_note ?? "");
      setTargets([
        ...actor.can_forward_to.map<Target>((role) => ({ key: "role:" + role, label: `${S.actor.anyone} ${S.roles[role]}`, sub: actor.region, icon: roleIcon[role] as IconName, to_role: role })),
        ...people.map<Target>((p) => ({ key: "actor:" + p.id, label: p.name, sub: [p.organisation, p.commune].filter(Boolean).join(" · "), icon: "person", to_actor_id: p.id })),
      ]);
    } catch (e) {
      setError(errorMessage(e, "fr"));
    }
  };
  useEffect(() => { load(); }, [id, token]);

  if (!token) return <Redirect href="/actor/login" />;

  const mustSummarize = !!actor?.must_summarize;
  // Un relais / point focal qui a déjà transmis n'a plus rien à faire : on ne
  // lui remontre pas le formulaire, il croirait devoir recommencer.
  const alreadyForwarded = mustSummarize && !!report?.events.some((e) => e.kind === "FORWARDED" && e.by_id === actor?.id);
  const forwardedTo = report ? report.assignee ?? (report.target_role ? S.roles[report.target_role] : "—") : "";

  const doForward = async () => {
    if (!to) return setError(S.actor.pickRecipient);
    if (mustSummarize && !summary.trim()) return setError(S.actor.summaryMissing);
    setBusy("forward");
    setError(null);
    try {
      await api.forward(token, id!, { to_actor_id: to.to_actor_id, to_role: to.to_role, summary: summary.trim() || undefined, note: note.trim() || undefined });
      setInfo(S.actor.forwarded);
      router.back();
    } catch (e) {
      setError(errorMessage(e, "fr"));
    } finally {
      setBusy(null);
    }
  };

  const doSummary = async () => {
    if (!summary.trim()) return setError(S.actor.summaryMissing);
    setBusy("summary");
    setError(null);
    try {
      await api.updateSummary(token, id!, summary.trim());
      setInfo(S.actor.summarySaved);
      await load();
    } catch (e) {
      setError(errorMessage(e, "fr"));
    } finally {
      setBusy(null);
    }
  };

  const doStatus = async () => {
    setBusy("status");
    setError(null);
    try {
      await api.setStatus(token, id!, { status, note: partnerNote });
      setInfo(S.actor.saved);
      await load();
    } catch (e) {
      setError(errorMessage(e, "fr"));
    } finally {
      setBusy(null);
    }
  };

  const when = (iso: string) => new Date(iso).toLocaleString();

  return (
    <Screen>
      {error ? <Banner kind="error">{error}</Banner> : null}
      {info ? <Banner kind="success">{info}</Banner> : null}
      {!report && !error ? <Loading /> : null}
      {report ? (
        <>
          {/* En-tête de la fiche : code, statut, type, lieu, chez qui. */}
          <Card accent={colors[report.status]}>
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: space.sm, flexWrap: "wrap" }}>
              <Text style={{ fontFamily: mono, fontSize: 19, fontWeight: "700", color: th.text }}>{report.code}</Text>
              <Pill icon={statusIcon[report.status] as IconName} label={S.statuses[report.status]} color={colors[report.status]} />
            </View>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginTop: space.xs }}>
              <Ionicons name={((report.subtype && subtypeIcon[report.subtype]) || "alert-circle") as IconName} size={18} color={th.primary} />
              <Text style={[type.body, { fontWeight: "600", color: th.text, flex: 1 }]}>
                {t("type_" + report.type)}{report.subtype ? ` · ${t("subtype_" + report.subtype)}` : ""}
              </Text>
            </View>
            {[
              ["location-outline", `${report.commune ?? "—"} (${report.region})`],
              ["time-outline", `${when(report.created_at)} · ${S.actor.receivedVia} ${report.channel}`],
              ["person-outline", `${S.actor.with} : ${report.assignee ?? (report.target_role ? `${S.roles[report.target_role]} (${S.actor.unassigned})` : "—")}`],
            ].map(([icon, label]) => (
              <View key={label} style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                <Ionicons name={icon as IconName} size={14} color={th.textSecondary} />
                <Text style={[type.bodySm, { color: th.textSecondary, flex: 1 }]}>{label}</Text>
              </View>
            ))}
          </Card>

          <SectionTitle icon="chatbox-ellipses-outline">{S.actor.story}</SectionTitle>
          {report.description ? <Quote>{report.description}</Quote> : <Banner kind="warn">{report.legacy ? S.actor.legacy : S.actor.unreadable}</Banner>}

          {report.summary ? (
            <>
              <SectionTitle icon="create-outline">{S.actor.summary}</SectionTitle>
              <Muted>{S.actor.by} {report.summary_by ?? "?"}{report.summary_at ? `, ${when(report.summary_at)}` : ""}</Muted>
              <Quote>{report.summary}</Quote>
            </>
          ) : null}

          {report.partner_note ? <Banner kind="success" title={t("track_partner_note")}>{report.partner_note}</Banner> : null}

          <SectionTitle icon="git-commit-outline">{S.actor.history}</SectionTitle>
          {report.events.map((e, i) => {
            const icon: IconName = e.kind === "CREATED" ? "mail-outline" : e.kind === "FORWARDED" ? "arrow-redo-outline" : (statusIcon[e.status ?? "RECU"] as IconName);
            const color = e.kind === "STATUS" && e.status ? colors[e.status] : th.primary;
            return (
              <View key={i} style={{ flexDirection: "row", gap: space.sm + 4, paddingVertical: space.sm }}>
                <Ionicons name={icon} size={18} color={color} style={{ marginTop: 2, width: 22 }} />
                <View style={{ flex: 1 }}>
                  <Text style={[type.caption, { color: th.textSecondary }]}>{when(e.at)}</Text>
                  <Text style={[type.bodySm, { color: th.text }]}>
                    {e.kind === "CREATED"
                      ? `${S.actor.filed} ${S.actor.by} ${e.by ?? S.actor.anonymous}, ${S.actor.addressedTo} ${e.to ?? (e.to_role ? S.roles[e.to_role] : "—")}.`
                      : e.kind === "FORWARDED"
                        ? `${e.by ?? "?"} ${S.actor.forwardedTo} ${e.to ?? (e.to_role ? S.roles[e.to_role] : "—")}.${e.note ? ` « ${e.note} »` : ""}`
                        : `${e.by ?? "Admin"} → ${e.status ? S.statuses[e.status] : ""}.`}
                  </Text>
                </View>
              </View>
            );
          })}

          {alreadyForwarded ? (
            <Card style={{ marginTop: space.lg }}>
              <SectionTitle icon="create-outline">{S.actor.summary}</SectionTitle>
              <Banner kind="success">{S.actor.alreadyForwarded.replace("{to}", forwardedTo)}</Banner>
              {canSuggest ? <SuggestBlock onPress={propose} loading={busy === "suggest"} suggestion={suggestion} /> : null}
              <Field label={S.actor.summaryConcise} hint={`🔒 ${S.actor.summaryConciseHint}`} multiline value={summary} onChangeText={setSummary} maxLength={MAX_DESCRIPTION} />
              <Button variant="primary" icon="checkmark-outline" title={S.actor.saveSummary} loading={busy === "summary"} disabled={!summary.trim()} onPress={doSummary} />
            </Card>
          ) : null}

          {actor && actor.can_forward_to.length > 0 && !alreadyForwarded ? (
            <Card style={{ marginTop: space.lg }}>
              <SectionTitle icon="arrow-redo-outline">{S.actor.forward}</SectionTitle>
              {mustSummarize ? <Banner kind="info">{S.actor.relayRole}</Banner> : null}
              <Muted>{S.actor.forwardTo}</Muted>
              {targets.map((tg) => (
                <Choice key={tg.key} icon={tg.icon} label={tg.label} sub={tg.sub} selected={to?.key === tg.key} onPress={() => setTo(tg)} />
              ))}
              {canSuggest ? <SuggestBlock onPress={propose} loading={busy === "suggest"} suggestion={suggestion} /> : null}
              <Field label={mustSummarize ? S.actor.summaryConcise : S.actor.summaryLabel} hint={`🔒 ${S.actor.summaryConciseHint}`} multiline value={summary} onChangeText={setSummary} maxLength={MAX_DESCRIPTION} />
              <Field label={S.actor.noteLabel} icon="chatbubble-outline" placeholder={S.actor.notePlaceholder} value={note} onChangeText={setNote} maxLength={NOTE_MAX} />
              <Button variant="primary" icon="send-outline" title={S.actor.forward} loading={busy === "forward"} disabled={!to || (mustSummarize && !summary.trim())} onPress={doForward} />
            </Card>
          ) : null}

          {actor?.can_set_status ? (
            <Card style={{ marginTop: space.lg }}>
              <SectionTitle icon="people-outline">{S.actor.status}</SectionTitle>
              {api.STATUSES.map((st) => (
                <Choice key={st} icon={statusIcon[st] as IconName} label={S.statuses[st]} selected={status === st} onPress={() => setStatus(st)} />
              ))}
              <Field label={S.actor.partnerNote} hint={S.actor.partnerNoteHint} multiline value={partnerNote} onChangeText={setPartnerNote} maxLength={NOTE_MAX} />
              <Button variant="primary" icon="checkmark-outline" title={S.actor.save} loading={busy === "status"} onPress={doStatus} />
            </Card>
          ) : !mustSummarize ? (
            <Banner kind="info">{S.actor.noStatusRight}</Banner>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}
