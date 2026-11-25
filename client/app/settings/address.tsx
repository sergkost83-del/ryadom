import { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { ApiError, errorMessage } from "../../src/api/errors";
import { api } from "../../src/api/instance";
import type { AddressChangeState, DirectoryCommunity } from "../../src/api/types";
import { ILLUSTRATIONS } from "../../src/assets";
import { useAuth } from "../../src/auth/AuthContext";
import { addressLine } from "../../src/houses";
import { colors, radius, spacing } from "../../src/theme";
import { isInviteCodeComplete, normalizeInviteCode } from "../../src/validation";
import { Banner } from "../../src/ui/Banner";
import { Button } from "../../src/ui/Button";
import { HousePicker } from "../../src/ui/HousePicker";
import { Screen } from "../../src/ui/Screen";
import { StateView } from "../../src/ui/StateView";
import { TextField } from "../../src/ui/TextField";

export default function AddressScreen() {
  const { refreshUser } = useAuth();
  const [current, setCurrent] = useState<AddressChangeState | null>(null);
  const [directory, setDirectory] = useState<DirectoryCommunity[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"house" | "invite">("house");
  const [buildingId, setBuildingId] = useState<string | null>(null);
  const [invite, setInvite] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [state, dir] = await Promise.all([api.addressChange(), api.communities()]);
      setCurrent(state);
      setDirectory(dir.communities);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const pending = current?.request?.status === "pending" ? current.request : null;
  const canSubmit = (mode === "house" ? buildingId !== null : isInviteCodeComplete(invite)) && !busy;

  async function submit() {
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    setInfo(null);
    setFieldError(null);
    try {
      const result = await api.requestAddressChange(mode === "house" ? { building_id: buildingId ?? undefined } : { invite_code: invite });
      setInfo(result.request.status === "approved" ? "Адрес изменён." : "Заявка отправлена. Модератор рассмотрит её.");
      setBuildingId(null);
      setInvite("");
      await Promise.all([load(), refreshUser()]);
    } catch (e) {
      setError(errorMessage(e));
      if (e instanceof ApiError) setFieldError(e.fieldErrors.invite_code ?? e.fieldErrors.building_id ?? null);
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    try {
      await api.cancelAddressChange();
      setInfo("Заявка отменена.");
      await load();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <Screen>
      {error ? <Banner message={error} testID="address-error" /> : null}
      {info ? <Banner kind="info" message={info} testID="address-info" /> : null}

      <View style={styles.card}>
        <Text style={styles.label}>Сейчас</Text>
        <Text style={styles.value} testID="address-current">{current?.membership ? addressLine(current.membership.building) : "Адрес не указан"}</Text>
        {current?.membership ? <Text style={styles.muted}>{current.membership.status === "confirmed" ? "Подтверждён" : "На проверке у модератора"}</Text> : null}
      </View>

      {pending ? (
        <>
          <StateView image={ILLUSTRATIONS.pending} title="Заявка на смену адреса" text={`Новый адрес: ${addressLine(pending.to_building)}. Ждём решения модератора.`} testID="address-request-pending" />
          <Button title="Отменить заявку" onPress={cancel} variant="secondary" testID="address-cancel" />
        </>
      ) : directory ? (
        <>
          <Text style={styles.section}>Сменить адрес</Text>
          <View style={styles.tabs}>
            <Button title="Выбрать дом" onPress={() => setMode("house")} variant={mode === "house" ? "primary" : "secondary"} testID="address-mode-house" />
            <Button title="У меня есть код" onPress={() => setMode("invite")} variant={mode === "invite" ? "primary" : "secondary"} testID="address-mode-invite" />
          </View>
          {mode === "house" ? (
            <HousePicker directory={directory} value={buildingId} onChange={setBuildingId} />
          ) : (
            <TextField label="Код приглашения" value={invite} onChangeText={(text) => setInvite(normalizeInviteCode(text))} autoCapitalize="characters" placeholder="ABCD-EFGH" error={fieldError} testID="address-invite-input" />
          )}
          <Button title={mode === "house" ? "Отправить заявку" : "Применить код"} onPress={submit} disabled={!canSubmit} loading={busy} testID="address-submit" />
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.surface, borderRadius: radius.l, borderWidth: 1, borderColor: colors.border, padding: spacing.l, gap: spacing.xs },
  label: { color: colors.textMuted, fontSize: 13, fontWeight: "600" },
  value: { color: colors.text, fontSize: 17, fontWeight: "800" },
  muted: { color: colors.textMuted, fontSize: 14 },
  section: { fontSize: 18, fontWeight: "800", color: colors.text },
  tabs: { flexDirection: "row", gap: spacing.s },
});
