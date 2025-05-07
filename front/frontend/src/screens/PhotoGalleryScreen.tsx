import React from 'react';
import {View, FlatList, Text} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../types/types';

// import Icon from 'react-native-vector-icons/Ionicons';
import {useEffect} from 'react';

import {GalleryHeader} from '../components/GalleryHeader';
import {ImageThumbnail} from '../components/ImageThumbnail';
import {Section} from '../components/Section';

import {useImageStore, ImageItem} from '../stores/useImageStore';
import tw from '../utils/tw';

// 더미데이터
import {dummyPhotos} from '../components/dummyPhotos';

const PhotoGalleryScreen = () => {
  const {images, appendImages} = useImageStore();

  useEffect(() => {
    appendImages(dummyPhotos); // 초기에 한 번 더미 데이터 로드
  }, []);

  const navigation = useNavigation<StackNavigationProp<RootStackParamList>>();

  const favorites = images.filter(img => img.isFavorite);
  const alarms = images.filter(img => img.hasAlarm);

  return (
    <View style={tw`flex-1 bg-white `}>
      {/* Header */}
      <GalleryHeader />

      <FlatList
        data={images}
        renderItem={({item}) => <ImageThumbnail item={item} size="small" />}
        keyExtractor={item => item.imageUuid}
        numColumns={4}
        contentContainerStyle={tw`px-5 pb-4 `}
        ListHeaderComponent={
          <>
            <Section
              title="즐겨찾기"
              data={favorites}
              onPressMore={() => navigation.navigate('FavoriteGallery')}
            />
            <Section
              title="알림"
              data={alarms}
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
