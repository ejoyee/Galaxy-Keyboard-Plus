import {create} from 'zustand';
import {persist, createJSONStorage} from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface UserState {
  userId: string;
  setUserId: (id: string) => void;
}

export const useUserStore = create(
  persist<UserState>(
    set => ({
      userId: '',
      setUserId: id => set({userId: id}),
    }),
    {
      name: 'user-storage', // 🔑 저장 키 이름
      storage: createJSONStorage(() => AsyncStorage), // ✅ 타입 변환 래퍼 사용
    },
  ),
);
