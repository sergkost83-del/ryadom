import type { ImageSourcePropType } from "react-native";

// Файлы копирует команда npm run assets из design/assets. Metro требует статических путей.
export const AVATARS_256: ImageSourcePropType[] = [1, 2, 3, 4, 5, 6, 7, 8].map((i) => AVATAR_FILES[i - 1]);
const AVATAR_FILES: ImageSourcePropType[] = [
  require("../assets/images/avatars/avatar_1_256.webp"),
  require("../assets/images/avatars/avatar_2_256.webp"),
  require("../assets/images/avatars/avatar_3_256.webp"),
  require("../assets/images/avatars/avatar_4_256.webp"),
  require("../assets/images/avatars/avatar_5_256.webp"),
  require("../assets/images/avatars/avatar_6_256.webp"),
  require("../assets/images/avatars/avatar_7_256.webp"),
  require("../assets/images/avatars/avatar_8_256.webp"),
];

export const ILLUSTRATIONS = {
  pending: require("../assets/images/illustrations/state_pending.webp") as ImageSourcePropType,
  confirmed: require("../assets/images/illustrations/state_confirmed.webp") as ImageSourcePropType,
  error: require("../assets/images/illustrations/state_error.webp") as ImageSourcePropType,
  emptyNotices: require("../assets/images/illustrations/empty_notices.webp") as ImageSourcePropType,
  emptySearch: require("../assets/images/illustrations/empty_search.webp") as ImageSourcePropType,
};

export const COVER_GENERIC: ImageSourcePropType = require("../assets/images/covers/cover_generic_800.webp");
export const LOGO: ImageSourcePropType = require("../assets/images/brand/logo-mark_512.webp");
