// useAutoBackup.ts

import {AppState, AppStateStatus} from 'react-native';
import {useCallback, useEffect, useRef} from 'react';

import {fetchScreenshotImageUris} from '../utils/imageHelper';
import {uploadImagesToServer} from '../utils/uploadHelper';

export const useAutoBackup = (userId: string | null) => {
  const backedUp = useRef<Set<string>>(new Set());

  const backupNow = useCallback(async () => {
    if (!userId) return;
    const images = await fetchScreenshotImageUris();
    const newImages = images.filter(
      img => img.contentId && !backedUp.current.has(img.contentId),
    ) as {
      uri: string;
      contentId: string;
      filename: string;
      timestamp: number;
    }[];

    if (newImages.length > 0) {
      await uploadImagesToServer(newImages, userId);
      newImages.forEach(img => backedUp.current.add(img.contentId));
    }
  }, [userId]);

  useEffect(() => {
    if (!userId) return;
    const sub = AppState.addEventListener('change', state => {
      if (state === 'active') backupNow();
    });
    return () => sub.remove();
  }, [backupNow]);

  return {backupNow};
};
