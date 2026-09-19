import * as Clipboard from "expo-clipboard";
import { router, useLocalSearchParams } from "expo-router";
import React, { useEffect, useState } from "react";

import * as api from "@/api";
import { useDraft } from "@/draft";
import { useI18n } from "@/i18n";
import { ResourceList } from "@/resources-list";
import { tc } from "@/strings";
import { space, useTheme } from "@/theme";
import { Banner, Button, Card, CodeBox, H1, H2, IconBadge, Muted, P, Screen } from "@/ui";

/** Confirmation : le code de suivi, puis les ressources pour ce type d'incident et cette région. */
export default function ReportDone() {
  const { t, lang } = useI18n();
  const { reset } = useDraft();
  const th = useTheme();
  const { code, subtype, region, type: rtype } = useLocalSearchParams<{ code: string; subtype: string; region: string; type: api.ReportType }>();
  const [resources, setResources] = useState<api.Resource[]>([]);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    reset();
    api.getResources({ type: rtype, subtype, region }).then(setResources).catch(() => {});
  }, []);

  return (
    <Screen>
      <IconBadge icon="checkmark-circle-outline" color={th.primary} />
      <H1 style={{ textAlign: "center", marginTop: 0 }}>{t("confirm_title")}</H1>
      <P style={{ textAlign: "center" }}>{t("confirm_body")}</P>
      <Muted style={{ textAlign: "center" }}>{t("confirm_nothing_stored")}</Muted>

      <Card style={{ marginTop: space.lg }}>
        <H2 style={{ marginTop: 0 }}>{t("confirm_code_title")}</H2>
        <CodeBox code={code ?? ""} />
        <Button
          variant="primary"
          icon={copied ? "checkmark" : "copy-outline"}
          title={copied ? tc(lang, "copied") : tc(lang, "copy")}
          onPress={async () => {
            await Clipboard.setStringAsync(code ?? "");
            setCopied(true);
          }}
        />
        <P>{t("confirm_code_body")}</P>
        <Banner kind="warn">{t("confirm_code_warning")}</Banner>
      </Card>

      {resources.length > 0 ? (
        <>
          <H2>{t("confirm_resources")}</H2>
          <ResourceList resources={resources} />
        </>
      ) : null}

      <Button icon="search-outline" title={t("home_track")} onPress={() => router.replace("/track")} style={{ marginTop: space.lg }} />
      <Button variant="danger" icon="exit-outline" title={tc(lang, "forget")} onPress={() => router.dismissAll()} />
    </Screen>
  );
}
