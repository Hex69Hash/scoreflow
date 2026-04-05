import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = '@assam_board_saved';

export type SavedEntry = {
  id: string;
  board: string;
  roll: string;
  number: string;
  regNo?: string;
  studentName?: string;
  savedAt: string;
};

export async function getSaved(): Promise<SavedEntry[]> {
  try {
    const d = await AsyncStorage.getItem(KEY);
    return d ? JSON.parse(d) : [];
  } catch {
    return [];
  }
}

export async function addSaved(e: Omit<SavedEntry, 'id' | 'savedAt'>): Promise<SavedEntry[]> {
  const list = await getSaved();
  const dup = list.find(x => x.board === e.board && x.roll === e.roll && x.number === e.number);
  if (dup) return list;
  const entry: SavedEntry = { ...e, id: Date.now().toString(), savedAt: new Date().toISOString() };
  list.unshift(entry);
  const trimmed = list.slice(0, 10);
  await AsyncStorage.setItem(KEY, JSON.stringify(trimmed));
  return trimmed;
}

export async function removeSaved(id: string): Promise<SavedEntry[]> {
  let list = await getSaved();
  list = list.filter(x => x.id !== id);
  await AsyncStorage.setItem(KEY, JSON.stringify(list));
  return list;
}
