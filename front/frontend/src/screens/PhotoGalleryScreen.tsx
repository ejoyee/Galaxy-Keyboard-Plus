import React, {useEffect, useLayoutEffect} from 'react';
import {View, FlatList, Text, TouchableOpacity} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../types/types';
import {GalleryHeader} from '../components/GalleryHeader';
import {ImageThumbnail} from '../components/ImageThumbnail';
import {Section} from '../components/Section';
import {useImagePreviewStore} from '../stores/useImagePreviewStore';
import tw from '../utils/tw';
import {BasicImageItem} from '../types/imageTypes';
import {dummyPhotos} from '../components/dummyPhotos';

const PhotoGalleryScreen = () => {
  const {images, appendImages} = useImagePreviewStore();
  const navigation = useNavigation<StackNavigationProp<RootStackParamList>>();

  useLayoutEffect(() => {
    navigation.navigate('ImageDetail', {imageId: 'dummy-001'});
  }, []);

  useEffect(() => {
    appendImages(dummyPhotos); // 임시 데이터 초기 로드
  }, []);

  const favorites = images.filter(img => img.star);

  const handleImagePress = (image: BasicImageItem) => {
    navigation.navigate('ImageDetail', {imageId: image.imageId});
  };

  return (
    <View style={tw`flex-1 bg-white`}>
      <GalleryHeader />

      <FlatList
        data={images}
        renderItem={({item}) => (
          <TouchableOpacity onPress={() => handleImagePress(item)}>
            <ImageThumbnail item={item} size="small" />
          </TouchableOpacity>
        )}
        keyExtractor={item => item.imageId}
        numColumns={4}
        contentContainerStyle={tw`px-5 pb-4`}
        ListHeaderComponent={
          <>
            <Section
              title="즐겨찾기"
              data={favorites}
              onPressMore={() => navigation.navigate('FavoriteGallery')}
            />
            <Section
              title="알림"
              data={favorites}
              onPressMore={() => navigation.navigate('AlarmGallery')}
            />

            <Text style={tw`mt-4 mb-2 text-base font-semibold`}>전체 보기</Text>
          </>
        }
      />
    </View>
  );
};

export default PhotoGalleryScreen;
