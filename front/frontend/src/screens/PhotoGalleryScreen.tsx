import React from 'react';
import {
  View,
  FlatList,
  Image,
  Text,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../types/types';
import Icon from 'react-native-vector-icons/Ionicons';
import {useEffect} from 'react';

import {GalleryHeader} from '../components/GalleryHeader';

import {useImageStore, ImageItem} from '../stores/useImageStore';
import tw from '../utils/tw';

// 더미데이터
import {dummyPhotos} from '../components/dummyPhotos';

const ImageThumbnail = ({
  item,
  size = 'large', // 기본은 섹션용
}: {
  item: ImageItem;
  size?: 'small' | 'large';
}) => {
  const imageSize = size === 'small' ? 'w-22 h-22' : 'w-28 h-28'; // small: 64px, large: 80px

  return (
    <View style={tw`relative mr-2 mb-2`}>
      <Image
        source={{uri: item.uri}}
        style={tw`${imageSize} rounded-lg bg-gray-200`}
      />
      {item.isFavorite && (
        <View style={tw`absolute bottom-1 right-1`}>
          <Icon name="star" size={16} color="white" />
        </View>
      )}
      {item.hasAlarm && (
        <View style={tw`absolute top-1 right-1`}>
          <Icon name="notifications" size={16} color="white" />
        </View>
      )}
    </View>
  );
};

const Section = ({
  title,
  data,
  onPressMore,
}: {
  title: string;
  data: ImageItem[];
  onPressMore: () => void;
}) => (
  <View style={tw`mt-4`}>
    <View style={tw`flex-row justify-between items-center  mb-2`}>
      <Text style={tw`font-semibold text-base`}>{title}</Text>
      <TouchableOpacity onPress={onPressMore} style={tw`flex-row items-center`}>
        <Text style={tw`text-gray-500 text-sm`}>더 보기</Text>
        <Icon name="chevron-forward" size={16} color="#999" />
      </TouchableOpacity>
    </View>
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={tw``}>
      {data.slice(0, 10).map(image => (
        <ImageThumbnail key={image.imageUuid} item={image} size="large" />
      ))}
    </ScrollView>
  </View>
);

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
        contentContainerStyle={tw`px-4 pb-4 `}
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
