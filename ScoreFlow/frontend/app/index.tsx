import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  ActivityIndicator, Share, Linking, KeyboardAvoidingView, Platform,
  Keyboard, Animated, Modal, Image, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system/legacy';
import { getSaved, addSaved, removeSaved, SavedEntry } from '../utils/storage';

const API = process.env.EXPO_PUBLIC_BACKEND_URL;

const C = {
  primary: '#3467D6', accent: '#2563EB', bg: '#FFFFFF', surface: '#F8F9FA',
  surfaceOff: '#E5E7EB', text: '#111827', textSec: '#4B5563', textDis: '#9CA3AF',
  textOn: '#FFFFFF', errBg: '#FEF2F2', errText: '#DC2626', warnBg: '#FEF3C7',
  warnText: '#92400E', border: '#D1D5DB', borderFocus: '#2563EB',
  successText: '#16A34A', successBg: '#F0FDF4', overlay: 'rgba(0,0,0,0.5)',
  redAccent: '#DC2626', redLight: '#FEF2F2',
};

function normSeba(raw: string): string {
  let v = raw.trim().toUpperCase().replace(/\s+/g, '');
  if (v.length === 7 && /^[A-Z]\d{2}\d{4}$/.test(v) && !v.includes('-')) v = v.slice(0, 3) + '-' + v.slice(3);
  return v;
}

function pdfHtml(d: any): string {
  const rows = (d.subjects || []).map((s: any, i: number) =>
    `<tr style="background:${i % 2 === 0 ? '#F8FAFC' : '#FFF'}"><td style="padding:10px 14px;border-bottom:1px solid #F3F4F6">${s.subject}</td><td style="padding:10px 14px;border-bottom:1px solid #F3F4F6;text-align:right;font-weight:600">${s.marks} / ${s.full_marks}</td></tr>`
  ).join('');
  return `<html><head><meta charset="utf-8"><style>
body{font-family:Arial,sans-serif;margin:0;padding:30px;color:#111827}
.card{border:2px solid #003B73;border-radius:8px;overflow:hidden}
.hdr{background:#003B73;color:#FFF;padding:24px;text-align:center}
.hdr h1{margin:0;font-size:18px;letter-spacing:0.5px}
.hdr p{margin:4px 0 0;font-size:14px;opacity:0.85}
.sec{padding:16px;border-bottom:1px solid #E5E7EB}
.st{font-size:11px;font-weight:bold;color:#6B7280;letter-spacing:1px;margin-bottom:8px}
.dr{display:flex;padding:4px 0}.dl{width:130px;color:#6B7280;font-size:13px}.dv{font-weight:600;font-size:14px}
table{width:100%;border-collapse:collapse}
th{background:#003B73;color:#FFF;padding:10px 14px;text-align:left;font-size:13px}
th:last-child{text-align:right}
.sum{padding:16px;background:#F8FAFC}
.sr{display:flex;justify-content:space-between;padding:6px 0}
.sl{color:#6B7280;font-size:14px}.sv{font-weight:bold;font-size:16px}
.badge{display:inline-block;padding:4px 16px;border-radius:4px;color:#FFF;font-weight:bold;font-size:14px}
.pass{background:#16A34A}.fail{background:#DC2626}
.ft{text-align:center;padding:12px;color:#9CA3AF;font-size:11px;border-top:1px solid #E5E7EB}
</style></head><body><div class="card">
<div class="hdr"><h1>${d.full_name || ''}</h1><p>${d.exam_name || ''}</p></div>
<div class="sec"><div class="st">STUDENT DETAILS</div>
<div class="dr"><span class="dl">Name</span><span class="dv">${d.student_name || ''}</span></div>
<div class="dr"><span class="dl">Roll</span><span class="dv">${d.roll || ''}</span></div>
<div class="dr"><span class="dl">Number</span><span class="dv">${d.number || ''}</span></div>
${d.registration_number ? `<div class="dr"><span class="dl">Reg No</span><span class="dv">${d.registration_number}</span></div>` : ''}
<div class="dr"><span class="dl">Year</span><span class="dv">${d.year || ''}</span></div></div>
<div class="sec"><div class="st">MARKS OBTAINED</div>
<table><tr><th>Subject</th><th style="text-align:right">Marks</th></tr>${rows}</table></div>
<div class="sum">
<div class="sr"><span class="sl">Total Marks</span><span class="sv">${d.total_marks} / ${d.full_total_marks}</span></div>
<div class="sr"><span class="sl">Percentage</span><span class="sv">${d.percentage}%</span></div>
<div class="sr"><span class="sl">Result</span><span class="badge ${d.result_status === 'PASS' ? 'pass' : 'fail'}">${d.result_status}</span></div></div>
<div class="ft">Verify this result on the official board website &bull; Assam Board Results Portal</div>
</div></body></html>`;
}

