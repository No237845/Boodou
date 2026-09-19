/** Composants de base, sobres : écran, textes, bouton, tuile d'action, choix, champ, bandeau. */

import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, TextInputProps, TextStyle, View, ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { mono, radius, shadow, space, type, useTheme } from "./theme";

export type IconName = React.ComponentProps<typeof Ionicons>["name"];

// --------------------------------------------------------------------------- mise en page

export function Screen({ children, scroll = true, footer, padded = true }: { children: React.ReactNode; scroll?: boolean; footer?: React.ReactNode; padded?: boolean }) {
  const th = useTheme();
  const pad = padded ? s.content : undefined;
  const body = scroll ? (
    <ScrollView contentContainerStyle={pad} keyboardShouldPersistTaps="handled">{children}</ScrollView>
  ) : (
    <View style={[pad, { flex: 1 }]}>{children}</View>
  );
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: th.bg }} edges={["bottom", "left", "right"]}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        {body}
        {footer ? <View style={[s.footer, { borderTopColor: th.border, backgroundColor: th.bg }]}>{footer}</View> : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// --------------------------------------------------------------------------- texte

const T = (style: TextStyle, colorKey: "text" | "textSecondary" = "text") =>
  function Typo({ children, style: extra, color }: { children: React.ReactNode; style?: TextStyle; color?: string }) {
    const th = useTheme();
    return <Text style={[style, { color: color ?? th[colorKey] }, extra]}>{children}</Text>;
  };

export const H1 = T({ ...type.h1, marginTop: space.sm, marginBottom: space.sm });
export const H2 = T({ ...type.h2, marginTop: space.lg, marginBottom: space.sm });
export const H3 = T({ ...type.h3, marginTop: space.md, marginBottom: space.xs });
export const P = T({ ...type.body, marginVertical: space.xs });
export const Lead = T({ ...type.bodyLg, marginVertical: space.xs });
export const Muted = T({ ...type.bodySm, marginVertical: space.xs }, "textSecondary");
export const Caption = T({ ...type.caption }, "textSecondary");

/** Titre de section, avec une icône de contour discrète. */
export function SectionTitle({ icon, children }: { icon?: IconName; children: React.ReactNode }) {
  const th = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: space.sm, marginTop: space.lg, marginBottom: space.xs }}>
      {icon ? <Ionicons name={icon} size={18} color={th.textSecondary} /> : null}
      <Text style={[type.h3, { color: th.text, flex: 1 }]}>{children}</Text>
    </View>
  );
}

// --------------------------------------------------------------------------- boutons

type Variant = "primary" | "secondary" | "danger" | "success" | "ghost";

export function Button({
  title, sub, icon, onPress, variant = "secondary", disabled, loading, small, style,
}: {
  title: string; sub?: string; icon?: IconName; onPress?: () => void; variant?: Variant; disabled?: boolean; loading?: boolean; small?: boolean; style?: ViewStyle;
}) {
  const th = useTheme();
  const filled = variant === "primary" || variant === "danger" || variant === "success";
  const fill = variant === "primary" || variant === "success" ? th.primary : variant === "danger" ? th.urgent : variant === "ghost" ? "transparent" : th.primaryLight;
  const fg = filled ? th.onPrimary : variant === "ghost" ? th.primary : th.text;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityRole="button"
      style={({ pressed }) => [
        s.btn, small && s.btnSmall,
        { backgroundColor: disabled ? th.disabled : fill, borderColor: disabled ? th.disabled : filled ? fill : variant === "ghost" ? "transparent" : th.border, opacity: pressed ? 0.8 : 1 },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : (
        <View style={{ flexDirection: "row", alignItems: "center", gap: space.sm }}>
          {icon ? <Ionicons name={icon} size={small ? 16 : 18} color={disabled ? th.textDisabled : fg} /> : null}
          <View>
            <Text style={[type.button, small && { fontSize: 14 }, { color: disabled ? th.textDisabled : fg }]}>{title}</Text>
            {sub ? <Text style={[type.bodySm, { color: fg, opacity: 0.85 }]}>{sub}</Text> : null}
          </View>
        </View>
      )}
    </Pressable>
  );
}

/** Tuile d'action de l'accueil : icône de contour, titre, sous-titre, chevron. `hero` = pleine, en vert. */
export function ActionCard({ title, sub, icon, onPress, hero }: { title: string; sub?: string; icon: IconName; color?: string; onPress: () => void; hero?: boolean }) {
  const th = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [
        s.action,
        { backgroundColor: hero ? th.primary : th.surface, borderColor: hero ? th.primary : th.border, opacity: pressed ? 0.85 : 1 },
      ]}
    >
      <Ionicons name={icon} size={24} color={hero ? th.onPrimary : th.primary} />
      <View style={{ flex: 1 }}>
        <Text style={[type.h3, { color: hero ? th.onPrimary : th.text }]}>{title}</Text>
        {sub ? <Text style={[type.bodySm, { color: hero ? th.onPrimary : th.textSecondary, opacity: hero ? 0.9 : 1 }]}>{sub}</Text> : null}
      </View>
      <Ionicons name="chevron-forward" size={20} color={hero ? th.onPrimary : th.textSecondary} />
    </Pressable>
  );
}

