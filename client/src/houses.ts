import type { BuildingInfo, DirectoryBuilding, DirectoryCommunity, DirectoryStreet, MembershipInfo } from "./api/types";

export function streetsOf(directory: DirectoryCommunity[], communityId: string | null): DirectoryStreet[] {
  return directory.find((c) => c.id === communityId)?.streets ?? [];
}

export function buildingsOf(streets: DirectoryStreet[], streetId: string | null): DirectoryBuilding[] {
  return streets.find((s) => s.id === streetId)?.buildings ?? [];
}

/** Находит дом в справочнике и возвращает его вместе с улицей и ЖК. */
export function findBuilding(directory: DirectoryCommunity[], buildingId: string | null) {
  if (!buildingId) return null;
  for (const community of directory) {
    for (const street of community.streets) {
      const building = street.buildings.find((b) => b.id === buildingId);
      if (building) return { community, street, building };
    }
  }
  return null;
}

export function addressLine(building: BuildingInfo): string {
  return `${building.community.name}, ${building.street}, ${building.label}`;
}

export function membershipStatusText(membership: MembershipInfo | null): string {
  if (!membership) return "Адрес не указан";
  return membership.status === "confirmed" ? "Адрес подтверждён" : "Адрес на проверке у модератора";
}
