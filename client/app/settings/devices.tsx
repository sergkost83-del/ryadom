import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { errorMessage } from "../../src/api/errors";
import { api } from "../../src/api/instance";
import type { SessionInfo } from "../../src/api/types";
import { useAuth } from "../../src/auth/AuthContext";
import { formatDate } from "../../src/format";
import { colors, radius, spacing } from "../../src/theme";
import { Banner } from "../../src/ui/Banner";
import { Button } from "../../src/ui/Button";
import { Screen } from "../../src/ui/Screen";

export default function DevicesScreen() {
  const { signOut } = useAuth();
  const [sessions, setSessions] = useState<SessionInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmAll, setConfirmAll] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setSessions((await api.sessions()).sessions);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function revoke(id: string) {
    try {
      await api.revokeSession(id);
      await load();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function logoutEverywhere() {
    if (!confirmAll) {
      setConfirmAll(true);
      return;
    }
    try {
      await api.logoutAll();
    } catch (e) {
      setError(errorMessage(e));
      return;
    }
    await signOut();
    router.replace("/welcome");
  }

  return (
    <Screen>
      {error ? <Banner message={error} testID="devices-error" /> : null}
      {sessions === null && !error ? <Text style={styles.muted}>Загружаем…</Text> : null}
      {sessions?.map((session) => (
        <View key={session.id} style={styles.card} testID="device-card">
          <Text style={styles.title}>{session.device_name || "Устройство"}{session.current ? " (это устройство)" : ""}</Text>
          <Text style={styles.muted}>Последняя активность: {formatDate(session.last_seen_at)}</Text>
          {!session.current ? <Button title="Выйти на этом устройстве" onPress={() => revoke(session.id)} variant="secondary" testID="device-revoke" /> : null}
        </View>
      ))}
      <Button title={confirmAll ? "Нажмите ещё раз, чтобы выйти везде" : "Выйти на всех устройствах"} onPress={logoutEverywhere} variant="danger" testID="devices-logout-all" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.surface, borderRadius: radius.l, borderWidth: 1, borderColor: colors.border, padding: spacing.l, gap: spacing.s },
  title: { fontSize: 16, fontWeight: "800", color: colors.text },
  muted: { color: colors.textMuted, fontSize: 14 },
});
