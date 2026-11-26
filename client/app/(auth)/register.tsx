import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { ApiError, errorMessage } from "../../src/api/errors";
import { api, DEVICE_NAME } from "../../src/api/instance";
import type { DirectoryCommunity, LegalInfo } from "../../src/api/types";
import { useAuth } from "../../src/auth/AuthContext";
import { flow } from "../../src/flow";
import { colors, spacing } from "../../src/theme";
import { cleanDisplayName, isInviteCodeComplete, nameError, normalizeInviteCode } from "../../src/validation";
import { AVATARS_256 } from "../../src/assets";
import { Avatar } from "../../src/ui/Avatar";
import { Banner } from "../../src/ui/Banner";
import { Button } from "../../src/ui/Button";
import { Checkbox } from "../../src/ui/Checkbox";
import { HousePicker } from "../../src/ui/HousePicker";
import { Screen } from "../../src/ui/Screen";
import { TextField } from "../../src/ui/TextField";

export default function RegisterScreen() {
  const { signIn } = useAuth();
  const [directory, setDirectory] = useState<DirectoryCommunity[] | null>(null);
  const [legal, setLegal] = useState<LegalInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [mode, setMode] = useState<"house" | "invite">("house");
  const [buildingId, setBuildingId] = useState<string | null>(null);
  const [invite, setInvite] = useState("");
  const [avatar, setAvatar] = useState(1);
  const [adult, setAdult] = useState(false);
  const [acceptPolicy, setAcceptPolicy] = useState(false);
  const [acceptData, setAcceptData] = useState(false);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!flow.registrationToken) router.replace("/email");
  }, []);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const [dir, info] = await Promise.all([api.communities(), api.legal()]);
      setDirectory(dir.communities);
      setLegal(info);
    } catch (e) {
      setLoadError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const nameProblem = name.length > 0 ? nameError(name) : null;
  const addressOk = mode === "house" ? buildingId !== null : isInviteCodeComplete(invite);
  const canSubmit = nameError(name) === null && addressOk && adult && acceptPolicy && acceptData && legal !== null && !busy;

  async function submit() {
    if (!canSubmit || !legal) return;
    setBusy(true);
    setError(null);
    setFieldErrors({});
    try {
      const result = await api.register({
        registration_token: flow.registrationToken,
        display_name: cleanDisplayName(name),
        is_adult: true,
        avatar_id: avatar,
        consents: legal.documents,
        ...(mode === "house" ? { building_id: buildingId ?? undefined } : { invite_code: invite }),
        device_name: DEVICE_NAME,
      });
      await signIn(result.tokens, result.user);
      flow.reset();
      router.replace("/home");
    } catch (e) {
      setError(errorMessage(e));
      if (e instanceof ApiError) setFieldErrors(e.fieldErrors);
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <Screen>
        <Banner message={loadError} testID="register-load-error" />
        <Button title="Повторить" onPress={load} testID="register-retry" />
      </Screen>
    );
  }

  return (
    <Screen>
      <Text style={styles.title}>Знакомство</Text>
      <TextField label="Как вас зовут" value={name} onChangeText={setName} autoCapitalize="words" placeholder="Анна Иванова" error={nameProblem ?? fieldErrors.display_name} testID="name-input" />

      <Text style={styles.section}>Аватар</Text>
      <View style={styles.avatars}>
        {AVATARS_256.map((_, index) => (
          <Pressable key={index} testID={`reg-avatar-${index + 1}`} accessibilityRole="button" accessibilityState={{ selected: avatar === index + 1 }} onPress={() => setAvatar(index + 1)} style={[styles.avatarBox, avatar === index + 1 && styles.avatarBoxSelected]}>
            <Avatar id={index + 1} size={56} />
          </Pressable>
        ))}
      </View>

      <Text style={styles.section}>Ваш дом</Text>
      <View style={styles.tabs}>
        <Button title="Выбрать дом" onPress={() => setMode("house")} variant={mode === "house" ? "primary" : "secondary"} testID="mode-house" />
        <Button title="У меня есть код" onPress={() => setMode("invite")} variant={mode === "invite" ? "primary" : "secondary"} testID="mode-invite" />
      </View>
      {directory === null ? (
        <Text style={styles.muted}>Загружаем список домов…</Text>
      ) : mode === "house" ? (
        <>
          <HousePicker directory={directory} value={buildingId} onChange={setBuildingId} />
          <Text style={styles.muted}>Адрес подтвердит модератор вашего комплекса.</Text>
          {fieldErrors.building_id ? <Text style={styles.error}>{fieldErrors.building_id}</Text> : null}
        </>
      ) : (
        <>
          <TextField label="Код приглашения" value={invite} onChangeText={(text) => setInvite(normalizeInviteCode(text))} autoCapitalize="characters" placeholder="ABCD-EFGH" error={fieldErrors.invite_code} testID="invite-input" />
          <Text style={styles.muted}>Код выдаёт управляющая компания или модератор. С ним адрес подтверждается сразу.</Text>
        </>
      )}

      <Text style={styles.section}>Согласия</Text>
      <Checkbox checked={adult} onChange={setAdult} label="Мне есть 18 лет." testID="adult-check" />
      {fieldErrors.is_adult ? <Text style={styles.error}>{fieldErrors.is_adult}</Text> : null}
      <Checkbox checked={acceptPolicy} onChange={setAcceptPolicy} label="Я прочитал(а) и принимаю" linkText="политику конфиденциальности." onLinkPress={() => router.push("/legal/privacy_policy")} testID="policy-check" />
      <Checkbox checked={acceptData} onChange={setAcceptData} label="Согласен(на) на" linkText="обработку персональных данных." onLinkPress={() => router.push("/legal/personal_data")} testID="data-check" />
      {fieldErrors.consents ? <Text style={styles.error}>{fieldErrors.consents}</Text> : null}

      {error ? <Banner message={error} testID="register-error" /> : null}
      <Button title="Зарегистрироваться" onPress={submit} disabled={!canSubmit} loading={busy} testID="register-submit" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 28, fontWeight: "800", color: colors.text },
  section: { fontSize: 18, fontWeight: "800", color: colors.text, marginTop: spacing.m },
  tabs: { flexDirection: "row", gap: spacing.s },
  muted: { color: colors.textMuted, fontSize: 14, lineHeight: 20 },
  error: { color: colors.danger, fontSize: 13 },
  avatars: { flexDirection: "row", flexWrap: "wrap", gap: spacing.s },
  avatarBox: { borderRadius: 34, padding: 2, borderWidth: 3, borderColor: "transparent" },
  avatarBoxSelected: { borderColor: colors.primary },
});
