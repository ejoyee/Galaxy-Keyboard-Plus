import React from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import HomeScreen from '../screens/HomeScreen.tsx';
import ChatScreen from '../screens/ChatScreen.tsx'; // ChatScreen 임포트
import PhotoGalleryScreen from '../screens/PhotoGalleryScreen';
import FavoriteGallery from '../screens/FavoriteGallery.tsx';
import AlarmGallery from '../screens/AlarmGallery.tsx';

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  return (
    <NavigationContainer>
      {/* 초기 화면을 Home으로 설정하려면 initialRouteName="Home"을 명시할 수 있습니다. */}
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="ChatScreen" component={ChatScreen} />
        <Stack.Screen
          name="PhotoGallery"
          component={PhotoGalleryScreen}
          options={{headerShown: false}}
        />
        <Stack.Screen name="FavoriteGallery" component={FavoriteGallery} />
        <Stack.Screen name="AlarmGallery" component={AlarmGallery} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}