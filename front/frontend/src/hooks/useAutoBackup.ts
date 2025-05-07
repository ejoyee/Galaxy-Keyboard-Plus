/**
 * 🍧 현재 테스트 중이기에 오토 임베딩 막아둔 상태
 * 또 media store 접근이 아니라 fs 접근으로 구현을 해둬서 형식이 조금 다름
 * 훗날 자동 임베딩을 살리게 된다면 해당 훅을 fs 버전 및 타입 수정 예
 */

// import {AppState, AppStateStatus} from 'react-native';
// import {useCallback, useEffect, useRef} from 'react';

// import {fetchScreenshotImageUris} from '../utils/fetchScreenshotImageUris';
// import {uploadImagesToServer} from '../utils/uploadHelper';

// export const useAutoBackup = (userId: string | null) => {
//   const backedUp = useRef<Set<string>>(new Set());

//   const backupNow = useCallback(async () => {
//     if (!userId) return;
//     const images = await fetchScreenshotImageUris();
//     const newImages = images.filter(
//       img => img.contentId && !backedUp.current.has(img.contentId),
//     ) as {
//       uri: string;
//       contentId: string;
//       filename: string;
//       timestamp: number;
//     }[];

//     if (newImages.length > 0) {
//       await uploadImagesToServer(newImages, userId);
//       newImages.forEach(img => backedUp.current.add(img.contentId));
//     }
//   }, [userId]);

//   useEffect(() => {
//     if (!userId) return;
//     const sub = AppState.addEventListener('change', state => {
//       if (state === 'active') backupNow();
//     });
//     return () => sub.remove();
//   }, [backupNow]);

//   return {backupNow};
// };