/** Une option dans une liste à choix unique. */
export function Choice({ label, sub, icon, selected, onPress }: { label: string; sub?: string; icon?: IconName; selected?: boolean; onPress: () => void }) {
  const th = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="radio"
      accessibilityState={{ selected: !!selected }}
      style={({ pressed }) => [
        s.choice,
        { borderColor: selected ? th.primary : th.border, backgroundColor: selected ? th.primaryLight : th.surface, opacity: pressed ? 0.85 : 1 },
      ]}
    >
      <Ionicons name={selected ? "radio-button-on" : "radio-button-off"} size={22} color={selected ? th.primary : th.textDisabled} />
      {icon ? <Ionicons name={icon} size={20} color={selected ? th.primary : th.textSecondary} /> : null}
      <View style={{ flex: 1 }}>
        <Text style={[type.body, { color: th.text, fontWeight: selected ? "600" : "400" }]}>{label}</Text>
        {sub ? <Text style={[type.bodySm, { color: th.textSecondary }]}>{sub}</Text> : null}
      </View>
    </Pressable>
  );
}

// --------------------------------------------------------------------------- saisie

export function Field({ label, hint, icon, error, ...props }: TextInputProps & { label?: string; hint?: string; icon?: IconName; error?: boolean }) {
  const th = useTheme();
  const [focus, setFocus] = React.useState(false);
  return (
    <View style={{ marginTop: space.md }}>
      {label ? <Text style={[type.bodySm, { fontWeight: "600", color: th.text, marginBottom: space.xs }]}>{label}</Text> : null}
      <View style={[s.inputWrap, { borderColor: error ? th.urgent : focus ? th.primary : th.border, backgroundColor: th.surface }]}>
        {icon ? <Ionicons name={icon} size={18} color={th.textSecondary} style={{ marginLeft: 12 }} /> : null}
        <TextInput
          placeholderTextColor={th.textDisabled}
          onFocus={() => setFocus(true)}
          onBlur={() => setFocus(false)}
          {...props}
          style={[s.input, { color: th.text }, props.multiline && { minHeight: 140, textAlignVertical: "top" }, props.style]}
        />
      </View>
      {hint ? <Text style={[type.bodySm, { color: th.textSecondary, marginTop: space.xs }]}>{hint}</Text> : null}
    </View>
  );
}

// --------------------------------------------------------------------------- messages

const BANNER_ICON: Record<string, IconName> = { info: "information-circle-outline", error: "alert-circle-outline", warn: "warning-outline", success: "checkmark-circle-outline", lock: "lock-closed-outline" };

export function Banner({ children, kind = "info", title }: { children: React.ReactNode; kind?: "info" | "error" | "warn" | "success" | "lock"; title?: string }) {
  const th = useTheme();
  const color = kind === "error" ? th.urgent : kind === "warn" ? th.warning : th.primary;
  const bg = kind === "error" ? th.urgentLight : kind === "warn" ? th.warningLight : th.primaryLight;
  return (
    <View style={[s.banner, { backgroundColor: bg, borderLeftColor: color }]} accessibilityRole={kind === "error" ? "alert" : undefined}>
      <Ionicons name={BANNER_ICON[kind]} size={20} color={color} style={{ marginTop: 1 }} />
      <View style={{ flex: 1 }}>
        {title ? <Text style={[type.bodySm, { fontWeight: "600", color: th.text, marginBottom: 2 }]}>{title}</Text> : null}
        <Text style={[type.bodySm, { color: kind === "error" ? th.urgent : th.text, fontWeight: kind === "error" ? "600" : "400" }]}>{children}</Text>
      </View>
    </View>
  );
}

export function Pill({ label, color, icon }: { label: string; color: string; icon?: IconName }) {
  return (
    <View style={[s.pill, { borderColor: color }]}>
      {icon ? <Ionicons name={icon} size={12} color={color} /> : null}
      <Text style={[type.caption, { color, fontWeight: "600" }]}>{label}</Text>
    </View>
  );
}

