import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { errorMessage } from "../../src/api/errors";
import { api } from "../../src/api/instance";
import type { Notice } from "../../src/api/types";
import { ILLUSTRATIONS } from "../../src/assets";
import { useAuth } from "../../src/auth/AuthContext";
import { formatDate } from "../../src/format";
import { addressLine } from "../../src/houses";
import { colors, radius, spacing } from "../../src/theme";
import { Avatar } from "../../src/ui/Avatar";
import { Banner } from "../../src/ui/Banner";
import { Button } from "../../src/ui/Button";
import { Screen } from "../../src/ui/Screen";
import { StateView } from "../../src/ui/StateView";

export default function HomeScreen() {
  const { state, refreshUser } = useAuth();
  const [notices, setNotices] = useState<Notice[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [consentBusy, setConsentBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const fresh = await refreshUser();
      if (fresh && fresh.membership?.status === "confirmed" && fresh.consents_up_to_date) {
        const data = await api.notices();
        setNotices(data.notices);
      } else {
        setNotices(null);
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [refreshUser]);

  useEffect(() => {
    void load();
  }, [load]);

  async function acceptDocuments() {
    setConsentBusy(true);
    setError(null);
    try {
      const legal = await api.legal();
      await api.acceptConsents(legal.documents);
      await load();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setConsentBusy(false);
    }
  }

  if (state.status !== "signedIn") return null;
  const user = state.user;
  const membership = user.membership;

  return (
    <Screen>
      <View style={styles.header}>
        <Avatar id={user.avatar_id} size={52} />
        <View style={styles.headerText}>
          <Text style={styles.hello} testID="home-greeting">Здравствуйте, {user.display_name}</Text>
          <Text style={styles.muted}>{membership ? addressLine(membership.building) : "Адрес не указан"}</Text>
        </View>
      </View>

      {error ? <Banner message={error} testID="home-error" /> : null}

      {!user.consents_up_to_date ? (
        <View style={styles.card} testID="consent-gate">
          <Text style={styles.cardTitle}>Обновились документы</Text>
          <Text style={styles.muted}>Чтобы продолжить, примите актуальные версии политики конфиденциальности и согласия на обработку данных.</Text>
          <Button title="Принять" onPress={acceptDocuments} loading={consentBusy} testID="consent-accept" />
        </View>
      ) : null}

      {!membership ? (
        <StateView image={ILLUSTRATIONS.emptySearch} title="Укажите ваш дом" text="Без адреса объявления дома недоступны." actionTitle="Указать адрес" onAction={() => router.push("/settings/address")} testID="address-missing" />
      ) : membership.status === "pending" ? (
        <StateView image={ILLUSTRATIONS.pending} title="Адрес на проверке" text="Модератор вашего комплекса подтвердит адрес. После этого здесь появятся объявления дома." testID="address-pending" />
      ) : (
        <View style={styles.statusRow} testID="address-confirmed">
          <Text style={styles.statusOk}>✓ Адрес подтверждён</Text>
        </View>
      )}

      {membership?.status === "confirmed" && user.consents_up_to_date ? (
        <View style={styles.list} testID="notices-list">
          <Text style={styles.section}>Объявления дома</Text>
          {notices && notices.length > 0 ? (
            notices.map((notice) => (
              <View key={notice.id} style={styles.card} testID="notice-card">
                <Text style={styles.cardTitle}>{notice.title}</Text>
                <Text style={styles.body}>{notice.body}</Text>
                <Text style={styles.muted}>{formatDate(notice.created_at)}</Text>
              </View>
            ))
          ) : notices ? (
            <StateView image={ILLUSTRATIONS.emptyNotices} title="Пока нет объявлений" text="Когда управляющая компания что-то опубликует, это появится здесь." testID="notices-empty" />
          ) : null}
        </View>
      ) : null}

      <Button title={loading ? "Обновляем…" : "Обновить"} onPress={load} variant="link" disabled={loading} testID="refresh" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", gap: spacing.m },
  headerText: { flex: 1, gap: 2 },
  hello: { fontSize: 20, fontWeight: "800", color: colors.text },
  muted: { color: colors.textMuted, fontSize: 14, lineHeight: 20 },
  card: { backgroundColor: colors.surface, borderRadius: radius.l, borderWidth: 1, borderColor: colors.border, padding: spacing.l, gap: spacing.s },
  cardTitle: { fontSize: 17, fontWeight: "800", color: colors.text },
  body: { fontSize: 15, lineHeight: 22, color: colors.text },
  section: { fontSize: 18, fontWeight: "800", color: colors.text },
  list: { gap: spacing.m },
  statusRow: { backgroundColor: "#E9F6EF", borderRadius: radius.m, padding: spacing.m },
  statusOk: { color: colors.success, fontWeight: "800", fontSize: 15 },
});