export default function Index() {
  const [board, setBoard] = useState<'seba' | 'ahsec'>('seba');
  const [roll, setRoll] = useState('');
  const [number, setNumber] = useState('');
  const [regNo, setRegNo] = useState('');
  const [loading, setLoading] = useState(false);
  const [rollErr, setRollErr] = useState('');
  const [numErr, setNumErr] = useState('');
  const [regErr, setRegErr] = useState('');
  const [generalErr, setGeneralErr] = useState('');
  const [result, setResult] = useState<any>(null);
  const [modalVis, setModalVis] = useState(false);
  const [modalData, setModalData] = useState<any>(null);
  const [helpVis, setHelpVis] = useState(false);
  const [saved, setSaved] = useState<SavedEntry[]>([]);
  const [pdfLoad, setPdfLoad] = useState(false);
  const [pngLoad, setPngLoad] = useState(false);
  const [rollF, setRollF] = useState(false);
  const [numF, setNumF] = useState(false);
  const [regF, setRegF] = useState(false);

  const shR = useRef(new Animated.Value(0)).current;
  const shN = useRef(new Animated.Value(0)).current;
  const shG = useRef(new Animated.Value(0)).current;
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => { loadSaved(); }, []);

  const loadSaved = async () => setSaved(await getSaved());

  const shake = useCallback((a: Animated.Value) => {
    Animated.sequence([
      Animated.timing(a, { toValue: 10, duration: 50, useNativeDriver: true }),
      Animated.timing(a, { toValue: -10, duration: 50, useNativeDriver: true }),
      Animated.timing(a, { toValue: 10, duration: 50, useNativeDriver: true }),
      Animated.timing(a, { toValue: 0, duration: 50, useNativeDriver: true }),
    ]).start();
  }, []);

  const clrErr = () => { setRollErr(''); setNumErr(''); setRegErr(''); setGeneralErr(''); };

  const switchBoard = (b: 'seba' | 'ahsec') => {
    setBoard(b); setRoll(''); setNumber(''); setRegNo(''); setResult(null); clrErr();
  };

  const onRollCh = (t: string) => { setRoll(board === 'seba' ? t.toUpperCase().replace(/\s+/g, '') : t.replace(/\s+/g, '')); if (rollErr) setRollErr(''); if (generalErr) setGeneralErr(''); };
  const onRollBlur = () => { setRollF(false); if (board === 'seba' && roll) setRoll(normSeba(roll)); };
  const onNumCh = (t: string) => { setNumber(t.replace(/\s+/g, '')); if (numErr) setNumErr(''); if (generalErr) setGeneralErr(''); };
  const onRegCh = (t: string) => { setRegNo(t.replace(/\s+/g, '')); if (regErr) setRegErr(''); if (generalErr) setGeneralErr(''); };

  const validate = (): boolean => {
    let ok = true;
    if (board === 'seba') {
      const nr = normSeba(roll);
      if (!nr) { setRollErr('Please enter your roll number'); shake(shR); ok = false; }
      else if (!/^[A-Z]\d{2}-\d{4}$/.test(nr)) { setRollErr('Roll must match BXX-XXXX (e.g., B26-0816)'); shake(shR); ok = false; }
      if (!number.trim()) { setNumErr('Please enter your number'); shake(shN); ok = false; }
      else if (!/^\d+$/.test(number.trim())) { setNumErr('Number must contain only digits'); shake(shN); ok = false; }
      else if (number.trim().length < 3) { setNumErr('Number must be at least 3 digits'); shake(shN); ok = false; }
    } else {
      if (!roll.trim()) { setRollErr('Please enter your roll number'); shake(shR); ok = false; }
      else if (!/^\d+$/.test(roll.trim())) { setRollErr('Roll must contain only digits'); shake(shR); ok = false; }
      if (!number.trim()) { setNumErr('Please enter your number'); shake(shN); ok = false; }
      else if (!/^\d+$/.test(number.trim())) { setNumErr('Number must contain only digits'); shake(shN); ok = false; }
      if (!regNo.trim()) { setRegErr('Please enter your registration number'); shake(shG); ok = false; }
      else if (!/^\d+$/.test(regNo.trim())) { setRegErr('Registration number must contain only digits'); shake(shG); ok = false; }
    }
    return ok;
  };

  const handleCheck = async () => {
    Keyboard.dismiss(); setResult(null); setGeneralErr(''); setModalData(null);
    if (board === 'seba') setRoll(normSeba(roll));
    if (!validate()) return;
    setLoading(true);
    try {
      const body: any = { board, roll: board === 'seba' ? normSeba(roll) : roll.trim(), number: number.trim() };
      if (board === 'ahsec') body.registration_number = regNo.trim();
      const res = await fetch(`${API}/api/check-result`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await res.json();
      if (data.success) {
        setResult(data);
        const entry = { board, roll: data.roll, number: data.number, regNo: data.registration_number, studentName: data.student_name };
        setSaved(await addSaved(entry));
      } else if (data.error_type === 'not_released') { setModalData(data); setModalVis(true); }
      else if (data.error_type === 'unsupported_year') setGeneralErr(data.error);
      else setGeneralErr(data.error || 'Something went wrong.');
    } catch { setGeneralErr('Network error. Please check your internet connection.'); }
    finally { setLoading(false); }
  };

  const handlePdf = async () => {
    if (!result) return;
    setPdfLoad(true);
    try {
      const { uri } = await Print.printToFileAsync({ html: pdfHtml(result) });
      if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(uri, { mimeType: 'application/pdf', dialogTitle: 'Save Result PDF' });
      else Alert.alert('PDF Saved', `File saved to: ${uri}`);
    } catch {Alert.alert('Error', 'Something went wrong');}
    finally { setPdfLoad(false); }
  };

  const handlePng = async () => {
    if (!result) return;
    setPngLoad(true);
    try {
      const res = await fetch(`${API}/api/generate-image`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(result) });
      const data = await res.json();
      if (data.success && data.image) {
        const fileUri = FileSystem.cacheDirectory + 'assam_board_result.png';
        await FileSystem.writeAsStringAsync(fileUri, data.image, { encoding: FileSystem.EncodingType.Base64 });
        if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(fileUri, { mimeType: 'image/png' });
        else Alert.alert('Image Saved', `Saved to: ${fileUri}`);
      } else Alert.alert('Error', data.error || 'Could not generate image');
    } catch { Alert.alert('Error', 'Could not generate image'); }
    finally { setPngLoad(false); }
  };

  const handleShare = async () => {
    if (!result) return;
    const bl = board === 'seba' ? 'SEBA (HSLC)' : 'AHSEC (HS)';
    let msg = `I checked my Assam Board Result using this app!\n\nBoard: ${bl}\nName: ${result.student_name}\nRoll: ${result.roll}\nResult: ${result.result_status}\nPercentage: ${result.percentage}%\n\nCheck your result: ${result.result_url}`;
    try { await Share.share({ message: msg, title: 'Assam Board Result' }); } catch {}
  };

  const handleQuickCheck = (e: SavedEntry) => {
    setBoard(e.board as 'seba' | 'ahsec');
    setRoll(e.roll); setNumber(e.number); setRegNo(e.regNo || '');
    setResult(null); clrErr();
    scrollRef.current?.scrollTo({ y: 0, animated: true });
  };

  const handleDeleteSaved = async (id: string) => setSaved(await removeSaved(id));

  const isSeba = board === 'seba';

  return (
    <SafeAreaView style={s.safe} edges={['top']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={s.flex}>
        <ScrollView ref={scrollRef} style={s.flex} contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>

          {/* ── Header ── */}
          <View style={{
  backgroundColor: '#3467D6',
  paddingTop: 60,
  paddingBottom: 30,
  paddingHorizontal: 20,
  borderBottomLeftRadius: 20,
  borderBottomRightRadius: 20,
}}>

  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
    
    {/* LEFT TEXT */}
    <View>
      <Text style={{
        fontSize: 32,
        fontFamily: 'Bebas',
        letterSpacing: 3,
        fontWeight: '600',
        color: '#FFFFFF'
      }}>
        score
      </Text>

      <Text style={{
        fontSize: 37,
        fontWeight: '800',
        color: '#7FB3FF',
        marginTop: -6
      }}>
        flow
      </Text>

      <Text style={{
        fontSize: 10,
        letterSpacing: 2,
        color: '#AFC6E0',
        marginTop: 6
      }}>
        ACADEMIC RESULTS PORTAL
      </Text>
    </View>

    {/* RIGHT ICON */}
    <View style={{
  width: 70,
  height: 70,
  borderRadius: 35,
  overflow: 'hidden',
  backgroundColor: '#2E6AA3',
  justifyContent: 'center',
  alignItems: 'center',
}}>
  <Image
    source={require('../assets/images/logo.png')}
    style={{
      width: '120%',
      height: '120%',
      resizeMode: 'cover'
    }}
  />
</View>

  </View>

</View>

          

          {/* ── Form Card ── */}
          <View style={s.card} testID="main-form-card">
            <Text style={s.label}>SELECT BOARD</Text>
            <View style={s.toggle} testID="board-selection-container">
              <TouchableOpacity testID="toggle-board-seba" style={[s.togBtn, isSeba && s.togOn]} onPress={() => switchBoard('seba')} activeOpacity={0.8}>
                <Text style={[s.togLbl, isSeba && s.togLblOn]}>SEBA</Text>
                <Text style={[s.togSub, isSeba && s.togSubOn]}>Class 10 · HSLC</Text>
              </TouchableOpacity>
              <TouchableOpacity testID="toggle-board-ahsec" style={[s.togBtn, !isSeba && s.togOn]} onPress={() => switchBoard('ahsec')} activeOpacity={0.8}>
                <Text style={[s.togLbl, !isSeba && s.togLblOn]}>AHSEC</Text>
                <Text style={[s.togSub, !isSeba && s.togSubOn]}>Class 12 · HS</Text>
              </TouchableOpacity>
            </View>

            <Text style={s.label}>ROLL</Text>
            <Animated.View style={{ transform: [{ translateX: shR }] }}>
              <TextInput testID="input-roll" style={[s.input, rollF && s.inputF, rollErr ? s.inputE : null]}
                placeholder={isSeba ? 'e.g., B26-0816' : 'e.g., 0259'} placeholderTextColor={C.textDis}
                value={roll} onChangeText={onRollCh} onFocus={() => setRollF(true)} onBlur={onRollBlur}
                autoCapitalize={isSeba ? 'characters' : 'none'} keyboardType={isSeba ? 'default' : 'numeric'}
                maxLength={isSeba ? 8 : 10} accessibilityLabel="Roll number input" />
            </Animated.View>
            <Text style={s.helper}>{isSeba ? 'Enter Roll as shown on your admit card (e.g., B26-0816)' : 'Enter your roll number (digits only)'}</Text>
            {rollErr ? <ErrLine text={rollErr} tid="roll-error" /> : null}

            <Text style={[s.label, { marginTop: 18 }]}>NUMBER</Text>
            <Animated.View style={{ transform: [{ translateX: shN }] }}>
              <TextInput testID="input-number" style={[s.input, numF && s.inputF, numErr ? s.inputE : null]}
                placeholder={isSeba ? 'e.g., 0238' : 'e.g., 20060'} placeholderTextColor={C.textDis}
                value={number} onChangeText={onNumCh} onFocus={() => setNumF(true)} onBlur={() => setNumF(false)}
                keyboardType="numeric" maxLength={10} accessibilityLabel="Number input" />
            </Animated.View>
            <Text style={s.helper}>Enter the number from your admit card</Text>
            {numErr ? <ErrLine text={numErr} tid="number-error" /> : null}

            {!isSeba && (
              <>
                <Text style={[s.label, { marginTop: 18 }]}>REGISTRATION NUMBER</Text>
                <Animated.View style={{ transform: [{ translateX: shG }] }}>
                  <TextInput testID="input-registration" style={[s.input, regF && s.inputF, regErr ? s.inputE : null]}
                    placeholder="e.g., 042283" placeholderTextColor={C.textDis}
                    value={regNo} onChangeText={onRegCh} onFocus={() => setRegF(true)} onBlur={() => setRegF(false)}
                    keyboardType="numeric" maxLength={10} accessibilityLabel="Registration number input" />
                </Animated.View>
                <Text style={s.helper}>Enter registration number from your admit card</Text>
                {regErr ? <ErrLine text={regErr} tid="reg-error" /> : null}
              </>
            )}

            <View style={s.exBox} testID="example-section">
              <Text style={s.exTitle}>EXAMPLE</Text>
              {isSeba ? (<><ExRow l="Roll:" v="B26-0816" /><ExRow l="Number:" v="0238" /></>) : (<><ExRow l="Roll:" v="0259" /><ExRow l="Number:" v="20060" /><ExRow l="Reg No:" v="042283" /></>)}
            </View>

            <TouchableOpacity testID="btn-help-link" style={s.helpLink} onPress={() => setHelpVis(true)} activeOpacity={0.7}>
              <Ionicons name="help-circle-outline" size={16} color={C.accent} />
              <Text style={s.helpLinkTxt}>Where to find this on admit card?</Text>
            </TouchableOpacity>

            {generalErr ? (<View style={s.genErr} testID="general-error"><Ionicons name="warning" size={16} color={C.errText} /><Text style={s.genErrTxt}>{generalErr}</Text></View>) : null}

            <TouchableOpacity testID="btn-check-result" style={[s.cta, loading && s.ctaOff]} onPress={handleCheck} disabled={loading} activeOpacity={0.8}>
              {loading ? <ActivityIndicator testID="indicator-loading" color={C.textOn} size="small" /> : (<><Ionicons name="search" size={20} color={C.textOn} /><Text style={s.ctaTxt}>Check Result</Text></>)}
            </TouchableOpacity>
          </View>

          {/* ── Marksheet Card ── */}
          {result && (
            <View style={s.mk} testID="marksheet-card">
              <View style={s.mkHdr}>
                <Text style={s.mkBoard}>{result.full_name}</Text>
                <Text style={s.mkExam}>{result.exam_name}</Text>
              </View>

              <View style={s.mkSec}>
                <Text style={s.mkSecTitle}>STUDENT DETAILS</Text>
                <DRow l="Name" v={result.student_name} />
                <DRow l="Roll" v={result.roll} />
                <DRow l="Number" v={result.number} />
                {result.registration_number && <DRow l="Reg No" v={result.registration_number} />}
                <DRow l="Year" v={String(result.year)} />
              </View>

              <View style={s.mkSec}>
                <Text style={s.mkSecTitle}>MARKS OBTAINED</Text>
                <View style={s.tblHdr}>
                  <Text style={s.thSubj}>Subject</Text>
                  <Text style={s.thMark}>Marks</Text>
                </View>
                {result.subjects.map((sub: any, i: number) => (
                  <View key={i} style={[s.tblRow, i % 2 === 0 && s.tblRowAlt]}>
                    <Text style={s.tdSubj}>{sub.subject}</Text>
                    <Text style={[s.tdMark, sub.marks < 30 && { color: C.errText }]}>{sub.marks} / {sub.full_marks}</Text>
                  </View>
                ))}
              </View>

              <View style={s.mkSum}>
                <View style={s.mkSumRow}><Text style={s.mkSumLbl}>Total Marks</Text><Text style={s.mkSumVal}>{result.total_marks} / {result.full_total_marks}</Text></View>
                <View style={s.mkSumRow}><Text style={s.mkSumLbl}>Percentage</Text><Text style={s.mkSumVal}>{result.percentage}%</Text></View>
                <View style={s.mkSumRow}>
                  <Text style={s.mkSumLbl}>Result</Text>
                  <View style={[s.badge, result.result_status === 'PASS' ? s.badgePass : s.badgeFail]}>
                    <Ionicons name={result.result_status === 'PASS' ? 'checkmark-circle' : 'close-circle'} size={16} color="#FFF" />
                    <Text style={s.badgeTxt}>{result.result_status}</Text>
                  </View>
                </View>
              </View>

              <View style={s.mkVerify}>
                <Ionicons name="shield-checkmark-outline" size={13} color={C.textDis} />
                <Text style={s.mkVerifyTxt}>Verify this result on the official board website</Text>
              </View>

              <View style={s.mkActions}>
                <TouchableOpacity testID="btn-download-pdf" style={s.mkActBtn} onPress={handlePdf} disabled={pdfLoad} activeOpacity={0.8}>
                  {pdfLoad ? <ActivityIndicator size="small" color={C.primary} /> : <Ionicons name="document-text-outline" size={18} color={C.primary} />}
                  <Text style={s.mkActTxt}>{pdfLoad ? 'Saving...' : 'PDF'}</Text>
                </TouchableOpacity>
                <TouchableOpacity testID="btn-download-png" style={s.mkActBtn} onPress={handlePng} disabled={pngLoad} activeOpacity={0.8}>
                  {pngLoad ? <ActivityIndicator size="small" color={C.primary} /> : <Ionicons name="image-outline" size={18} color={C.primary} />}
                  <Text style={s.mkActTxt}>{pngLoad ? 'Saving...' : 'Image'}</Text>
                </TouchableOpacity>
                <TouchableOpacity testID="btn-share-result" style={s.mkActBtn} onPress={handleShare} activeOpacity={0.8}>
                  <Ionicons name="share-social-outline" size={18} color={C.primary} />
                  <Text style={s.mkActTxt}>Share</Text>
                </TouchableOpacity>
                <TouchableOpacity testID="btn-visit-official" style={[s.mkActBtn, s.mkActPrimary]} onPress={() => Linking.openURL(result.result_url)} activeOpacity={0.8}>
                  <Ionicons name="open-outline" size={18} color={C.textOn} />
                  <Text style={[s.mkActTxt, s.mkActTxtP]}>Official</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {/* ── Saved Results ── */}
          {saved.length > 0 && (
            <View style={s.savedSection} testID="saved-results-section">
              <View style={s.savedHdr}>
                <Ionicons name="bookmark" size={18} color={C.primary} />
                <Text style={s.savedTitle}>Saved Results</Text>
              </View>
              {saved.map(e => (
                <View key={e.id} style={s.savedItem} testID={`saved-item-${e.id}`}>
                  <View style={s.savedInfo}>
                    <View style={[s.savedBadge, { backgroundColor: e.board === 'seba' ? '#EFF6FF' : '#FEF3C7' }]}>
                      <Text style={[s.savedBadgeTxt, { color: e.board === 'seba' ? C.accent : C.warnText }]}>{e.board.toUpperCase()}</Text>
                    </View>
                    <View style={s.savedDetails}>
                      {e.studentName && <Text style={s.savedName} numberOfLines={1}>{e.studentName}</Text>}
                      <Text style={s.savedMeta} numberOfLines={1}>Roll: {e.roll} · No: {e.number}{e.regNo ? ` · Reg: ${e.regNo}` : ''}</Text>
                    </View>
                  </View>
                  <View style={s.savedActions}>
                    <TouchableOpacity testID={`btn-quick-check-${e.id}`} style={s.savedCheckBtn} onPress={() => handleQuickCheck(e)} activeOpacity={0.7}>
                      <Ionicons name="refresh" size={16} color={C.accent} />
                    </TouchableOpacity>
                    <TouchableOpacity testID={`btn-delete-saved-${e.id}`} style={s.savedDelBtn} onPress={() => handleDeleteSaved(e.id)} activeOpacity={0.7}>
                      <Ionicons name="trash-outline" size={16} color={C.errText} />
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
            </View>
          )}

          {/* ── Footer ── */}
          <View style={s.footer} testID="banner-disclaimer">
            <Ionicons name="shield-checkmark-outline" size={14} color={C.textSec} />
            <Text style={s.footerTxt}>
              Results are sourced from official board websites. This is an unofficial portal. For official results, visit{' '}
              <Text style={s.footerLink} onPress={() => Linking.openURL('https://sebaonline.org/')}>SEBA</Text>
              {' / '}
              <Text style={s.footerLink} onPress={() => Linking.openURL('https://ahsec.assam.gov.in/')}>AHSEC</Text>
              {' '}websites.
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* ── Not Released Modal ── */}
      <Modal visible={modalVis} transparent animationType="fade" onRequestClose={() => setModalVis(false)} testID="modal-not-released">
        <View style={s.overlay}>
          <View style={s.modal} testID="modal-content">
            <View style={s.mIcon}><Ionicons name="time-outline" size={32} color={C.redAccent} /></View>
            <Text style={s.mTitle}>{modalData?.title}</Text>
            <Text style={s.mSub}>{modalData?.subtitle}</Text>
            <View style={s.mDiv} />
            <Text style={s.mMsg}>{modalData?.message}</Text>
            {modalData?.note ? (<View style={s.mNoteBox}><Ionicons name="calendar-outline" size={14} color={C.warnText} /><Text style={s.mNote}>{modalData.note}</Text></View>) : null}
            <TouchableOpacity testID="btn-modal-close" style={s.mBtn} onPress={() => setModalVis(false)} activeOpacity={0.8}><Text style={s.mBtnTxt}>Got it</Text></TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* ── Help Modal ── */}
      <Modal visible={helpVis} transparent animationType="fade" onRequestClose={() => setHelpVis(false)} testID="modal-help">
        <View style={s.overlay}>
          <View style={s.modal} testID="help-modal-content">
            <View style={[s.mIcon, { backgroundColor: '#EFF6FF' }]}><Ionicons name="document-text-outline" size={32} color={C.accent} /></View>
            <Text style={s.mTitle}>Finding Your Details</Text>
            <Text style={s.mSub}>{isSeba ? 'SEBA (HSLC) Admit Card' : 'AHSEC (HS) Admit Card'}</Text>
            <View style={s.mDiv} />
            {isSeba ? (<><HStep n="1" t="Look at the top-right of your Admit Card" /><HStep n="2" t="Roll is a code like B26-0816" /><HStep n="3" t="Number is the separate numeric ID like 0238" /><HStep n="4" t="Enter both exactly as printed" /></>) : (<><HStep n="1" t="Check the top section of your AHSEC Admit Card" /><HStep n="2" t="Roll is a short numeric code like 0259" /><HStep n="3" t="Number is your candidate number like 20060" /><HStep n="4" t="Registration No is your reg ID like 042283" /><HStep n="5" t="Enter all details exactly as printed" /></>)}
            <TouchableOpacity testID="btn-help-close" style={[s.mBtn, { backgroundColor: C.accent }]} onPress={() => setHelpVis(false)} activeOpacity={0.8}><Text style={s.mBtnTxt}>Understood</Text></TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function ErrLine({ text, tid }: { text: string; tid: string }) {
  return (<View style={s.errRow} testID={tid}><Ionicons name="alert-circle" size={14} color={C.errText} /><Text style={s.errTxt}>{text}</Text></View>);
}
function ExRow({ l, v }: { l: string; v: string }) {
  return (<View style={s.exRow}><Text style={s.exLbl}>{l}</Text><Text style={s.exVal}>{v}</Text></View>);
}
function DRow({ l, v }: { l: string; v: string }) {
  return (<View style={s.dRow}><Text style={s.dLbl}>{l}</Text><Text style={s.dVal}>{v}</Text></View>);
}
function HStep({ n, t }: { n: string; t: string }) {
  return (<View style={s.hItem}><Text style={s.hN}>{n}.</Text><Text style={s.hTxt}>{t}</Text></View>);
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.primary },
  flex: { flex: 1 },
  scroll: { flexGrow: 1, backgroundColor: '#F3F4F6' },

  // Header
  header: { backgroundColor: C.primary, paddingVertical: 22, paddingHorizontal: 24, alignItems: 'center' },
  logoBox: { width: 52, height: 52, borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.15)', alignItems: 'center', justifyContent: 'center', marginBottom: 10 },
  logoImg: { width: 36, height: 36, borderRadius: 6 },
  headerTitle: { fontSize: 20, fontWeight: 'bold', color: C.textOn, letterSpacing: 0.3, textAlign: 'center' },
  headerSub: { fontSize: 12, color: 'rgba(255,255,255,0.75)', fontWeight: '500', marginTop: 3 },

  banner: { flexDirection: 'row', alignItems: 'center', backgroundColor: C.warnBg, paddingVertical: 9, paddingHorizontal: 16, gap: 8 },
  bannerTxt: { fontSize: 12, color: C.warnText, fontWeight: '500', flex: 1 },

  card: { margin: 16, padding: 20, backgroundColor: C.bg, borderRadius: 12, borderWidth: 1, borderColor: C.border, elevation: 2 },

  label: { fontSize: 11, fontWeight: 'bold', color: C.textSec, letterSpacing: 1.2, marginBottom: 6, marginTop: 14 },

  toggle: { flexDirection: 'row', borderRadius: 8, borderWidth: 1, borderColor: C.border, overflow: 'hidden' },
  togBtn: { flex: 1, paddingVertical: 12, alignItems: 'center', backgroundColor: C.surface },
  togOn: { backgroundColor: C.accent },
  togLbl: { fontSize: 15, fontWeight: 'bold', color: C.textSec },
  togLblOn: { color: C.textOn },
  togSub: { fontSize: 10, color: C.textDis, marginTop: 1 },
  togSubOn: { color: 'rgba(255,255,255,0.85)' },

  input: { height: 52, borderWidth: 1.5, borderColor: C.border, borderRadius: 8, paddingHorizontal: 14, fontSize: 17, color: C.text, backgroundColor: C.bg, fontWeight: '500' },
  inputF: { borderColor: C.borderFocus },
  inputE: { borderColor: C.errText, backgroundColor: C.errBg },
  helper: { fontSize: 11, color: C.textDis, marginTop: 4 },

  errRow: { flexDirection: 'row', alignItems: 'center', marginTop: 5, gap: 5 },
  errTxt: { fontSize: 12, color: C.errText, fontWeight: '500' },

  exBox: { marginTop: 16, backgroundColor: '#F0F4F8', borderRadius: 8, padding: 14, borderLeftWidth: 3, borderLeftColor: C.accent },
  exTitle: { fontSize: 11, fontWeight: 'bold', color: C.textSec, letterSpacing: 0.8, marginBottom: 6 },
  exRow: { flexDirection: 'row', alignItems: 'center', marginTop: 3 },
  exLbl: { fontSize: 13, color: C.textSec, fontWeight: '600', width: 65 },
  exVal: { fontSize: 14, color: C.text, fontWeight: '700', fontFamily: Platform.OS === 'ios' ? 'Courier New' : 'monospace' },

  helpLink: { flexDirection: 'row', alignItems: 'center', marginTop: 12, gap: 5 },
  helpLinkTxt: { fontSize: 12, color: C.accent, fontWeight: '500' },

  genErr: { flexDirection: 'row', alignItems: 'flex-start', marginTop: 14, backgroundColor: C.errBg, padding: 12, borderRadius: 8, gap: 8 },
  genErrTxt: { fontSize: 13, color: C.errText, fontWeight: '500', flex: 1 },

  cta: { height: 54, backgroundColor: C.accent, borderRadius: 8, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 20, gap: 8 },
  ctaOff: { backgroundColor: C.surfaceOff },
  ctaTxt: { fontSize: 16, fontWeight: 'bold', color: C.textOn },

  // Marksheet
  mk: { marginHorizontal: 16, marginBottom: 16, backgroundColor: C.bg, borderRadius: 12, borderWidth: 2, borderColor: C.primary, overflow: 'hidden', elevation: 3 },
  mkHdr: { backgroundColor: C.primary, paddingVertical: 18, paddingHorizontal: 20, alignItems: 'center' },
  mkBoard: { color: 'rgba(255,255,255,0.85)', fontSize: 13, fontWeight: '600' },
  mkExam: { color: C.textOn, fontSize: 18, fontWeight: 'bold', marginTop: 4, textAlign: 'center' },
  mkSec: { padding: 16, borderBottomWidth: 1, borderBottomColor: '#E5E7EB' },
  mkSecTitle: { fontSize: 11, fontWeight: 'bold', color: '#6B7280', letterSpacing: 1, marginBottom: 10 },
  dRow: { flexDirection: 'row', paddingVertical: 5 },
  dLbl: { width: 80, fontSize: 13, color: '#6B7280', fontWeight: '500' },
  dVal: { flex: 1, fontSize: 14, color: C.text, fontWeight: '600' },
  tblHdr: { flexDirection: 'row', backgroundColor: C.primary, borderRadius: 4, paddingVertical: 10, paddingHorizontal: 14 },
  thSubj: { flex: 1, color: C.textOn, fontSize: 13, fontWeight: 'bold' },
  thMark: { width: 80, color: C.textOn, fontSize: 13, fontWeight: 'bold', textAlign: 'right' },
  tblRow: { flexDirection: 'row', paddingVertical: 10, paddingHorizontal: 14, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  tblRowAlt: { backgroundColor: '#F8FAFC' },
  tdSubj: { flex: 1, fontSize: 14, color: C.text },
  tdMark: { width: 80, fontSize: 14, color: C.text, fontWeight: '600', textAlign: 'right' },

  mkSum: { padding: 16, backgroundColor: '#F8FAFC' },
  mkSumRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 6 },
  mkSumLbl: { fontSize: 14, color: '#6B7280', fontWeight: '500' },
  mkSumVal: { fontSize: 16, color: C.text, fontWeight: 'bold' },
  badge: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 5, borderRadius: 6, gap: 5 },
  badgePass: { backgroundColor: '#16A34A' },
  badgeFail: { backgroundColor: '#DC2626' },
  badgeTxt: { color: C.textOn, fontSize: 14, fontWeight: 'bold' },

  mkVerify: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 10, gap: 5, borderTopWidth: 1, borderTopColor: '#E5E7EB' },
  mkVerifyTxt: { fontSize: 11, color: C.textDis },

  mkActions: { flexDirection: 'row', padding: 12, gap: 8, borderTopWidth: 1, borderTopColor: '#E5E7EB' },
  mkActBtn: { flex: 1, height: 42, borderRadius: 8, borderWidth: 1.5, borderColor: C.primary, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4 },
  mkActPrimary: { backgroundColor: C.primary, borderColor: C.primary },
  mkActTxt: { fontSize: 11, fontWeight: '600', color: C.primary },
  mkActTxtP: { color: C.textOn },

  // Saved
  savedSection: { marginHorizontal: 16, marginBottom: 16, backgroundColor: C.bg, borderRadius: 12, padding: 16, borderWidth: 1, borderColor: C.border },
  savedHdr: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  savedTitle: { fontSize: 16, fontWeight: 'bold', color: C.text },
  savedItem: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  savedInfo: { flexDirection: 'row', alignItems: 'center', flex: 1, gap: 10 },
  savedBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
  savedBadgeTxt: { fontSize: 10, fontWeight: 'bold' },
  savedDetails: { flex: 1 },
  savedName: { fontSize: 13, fontWeight: '600', color: C.text },
  savedMeta: { fontSize: 11, color: C.textSec, marginTop: 2 },
  savedActions: { flexDirection: 'row', gap: 8 },
  savedCheckBtn: { width: 36, height: 36, borderRadius: 8, backgroundColor: '#EFF6FF', alignItems: 'center', justifyContent: 'center' },
  savedDelBtn: { width: 36, height: 36, borderRadius: 8, backgroundColor: C.errBg, alignItems: 'center', justifyContent: 'center' },

  // Footer
  footer: { flexDirection: 'row', alignItems: 'flex-start', paddingHorizontal: 18, paddingVertical: 14, paddingBottom: 28, gap: 8, backgroundColor: C.bg, borderTopWidth: 1, borderTopColor: C.border, marginTop: 'auto' },
  footerTxt: { fontSize: 11, color: C.textSec, lineHeight: 17, flex: 1 },
  footerLink: { color: C.accent, fontWeight: '600', textDecorationLine: 'underline' },

  // Modals
  overlay: { flex: 1, backgroundColor: C.overlay, justifyContent: 'center', alignItems: 'center', padding: 24 },
  modal: { backgroundColor: C.bg, borderRadius: 16, padding: 28, width: '100%', maxWidth: 380, alignItems: 'center' },
  mIcon: { width: 64, height: 64, borderRadius: 32, backgroundColor: C.redLight, alignItems: 'center', justifyContent: 'center', marginBottom: 16 },
  mTitle: { fontSize: 20, fontWeight: 'bold', color: C.text, textAlign: 'center' },
  mSub: { fontSize: 14, color: C.textSec, fontWeight: '500', marginTop: 4, textAlign: 'center' },
  mDiv: { height: 1, backgroundColor: C.border, width: '100%', marginVertical: 16 },
  mMsg: { fontSize: 15, color: C.textSec, textAlign: 'center', lineHeight: 22 },
  mNoteBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: C.warnBg, paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8, marginTop: 14, gap: 6 },
  mNote: { fontSize: 13, color: C.warnText, fontWeight: '600' },
  mBtn: { marginTop: 20, height: 48, backgroundColor: C.primary, borderRadius: 8, alignItems: 'center', justifyContent: 'center', width: '100%' },
  mBtnTxt: { fontSize: 15, fontWeight: 'bold', color: C.textOn },

  hItem: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 10, width: '100%' },
  hN: { fontSize: 14, fontWeight: 'bold', color: C.accent, width: 20 },
  hTxt: { fontSize: 14, color: C.textSec, flex: 1, lineHeight: 20 },
});
