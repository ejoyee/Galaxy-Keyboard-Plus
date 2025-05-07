import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

/** 기존 화면 */
import HomeScreen from '../screens/HomeScreen';
import ChatScreen from '../screens/ChatScreen';
import PhotoGalleryScreen from '../screens/PhotoGalleryScreen';
import FavoriteGallery from '../screens/FavoriteGallery';
import AlarmGallery from '../screens/AlarmGallery';

/** 🔹 로그인 화면 추가 */
import LoginScreen from '../screens/LoginScreen';

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  return (
    <NavigationContainer>
      {/* ▸ 필요하면 initialRouteName="Login" 으로 바꿔도 됩니다 */}
      <Stack.Navigator initialRouteName="Home" screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Login" component={LoginScreen} />

        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="ChatScreen" component={ChatScreen} />

        <Stack.Screen
          name="PhotoGallery"
          component={PhotoGalleryScreen}
        />

        <Stack.Screen name="FavoriteGallery" component={FavoriteGallery} />
        <Stack.Screen name="AlarmGallery" component={AlarmGallery} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
