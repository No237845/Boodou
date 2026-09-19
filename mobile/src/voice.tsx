/** Dictée vocale : la personne parle, le texte remplit le champ.
 *
 *  Pour qui lit ou écrit peu. Enregistrement local (AAC mono, léger), envoi au
 *  serveur qui le transcrit puis l'oublie. Le texte revient ici, éditable : la
 *  personne relit (ou se fait relire) avant d'envoyer. Le bouton n'apparaît que
 *  si le serveur annonce la dictée (`GET /api/features`). */

import { Ionicons } from "@expo/vector-icons";
import { AudioModule, RecordingPresets, setAudioModeAsync, useAudioRecorder, useAudioRecorderState } from "expo-audio";
import React, { useEffect, useRef, useState } from "react";
import { Platform, Text, View } from "react-native";

import * as api from "./api";
import { useI18n } from "./i18n";
import { space, type, useTheme } from "./theme";
import { Banner, Button, Muted } from "./ui";

// 2 minutes suffisent pour une plainte ; au-delà on coupe, la personne
// complète en écrivant. AAC mono 32 kbit/s : ~500 Ko pour 2 min, ça passe en 3G.
const MAX_SECONDS = 120;
const OPTIONS = { ...RecordingPresets.HIGH_QUALITY, sampleRate: 16000, numberOfChannels: 1, bitRate: 32000 };

export function VoiceInput({ onText }: { onText: (text: string) => void }) {
  const { t, lang } = useI18n();
  const th = useTheme();
  const recorder = useAudioRecorder(OPTIONS);
  const state = useAudioRecorderState(recorder, 500);
  const [available, setAvailable] = useState(false);
  const [phase, setPhase] = useState<"idle" | "recording" | "sending" | "done">("idle");
  const [error, setError] = useState<string | null>(null);
  const stopping = useRef(false);

  useEffect(() => {
    api.getFeatures().then((f) => setAvailable(!!f.speech)).catch(() => {});
  }, []);

  const seconds = Math.floor((state.durationMillis ?? 0) / 1000);

  const start = async () => {
    setError(null);
    const perm = await AudioModule.requestRecordingPermissionsAsync();
    if (!perm.granted) return setError(t("voice_denied"));
    try {
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
      await recorder.prepareToRecordAsync();
      recorder.record();
      stopping.current = false;
      setPhase("recording");
    } catch (e) {
      console.warn("voice: record failed", e);
      setError(`${t("voice_error")} (micro : ${e instanceof Error ? e.message : String(e)})`);
    }
  };

  const stop = async () => {
    if (stopping.current) return;
    stopping.current = true;
    setPhase("sending");
    let step = "stop";
    try {
      await recorder.stop();
      await setAudioModeAsync({ allowsRecording: false });
      const uri = recorder.uri;
      if (!uri) throw new Error("no_uri");
      step = "upload";
      console.log("voice: sending", uri);
      const text = await api.transcribe(uri, lang ?? "fr");
      if (!text.trim()) {
        setError(t("voice_empty"));
        setPhase("idle");
        return;
      }
      onText(text.trim());
      setPhase("done");
    } catch (e) {
      console.warn("voice: failed at", step, e);
      if (e instanceof api.ApiError && e.status === 429) setError(t("track_too_many"));
      else {
        // Cause entre parenthèses : réseau, ou code + détail renvoyés par le serveur.
        const why = e instanceof api.ApiError ? (e.status === 0 ? "réseau" : `${e.status} ${e.detail}`) : `${step} : ${e instanceof Error ? e.message : String(e)}`;
        setError(`${t("voice_error")} (${why})`);
      }
      setPhase("idle");
    }
  };

  // Coupe toute seule à la durée max.
  useEffect(() => {
    if (phase === "recording" && seconds >= MAX_SECONDS) stop();
  }, [phase, seconds]);

  if (!available || Platform.OS === "web") return null;

  return (
    <View style={{ marginTop: space.md }}>
      {phase === "recording" ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: space.sm }}>
          <Button variant="danger" icon="stop-circle-outline" title={`${t("voice_stop")}  ${String(Math.floor(seconds / 60)).padStart(1, "0")}:${String(seconds % 60).padStart(2, "0")}`} onPress={stop} style={{ flex: 1, marginTop: 0 }} />
          <Ionicons name="mic" size={26} color={th.urgent} />
        </View>
      ) : (
        <Button
          icon="mic-outline"
          title={t("voice_button")}
          onPress={start}
          loading={phase === "sending"}
          disabled={phase === "sending"}
          style={{ marginTop: 0 }}
        />
      )}
      {phase === "recording" ? <Text style={[type.bodySm, { color: th.urgent, marginTop: space.xs }]}>{t("voice_recording")}</Text> : null}
      {phase === "sending" ? <Muted>{t("voice_transcribing")}</Muted> : null}
      {phase === "done" ? <Banner kind="success">{t("voice_done")}</Banner> : null}
      {phase === "idle" && !error ? (
        <Muted>
          {t("voice_hint")}
          {lang && lang !== "fr" && lang !== "en" ? ` ${t("voice_lang_note")}` : ""}
        </Muted>
      ) : null}
      {error ? <Banner kind="error">{error}</Banner> : null}
    </View>
  );
}
