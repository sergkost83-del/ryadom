import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { errorMessage } from "../../src/api/errors";
import { api } from "../../src/api/instance";
import type { ChatRoom } from "../../src/api/types";
import { ILLUSTRATIONS } from "../../src/assets";
import { useAuth } from "../../src/auth/AuthContext";
import { colors } from "../../src/theme";
import { Banner } from "../../src/ui/Banner";
import { Row } from "../../src/ui/Row";
import { Screen } from "../../src/ui/Screen";
import { StateView } from "../../src/ui/StateView";

export default function ChatsScreen() {
  const { state } = useAuth();
  const [rooms, setRooms] = useState<ChatRoom[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setRooms((await api.chatRooms()).rooms);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (state.status !== "signedIn") return null;
  const user = state.user;
  const confirmed = user.membership?.status === "confirmed" && user.consents_up_to_date;

  if (!confirmed) {
    return (
      <Screen>
        <StateView image={ILLUSTRATIONS.pending} title="Чаты откроются после подтверждения адреса" text="Когда модератор подтвердит ваш адрес, здесь появятся чат дома и общий чат комплекса." testID="chats-locked" />
      </Screen>
    );
  }

  return (
    <Screen>
      <Text style={styles.title}>Чаты</Text>
      {error ? <Banner message={error} testID="chats-error" /> : null}
      {rooms === null && !error ? <Text style={styles.muted}>Загружаем…</Text> : null}
      {rooms?.map((room) => (
        <View key={room.id}>
          <Row
            testID={`room-${room.kind}`}
            title={room.kind === "house" ? `Дом: ${room.title}` : `Общий чат: ${room.title}`}
            subtitle={room.kind === "house" ? "Только соседи вашего дома" : "Все жители комплекса"}
            onPress={() => router.push(`/chat/${room.id}`)}
          />
        </View>
      ))}
      {rooms && rooms.length === 0 ? <StateView image={ILLUSTRATIONS.emptyNotices} title="Чатов пока нет" text="Попробуйте обновить позже." /> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 28, fontWeight: "800", color: colors.text },
  muted: { color: colors.textMuted, fontSize: 15 },
});
