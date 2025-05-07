// ---------------------------------------------------------------------------
// zustand + zustand/persist + Expo SecureStore
// ---------------------------------------------------------------------------
import { create } from 'zustand';
import { persist, StorageValue } from 'zustand/middleware';
import * as SecureStore from 'expo-secure-store';
import { SECURE_KEY } from '@env';          // 환경변수

/* ------------------------------------------------------------------ *
 * 상태 타입
 * ------------------------------------------------------------------ */
interface Tokens {
  accessToken: string | null;
  refreshToken: string | null;
  // 만료 시각 등을 추가하고 싶으면 여기에
}

interface AuthState extends Tokens {
  /** 새 토큰 세트 저장 (스토어 + SecureStore) */
  setTokens: (payload: Tokens) => void;
  /** 모든 토큰 삭제(로그아웃) */
  clear: () => void;
}

/* ------------------------------------------------------------------ *
 * SecureStore 를 zustand persist 스토리지 어댑터로 래핑
 * ------------------------------------------------------------------ */
const secureZustandStorage = {
  // getItem: JSON 문자열 → 객체
  getItem: async (key: string): Promise<StorageValue<AuthState> | null> => {
    const raw = await SecureStore.getItemAsync(key);
    return raw ? JSON.parse(raw) : null;
  },
  // setItem: 객체 → JSON 문자열
  setItem: async (key: string, value: StorageValue<AuthState>) => {
    await SecureStore.setItemAsync(key, JSON.stringify(value));
  },
  removeItem: (key: string) => SecureStore.deleteItemAsync(key),
};

/* ------------------------------------------------------------------ *
 * zustand 스토어 정의
 * ------------------------------------------------------------------ */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,

      setTokens: ({ accessToken, refreshToken }) =>
        set({ accessToken, refreshToken }),

      clear: () => set({ accessToken: null, refreshToken: null }),
    }),
    {
      name: `${SECURE_KEY}:auth`,
      storage: secureZustandStorage,
      version: 1,
    },
  ),
);