export function Card({ children, onPress, accent, style }: { children: React.ReactNode; onPress?: () => void; accent?: string; style?: ViewStyle }) {
  const th = useTheme();
  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      style={({ pressed }) => [
        s.card, shadow.sm,
        { backgroundColor: th.surface, borderColor: th.border, opacity: pressed ? 0.85 : 1 },
        accent ? { borderLeftWidth: 3, borderLeftColor: accent } : null,
        style,
      ]}
    >
      {children}
    </Pressable>
  );
}

/** Progression du signalement : segments fins, l'étape en cours et les précédentes en vert. */
export function Stepper({ step, total, label }: { step: number; total: number; label: string }) {
  const th = useTheme();
  return (
    <View style={{ marginBottom: space.md }}>
      <View style={{ flexDirection: "row", gap: 4 }}>
        {Array.from({ length: total }, (_, i) => (
          <View key={i} style={{ flex: 1, height: 3, borderRadius: 2, backgroundColor: i < step ? th.primary : th.border }} />
        ))}
      </View>
      <Text style={[type.caption, { color: th.textSecondary, marginTop: space.sm }]}>{label}</Text>
    </View>
  );
}

/** Code de suivi, grand, en police à chasse fixe. */
export function CodeBox({ code }: { code: string }) {
  const th = useTheme();
  return (
    <View style={[s.codeBox, { borderColor: th.primary, backgroundColor: th.surface }]}>
      <Text selectable style={{ fontFamily: mono, fontSize: 28, fontWeight: "700", letterSpacing: 3, color: th.text, textAlign: "center" }}>{code}</Text>
    </View>
  );
}

export function IconBadge({ icon, color, size = 56 }: { icon: IconName; color: string; size?: number }) {
  return (
    <View style={{ alignSelf: "center", marginVertical: space.md }}>
      <Ionicons name={icon} size={size} color={color} />
    </View>
  );
}

export function Loading() {
  const th = useTheme();
  return (
    <View style={{ padding: space.xl, alignItems: "center" }}>
      <ActivityIndicator size="large" color={th.primary} />
    </View>
  );
}

export function Empty({ icon, children }: { icon: IconName; children: React.ReactNode }) {
  const th = useTheme();
  return (
    <View style={{ alignItems: "center", padding: space.xl }}>
      <Ionicons name={icon} size={32} color={th.textDisabled} />
      <Text style={[type.bodySm, { color: th.textSecondary, textAlign: "center", marginTop: space.sm }]}>{children}</Text>
    </View>
  );
}

/** Puces de filtre. */
export function Chip({ label, selected, onPress, icon }: { label: string; selected?: boolean; onPress: () => void; icon?: IconName }) {
  const th = useTheme();
  return (
    <Pressable onPress={onPress} style={[s.chip, { backgroundColor: selected ? th.primary : th.surface, borderColor: selected ? th.primary : th.border }]}>
      {icon ? <Ionicons name={icon} size={14} color={selected ? th.onPrimary : th.textSecondary} /> : null}
      <Text style={[type.bodySm, { color: selected ? th.onPrimary : th.text }]}>{label}</Text>
    </Pressable>
  );
}

const s = StyleSheet.create({
  content: { padding: space.md, paddingBottom: space.xl },
  footer: { padding: space.md, borderTopWidth: StyleSheet.hairlineWidth },
  btn: { minHeight: 48, paddingVertical: 12, paddingHorizontal: space.md, borderRadius: radius.md, borderWidth: 1, alignItems: "center", justifyContent: "center", marginTop: space.sm + 2 },
  btnSmall: { minHeight: 36, paddingVertical: 6, paddingHorizontal: 12, marginTop: 0 },
  action: { flexDirection: "row", alignItems: "center", gap: space.md, padding: space.md, borderRadius: radius.lg, borderWidth: 1, marginTop: space.sm + 2 },
  choice: { flexDirection: "row", alignItems: "center", gap: space.sm + 4, paddingVertical: 12, paddingHorizontal: space.md, borderWidth: 1, borderRadius: radius.md, marginTop: space.sm },
  inputWrap: { flexDirection: "row", alignItems: "flex-start", borderWidth: 1, borderRadius: radius.md },
  input: { flex: 1, paddingVertical: 11, paddingHorizontal: space.md, fontSize: 16 },
  banner: { flexDirection: "row", gap: space.sm + 2, borderLeftWidth: 3, padding: 12, borderRadius: radius.sm, marginVertical: space.sm },
  pill: { flexDirection: "row", alignItems: "center", gap: 4, alignSelf: "flex-start", paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.full, borderWidth: 1 },
  card: { borderWidth: 1, borderRadius: radius.lg, padding: space.md, marginTop: space.sm + 2, gap: space.xs },
  codeBox: { borderWidth: 1, borderRadius: radius.md, padding: space.md, marginVertical: space.sm },
  chip: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, paddingVertical: 7, borderRadius: radius.full, borderWidth: 1 },
});
