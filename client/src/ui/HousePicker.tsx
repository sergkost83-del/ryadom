import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { DirectoryCommunity } from "../api/types";
import { buildingsOf, findBuilding, streetsOf } from "../houses";
import { colors, radius, spacing } from "../theme";

interface Props {
  directory: DirectoryCommunity[];
  value: string | null;
  onChange: (buildingId: string | null) => void;
}

function Chips({ title, items, selected, onSelect, prefix }: { title: string; items: { id: string; label: string }[]; selected: string | null; onSelect: (id: string) => void; prefix: string }) {
  return (
    <View style={styles.group}>
      <Text style={styles.title}>{title}</Text>
      <View style={styles.chips}>
        {items.map((item) => (
          <Pressable key={item.id} testID={`${prefix}-${item.label}`} accessibilityRole="button" accessibilityState={{ selected: selected === item.id }} onPress={() => onSelect(item.id)} style={[styles.chip, selected === item.id && styles.chipSelected]}>
            <Text style={[styles.chipText, selected === item.id && styles.chipTextSelected]}>{item.label}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

/** Выбор дома по шагам: ЖК, затем улица, затем дом. */
export function HousePicker({ directory, value, onChange }: Props) {
  const found = findBuilding(directory, value);
  const [communityId, setCommunityId] = useState<string | null>(found?.community.id ?? null);
  const [streetId, setStreetId] = useState<string | null>(found?.street.id ?? null);
  const streets = streetsOf(directory, communityId);
  const buildings = buildingsOf(streets, streetId);

  return (
    <View style={styles.wrap}>
      <Chips
        title="Жилой комплекс"
        prefix="community"
        items={directory.map((c) => ({ id: c.id, label: c.name }))}
        selected={communityId}
        onSelect={(id) => {
          setCommunityId(id);
          setStreetId(null);
          onChange(null);
        }}
      />
      {communityId ? (
        <Chips
          title="Улица"
          prefix="street"
          items={streets.map((s) => ({ id: s.id, label: s.name }))}
          selected={streetId}
          onSelect={(id) => {
            setStreetId(id);
            onChange(null);
          }}
        />
      ) : null}
      {streetId ? <Chips title="Дом" prefix="building" items={buildings} selected={value} onSelect={(id) => onChange(id)} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.l },
  group: { gap: spacing.s },
  title: { color: colors.textMuted, fontSize: 14, fontWeight: "600" },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.s },
  chip: { paddingHorizontal: spacing.l, paddingVertical: 10, borderRadius: radius.xl, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  chipSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { color: colors.text, fontSize: 15 },
  chipTextSelected: { color: "#FFFFFF", fontWeight: "700" },
});
