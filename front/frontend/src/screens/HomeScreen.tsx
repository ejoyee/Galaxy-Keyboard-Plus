import {Button, StyleSheet, Text, View} from 'react-native';
import React, {useEffect} from 'react';

import type {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {requestStoragePermission} from '../utils/permissions';
import {uploadImagesToServer} from '../utils/uploadHelper';
import {useNavigation} from '@react-navigation/native';
import {useUserStore} from '../stores/useUserStore.ts';

type RootStackParamList = {
  Home: undefined;
  PhotoGallery: undefined;
};

type HomeScreenNavigationProp = NativeStackNavigationProp<
  RootStackParamList,
  'Home'
>;

export default function HomeScreen() {
  const navigation = useNavigation<HomeScreenNavigationProp>();

  const {userId, setUserId} = useUserStore();

  useEffect(() => {
    requestStoragePermission();
    setUserId('dajeong');
  }, [setUserId]);

  // const handleTestUpload = () => {
  //   // 🍧
  //   const dummyImages = [
  //     {
  //       uri: 'content://media/external/images/media/1234',
  //       contentId: '1234',
  //       filename: 'test-image.jpg',
  //       timestamp: Date.now(),
  //     },
  //   ];
  //   uploadImagesToServer(dummyImages, userId);
  // };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>홈 화면입니다</Text>
      <Button
        title="사진 모아보기로 이동"
        onPress={() => navigation.navigate('PhotoGallery')}
      />
      {/* <Button title="업로드 테스트" onPress={handleTestUpload} /> */}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, justifyContent: 'center', alignItems: 'center'},
  title: {fontSize: 24, marginBottom: 16},
});
