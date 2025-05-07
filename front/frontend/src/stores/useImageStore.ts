import {create} from 'zustand';

export interface ImageItem {
  imageUuid: string;
  uri: string; // 로컬 경로
  isFavorite: boolean;
  hasAlarm: boolean;
}

interface ImageStore {
  images: ImageItem[];
  setImages: (newImages: ImageItem[]) => void;
  appendImages: (newImages: ImageItem[]) => void;
  clearImages: () => void;
}

export const useImageStore = create<ImageStore>(set => ({
  images: [],
  setImages: newImages => set({images: newImages}),
  appendImages: newImages =>
    set(state => ({images: [...state.images, ...newImages]})),
  clearImages: () => set({images: []}),
}));
