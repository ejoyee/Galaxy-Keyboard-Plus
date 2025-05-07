// ---------------------------------------------------------------------------
// Kakao OAuth 관련 서비스 로직
// ---------------------------------------------------------------------------
import { login as kakaoLogin, logout as kakaoLogout, unlink } from '@react-native-seoul/kakao-login';
import { api } from '../api/axios';
import { useAuthStore } from '../stores/authStore';

/** ① 카카오 SDK → 백엔드 로그인 */
export async function signInWithKakao() {
  // 1) Kakao SDK 로그인
  const kRes = await kakaoLogin();    // {accessToken, idToken, ...}

  // 2) 우리 서버에 전달해 JWT 세트 획득
  const { data } = await api.post('/auth/kakao/login', {
    kakaoAccessToken: kRes.accessToken,
  });
  // data: { accessToken, refreshToken, userId }

  // 3) 전역 상태 & SecureStore 에 저장
  useAuthStore.getState().setTokens(data);
}

/** ② access 토큰 재발급 */
export async function refreshWithServer() {
  const { refreshToken } = useAuthStore.getState();
  if (!refreshToken) throw new Error('NO_REFRESH_TOKEN');

  const { data } = await api.post('/auth/reissue', { refreshToken });
  // data: { accessToken, refreshToken }
  useAuthStore.getState().setTokens(data);
}

/** ③ 로그아웃 */
export async function signOut() {
  try {
    await kakaoLogout();        // 카카오 세션 끊기
  } catch (_) {
    /* ignore */
  }

  // try {
  //   // (선택) 서버에도 RT 블랙리스트 요청
  //   const { refreshToken } = useAuthStore.getState();
  //   if (refreshToken) await api.post('/auth/logout', { refreshToken });
  // } catch (_) {
  //   /* ignore */
  // }

  useAuthStore.getState().clear();
}

/** ④ 회원탈퇴 = 카카오 unlink + 우리 DB 탈퇴 */
export async function unlinkKakao() {
  await unlink();
  await api.post('/auth/withdraw');
  useAuthStore.getState().clear();
}
