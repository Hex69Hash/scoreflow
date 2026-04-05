import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useFonts } from 'expo-font';

export default function RootLayout() {
  const [loaded] = useFonts({
    Bebas: require('../assets/fonts/BebasNeue-Regular.ttf'),
  });

  // ⛔ Wait until font loads
  if (!loaded) return null;

  return (
    <>
      <StatusBar style="light" backgroundColor="#3467D6"/>
      <Stack
        screenOptions={{
          headerShown: false,
        }}
      />
    </>
  );
}