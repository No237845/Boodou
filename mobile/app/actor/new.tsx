import * as Clipboard from "expo-clipboard";
import { Redirect, router } from "expo-router";
import React, { useEffect, useState } from "react";
import { View } from "react-native";

import * as api from "@/api";
import { MAX_DESCRIPTION } from "@/config";
import { errorMessage } from "@/errors";
import { useI18n } from "@/i18n";
import { useSession } from "@/session";
import { tc } from "@/strings";
import { SuggestBlock } from "@/suggestion";
import { VoiceInput } from "@/voice";
import { roleIcon, space, subtypeIcon, typeIcon, useTheme } from "@/theme";
import { Banner, Button, Chip, Choice, CodeBox, Field, H1, IconBadge, IconName, Loading, Screen, SectionTitle } from "@/ui";

type Target = { key: string; label: string; sub?: string; icon: IconName; to_actor_id?: number; to_role?: api.ActorRole };

/** Un relais enregistre le cas d'une personne venue le voir, et le transmet dans la foulée. */
export default function NewCase() {
  const { token, actor } = useSession();
  const { t } = useI18n();
  const th = useTheme();
  const [types, setTypes] = useState<api.TypeInfo[]>([]);
  const [regions, setRegions] = useState<api.Region[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [subtype, setSubtype] = useState<string | null>(null);
  const [region, setRegion] = useState<string>(actor?.region ?? "");
  const [commune, setCommune] = useState<string | null>(actor?.commune ?? null);
  const [to, setTo] = useState<Target | null>(null);
  const [description, setDescription] = useState("");
  const [summary, setSummary] = useState("");
  const [suggesting, setSuggesting] = useState(false);
  const [suggestion, setSuggestion] = useState<api.Suggestion | null>(null);

  const propose = async () => {
    setSuggesting(true);
    setError(null);
    try {
      const s = await api.reformulate(token!, { text: description.trim(), region, commune: commune ?? undefined, subtype: subtype ?? undefined });
      setSummary(s.summary);
      setSuggestion(s);
    } catch (e) {
      setError(errorMessage(e, "fr"));
    } finally {
      setSuggesting(false);
    }
  };
  const [busy, setBusy] = useState(false);
  const [code, setCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!token || !actor) return;
    Promise.all([api.getTypes("fr"), api.getRegions(), api.targets(token)])
      .then(([ty, rg, people]) => {
        setTypes(ty);
        setRegions(rg);
        setTargets([
          ...actor.can_forward_to.map<Target>((role) => ({ key: "role:" + role, label: `${t("actor_anyone")} ${t("role_" + role)}`, sub: actor.region, icon: roleIcon[role] as IconName, to_role: role })),
          ...people.map<Target>((p) => ({ key: "actor:" + p.id, label: p.name, sub: [p.organisation, p.commune].filter(Boolean).join(" · "), icon: "person", to_actor_id: p.id })),
        ]);
        setLoaded(true);
      })
      .catch((e) => setError(errorMessage(e, "fr")));
  }, [token]);

  if (!token || !actor) return <Redirect href="/actor/login" />;
  // L'action sociale et les gestionnaires traitent, ils ne saisissent pas de cas.
  if (!actor.must_summarize) return <Redirect href="/actor/inbox" />;

  const communes = regions.find((r) => r.name === region)?.communes ?? [];

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      // Le destinataire est choisi ici, une seule fois : le serveur enregistre
      // le signalement directement chez lui, déjà « transmis ».
      const r = await api.postReport(
        { subtype: subtype!, region, commune: commune!, description: description.trim(), summary: summary.trim(), target_role: to?.to_role ?? null, assignee_id: to?.to_actor_id ?? null, lang: "fr" },
        token,
      );
      setCode(r.code);
    } catch (e) {
      setError(errorMessage(e, "fr"));
    } finally {
      setBusy(false);
    }
  };

  if (code) {
    return (
      <Screen>
        <IconBadge icon="checkmark-circle-outline" color={th.primary} />
        <H1 style={{ textAlign: "center" }}>{t("confirm_code_title")}</H1>
        <CodeBox code={code} />
        <Button variant="primary" icon={copied ? "checkmark" : "copy-outline"} title={copied ? tc("fr", "copied") : tc("fr", "copy")} onPress={async () => { await Clipboard.setStringAsync(code); setCopied(true); }} />
        <Banner kind="warn">{t("actor_give_code")}</Banner>
        <Button icon="mail-outline" title={t("actor_inbox")} onPress={() => router.replace("/actor/inbox")} style={{ marginTop: space.lg }} />
      </Screen>
    );
  }

  const ready = subtype && region && commune && to && description.trim().length > 0 && (!actor.must_summarize || summary.trim().length > 0);

  return (
    <Screen footer={<Button variant="primary" icon="send-outline" title={t("actor_create_and_forward")} loading={busy} disabled={!ready} onPress={submit} />}>
      <H1>{t("actor_new_case")}</H1>
      <Banner kind="lock">{t("actor_new_intro")}</Banner>
      {error ? <Banner kind="error">{error}</Banner> : null}
      {!loaded && !error ? <Loading /> : null}
      {loaded ? (
        <>
          {types.map((ty) => (
            <React.Fragment key={ty.code}>
              <SectionTitle icon={typeIcon[ty.code] as IconName}>{ty.label}</SectionTitle>
              {ty.subtypes.map((s) => (
                <Choice key={s.code} icon={(subtypeIcon[s.code] ?? "ellipse") as IconName} label={s.label} selected={subtype === s.code} onPress={() => setSubtype(s.code)} />
              ))}
            </React.Fragment>
          ))}

          <SectionTitle icon="map-outline">{t("report_region")}</SectionTitle>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.sm }}>
            {regions.map((r) => (
              <Chip key={r.name} label={r.name} selected={region === r.name} onPress={() => { setRegion(r.name); setCommune(null); }} />
            ))}
          </View>
          <SectionTitle icon="location-outline">{t("report_commune")}</SectionTitle>
          {communes.map((c) => (
            <Choice key={c} icon="location-outline" label={c} selected={commune === c} onPress={() => setCommune(c)} />
          ))}

          <SectionTitle icon="arrow-redo-outline">{t("actor_forward")}</SectionTitle>
          {targets.map((tg) => (
            <Choice key={tg.key} icon={tg.icon} label={tg.label} sub={tg.sub} selected={to?.key === tg.key} onPress={() => setTo(tg)} />
          ))}

          <VoiceInput onText={(spoken) => setDescription((d) => ((d ? d.trimEnd() + "\n" : "") + spoken).slice(0, MAX_DESCRIPTION))} />
          <Field label={t("actor_what")} hint={`🔒 ${t("actor_what_hint")}`} multiline value={description} onChangeText={(v) => setDescription(v.slice(0, MAX_DESCRIPTION))} maxLength={MAX_DESCRIPTION} />
          {actor.ai_available ? <SuggestBlock onPress={propose} loading={suggesting} suggestion={suggestion} disabled={description.trim().length < 10} /> : null}
          <Field label={actor.must_summarize ? t("actor_summary_concise") : t("actor_summary_label")} hint={`🔒 ${t("actor_summary_concise_hint")}`} multiline value={summary} onChangeText={(v) => setSummary(v.slice(0, MAX_DESCRIPTION))} maxLength={MAX_DESCRIPTION} />
        </>
      ) : null}
    </Screen>
  );
}
