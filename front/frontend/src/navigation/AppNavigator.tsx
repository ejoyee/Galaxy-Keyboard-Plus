import React from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import HomeScreen from '../screens/HomeScreen.tsx';
import PhotoGalleryScreen from '../screens/PhotoGalleryScreen';
import FavoriteGallery from '../screens/FavoriteGallery.tsx';
import AlarmGallery from '../screens/AlarmGallery.tsx';

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Home" component={HomeScreen} />
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
