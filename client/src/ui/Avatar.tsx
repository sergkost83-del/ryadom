import { Image } from "react-native";

import { AVATARS_256 } from "../assets";

export function Avatar({ id, size = 56 }: { id: number; size?: number }) {
  const index = Math.min(Math.max(id, 1), AVATARS_256.length) - 1;
  return <Image source={AVATARS_256[index]} style={{ width: size, height: size, borderRadius: size / 2 }} accessibilityLabel="Аватар" />;
}
