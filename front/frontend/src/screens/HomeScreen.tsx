import React, {useEffect} from 'react';
import {View, Text, Button, StyleSheet} from 'react-native';
import {requestStoragePermission} from '../utils/permissions';
import {useNavigation} from '@react-navigation/native';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';

type RootStackParamList = {
  Home: undefined;
  PhotoGallery: undefined;
  ChatScreen: undefined;
  LoginScreen: undefined;
};

type HomeScreenNavigationProp = NativeStackNavigationProp<
  RootStackParamList,
  'Home'
>;

export default function HomeScreen() {
  const navigation = useNavigation<HomeScreenNavigationProp>();

  useEffect(() => {
    requestStoragePermission();
  }, []);

  // 만약 ChatScreen으로 파라미터를 전달해야 한다면:
  // navigation.navigate('ChatScreen', { userId: '123' });
  return (
    <View style={styles.container}>
      <Text style={styles.title}>홈 화면입니다</Text>
      <Button
        title="사진 모아보기로 이동"
        onPress={() => navigation.navigate('PhotoGallery')}
      />
      <Button title="채팅방으로 이동하기"
      onPress={() => navigation.navigate('ChatScreen')}
      />
      <Button title="카카오 로그인 페이지 이동"
      onPress={() => navigation.navigate('LoginScreen')}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, justifyContent: 'center', alignItems: 'center'},
  title: {fontSize: 24, marginBottom: 16},
});
