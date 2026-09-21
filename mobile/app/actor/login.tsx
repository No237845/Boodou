import { router } from "expo-router";
import React, { useState } from "react";

import { ApiError } from "@/api";
import { errorMessage } from "@/errors";
import { useSession } from "@/session";
import { useI18n } from "@/i18n";
import { useTheme } from "@/theme";
import { Banner, Button, Field, H1, IconBadge, Muted, Screen } from "@/ui";

export default function ActorLogin() {
  const { signIn } = useSession();
  const { t, lang } = useI18n();
  const th = useTheme();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await signIn(username, password);
      router.replace("/actor/inbox");
    } catch (e) {
      setError(e instanceof ApiError && e.status === 429 ? t("actor_too_many") : errorMessage(e, lang));
      setBusy(false);
    }
  };

  return (
    <Screen>
      <IconBadge icon="people-outline" color={th.primary} />
      <H1 style={{ textAlign: "center" }}>{t("actor_login")}</H1>
      <Muted style={{ textAlign: "center" }}>{t("actor_login_intro")}</Muted>
      {error ? <Banner kind="error">{error}</Banner> : null}
      <Field label={t("actor_username")} icon="person-outline" value={username} onChangeText={setUsername} autoCapitalize="none" autoCorrect={false} textContentType="username" />
      <Field label={t("actor_password")} icon="lock-closed-outline" value={password} onChangeText={setPassword} secureTextEntry textContentType="password" onSubmitEditing={submit} />
      <Button variant="primary" icon="log-in-outline" title={t("actor_login")} loading={busy} disabled={!username || !password} onPress={submit} style={{ marginTop: 24 }} />
    </Screen>
  );
}
