import {Button, StyleSheet, Text, View} from 'react-native';
import React, {useEffect} from 'react';

import type {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {requestStoragePermission} from '../utils/permissions';
import {uploadTop50Screenshots} from '../utils/testUploader';
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
  const {setUserId} = useUserStore();

  useEffect(() => {
    requestStoragePermission();
    setUserId('dajeong');
  }, [setUserId]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>홈 화면입니다</Text>
      <Button
        title="사진 모아보기로 이동"
        onPress={() => navigation.navigate('PhotoGallery')}
      />

      {/* 🍧 테스트 업로드 버튼 추가 */}
      <View style={{marginTop: 20}}>
        <Button
          title="🧪 스크린샷 50장 업로드 테스트"
          onPress={uploadTop50Screenshots}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, justifyContent: 'center', alignItems: 'center'},
  title: {fontSize: 24, marginBottom: 16},
});
