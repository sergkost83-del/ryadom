export interface Tokens {
  token_type: string;
  access: string;
  access_expires_in: number;
  refresh: string;
}

export interface BuildingInfo {
  id: string;
  label: string;
  street: string;
  community: { id: string; name: string };
}

export interface MembershipInfo {
  status: "pending" | "confirmed";
  building: BuildingInfo;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_id: number;
  phone: string;
  account_type: string;
  consents_up_to_date: boolean;
  phone_consent: boolean;
  membership: MembershipInfo | null;
}

export type VerifyResponse =
  | { is_new: true; registration_token: string }
  | { is_new: false; restored: boolean; tokens: Tokens; user: User };

export interface RegisterPayload {
  registration_token: string;
  display_name: string;
  is_adult: boolean;
  avatar_id?: number;
  consents: Record<string, string>;
  building_id?: string;
  invite_code?: string;
  device_name?: string;
}

export interface DirectoryBuilding {
  id: string;
  label: string;
}
export interface DirectoryStreet {
  id: string;
  name: string;
  buildings: DirectoryBuilding[];
}
export interface DirectoryCommunity {
  id: string;
  name: string;
  slug: string;
  locality: string;
  streets: DirectoryStreet[];
}

export interface LegalInfo {
  documents: Record<string, string>;
  minimum_age: number;
}

export interface Notice {
  id: string;
  title: string;
  body: string;
  created_at: string;
  building: { id: string; label: string; street: string };
}

export interface SessionInfo {
  id: string;
  device_name: string;
  created_at: string;
  last_seen_at: string;
  current: boolean;
}

export interface AddressChangeRequestInfo {
  id: string;
  status: "pending" | "approved" | "rejected" | "cancelled";
  to_building: BuildingInfo;
  created_at: string;
  decided_at: string | null;
  comment: string;
}

export interface AddressChangeState {
  membership: MembershipInfo | null;
  request: AddressChangeRequestInfo | null;
}

export interface ProfilePatch {
  display_name?: string;
  avatar_id?: number;
  phone?: string;
  phone_consent?: boolean;
}

export interface ChatRoom {
  id: string;
  kind: "house" | "common";
  title: string;
}

export interface ChatMessage {
  id: string;
  body: string;
  created_at: string;
  mine: boolean;
  author: { id: string; display_name: string; avatar_id: number } | null;
}
