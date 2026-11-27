import {act} from 'react';
import {createRoot} from 'react-dom/client';
import Results from './Results';
import {api} from '../lib/api';
import {useAuth} from '../components/Auth';

// CRA's Jest resolver predates React Router 7's exports map. Browser tests cover real routing.
jest.mock('react-router-dom', () => ({useParams: () => ({id: 'demo'}), Link: ({to, children, ...props}) => <a href={to} {...props}>{children}</a>}), {virtual: true});
jest.mock('../lib/api', () => ({api: {get: jest.fn(), patch: jest.fn()}, message: e => e.message, dateLabel: () => '27 Nov 2026'}));
jest.mock('../components/Auth', () => ({useAuth: jest.fn()}));
jest.mock('../components/GazeReplay', () => ({GazeReplay: () => <div data-testid="replay-preserved"/>}));
jest.mock('sonner', () => ({toast: {success: jest.fn(), error: jest.fn()}}));
// Keep these tests independent of the design-system dependency's browser APIs.
jest.mock('../components/Common', () => ({
  Action: ({children, busy, kind, ...props}) => <button disabled={busy} {...props}>{children}</button>,
  Back: ({to}) => <a href={to}>Kembali</a>, Loading: () => <p data-testid="loading-state">Memuat</p>,
  Empty: ({title, children}) => <div>{title}{children}</div>, Notice: ({children}) => <div>{children}</div>,
}));

const fixture = () => ({
  id: 'demo', student_alias: 'Peserta Demo', text_title: 'Bacaan Uji', created_at: '2026-11-27T00:00:00Z',
  profile: 'Latihan ketepatan kata', quality: 'layak', duration: 30, mode: 'both', transcript: 'bunga taman',
  recommendations: ['Dengarkan dan ulangi kata yang ditandai.'], limitations: ['Pengamatan sesi, bukan diagnosis.'],
  metrics: {accuracy: 60, wpm: 45, on_text_percent: 75, speech_reliable: true, gaze_usable: true,
    annotations: [{index: 0, type: 'substitute', word: 'bunga', spoken: 'bunda'}],
    multimodal: {multimodal_complete: true, pattern: 'Pola dari backend', concordance: 30, speech_error_words: 10,
      agreement_words: [{index: 0, word: 'bunga'}, {index: 1, word: 'taman'}, {index: 2, word: 'kelopak'}]},
    gaze: {longest_dwell: [{index: 0, word: 'bunga', ms: 500, visits: 2}]},
    fluency: {wpm: 60, pause_frequency_per_min: 0, mean_pause_duration_sec: null, qc_flags: []},
  },
});
let host, root;
const el = id => host.querySelector(`[data-testid="${id}"]`);
const click = async id => {await act(async () => el(id).click());};
const render = async data => {
  api.get.mockResolvedValue({data});
  await act(async () => root.render(<Results/>));
};
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks(); useAuth.mockReturnValue({user: {role: 'teacher'}});
  host = document.createElement('div'); document.body.appendChild(host); root = createRoot(host);
});
afterEach(async () => {await act(async () => root.unmount()); host.remove();});

test('uses backend findings, keeps three shared words and separate WPM definitions', async () => {
  await render(fixture());
  expect(el('fusion-pattern').textContent).toBe('Pola dari backend');
  expect(el('word-group-both').querySelectorAll('a')).toHaveLength(3);
  expect(el('metric-wpm').textContent).toContain('45');
  expect(el('fluency-wpm').textContent).toBe('60');
  expect(el('metric-wpm').parentElement.querySelector('.assessment-meter')).toBeNull();
  expect(el('adaptive-next-practice').getAttribute('href')).toBe('/pronunciation');
  expect(el('agreement-word-0').getAttribute('href')).toBe('/pronunciation?word=bunga');
});
test.each([[true, false], [false, true], [false, false]])('no fusion for audio=%s, gaze=%s, even with stale fusion data', async (audio, gaze) => {
  const data = fixture(); data.metrics.speech_reliable = audio; data.metrics.gaze_usable = gaze;
  await render(data);
  expect(el('fusion-panel')).toBeNull(); expect(el('fusion-unavailable')).not.toBeNull();
  expect(el('word-group-both').querySelectorAll('a')).toHaveLength(0);
});
test('legacy data without multimodal_complete cannot claim fusion', async () => {
  const data = fixture(); delete data.metrics.multimodal.multimodal_complete;
  await render(data); expect(el('fusion-panel')).toBeNull();
});
test('null mean pause is unavailable, while a measured zero stays zero', async () => {
  await render(fixture());
  expect(el('fluency-mean_pause_duration_sec').textContent).toBe('Belum tersedia');
  expect(el('fluency-pause_frequency_per_min').textContent).toBe('0');
});
test('missing legacy fields render every tab without undefined or NaN', async () => {
  await render({id: 'demo', metrics: {}});
  for (const tab of ['overview', 'speech', 'gaze', 'details']) {
    await click(`result-tab-${tab}`);
    expect(host.textContent).not.toMatch(/undefined|NaN/);
  }
});
test('loading, API error, and retry are usable', async () => {
  let reject;
  api.get.mockReturnValue(new Promise((resolve, fail) => {reject = fail;}));
  await act(async () => root.render(<Results/>)); expect(el('loading-state')).not.toBeNull();
  await act(async () => reject(new Error('Tidak dapat terhubung')));
  expect(el('results-error').textContent).toBe('Tidak dapat terhubung');
  api.get.mockResolvedValue({data: fixture()});
  await act(async () => Array.from(host.querySelectorAll('button')).find(b => b.textContent === 'Coba lagi').click());
  expect(el('result-heading')).not.toBeNull();
});
test('empty successful response shows an empty state', async () => {
  await render(null); expect(host.textContent).toContain('Hasil asesmen belum tersedia');
});
test('tab keyboard navigation moves focus and selected state', async () => {
  await render(fixture());
  el('result-tab-overview').focus();
  await act(async () => el('result-tab-overview').dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowRight', bubbles: true})));
  expect(el('result-tab-speech').getAttribute('aria-selected')).toBe('true');
  expect(document.activeElement).toBe(el('result-tab-speech'));
  await act(async () => el('result-tab-speech').dispatchEvent(new KeyboardEvent('keydown', {key: 'End', bubbles: true})));
  expect(el('result-tab-details').getAttribute('aria-selected')).toBe('true');
});
test('teacher review posts correction and renders returned metrics without replacing original fluency', async () => {
  const data = fixture(); await render(data); await click('result-tab-speech'); await click('edit-transcript');
  const reviewed = {...data, reviewed: true, transcript: 'bunga', metrics: {...data.metrics, accuracy: 100, wpm: 40}};
  api.patch.mockResolvedValue({data: reviewed});
  el('corrected-transcript').value = 'bunga'; el('review-note').value = 'Ditinjau';
  await act(async () => el('corrected-transcript').closest('form').dispatchEvent(new Event('submit', {bubbles: true, cancelable: true})));
  expect(api.patch).toHaveBeenCalledWith('/sessions/demo/review', {transcript: 'bunga', note: 'Ditinjau'});
  expect(el('metric-accuracy').textContent).toContain('100');
  expect(el('fluency-wpm').textContent).toBe('60');
  expect(el('corrected-transcript')).toBeNull();
});
test('student cannot see the transcript correction control', async () => {
  useAuth.mockReturnValue({user: {role: 'student'}}); await render(fixture()); await click('result-tab-speech');
  expect(el('edit-transcript')).toBeNull();
});
test('PDF keeps the existing endpoint and blob download contract', async () => {
  await render(fixture());
  URL.createObjectURL = jest.fn(() => 'blob:report'); URL.revokeObjectURL = jest.fn();
  const anchor = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  api.get.mockResolvedValue({data: new Blob(['PDF'])});
  await click('download-report');
  expect(api.get).toHaveBeenLastCalledWith('/sessions/demo/report', {responseType: 'blob'});
  expect(anchor).toHaveBeenCalled(); anchor.mockRestore();
});
test('gaze tab retains the replay component and word observation table', async () => {
  const data = fixture(); data.metrics.word_observations = [{display_index: 0, word: 'bunga', first_fixation_ms: 120}];
  await render(data); await click('result-tab-gaze');
  expect(el('replay-preserved')).not.toBeNull(); expect(host.querySelector('.data-table')).not.toBeNull();
});

test('additional backend recommendation opens the transcript tab', async () => {
  const data = fixture(); data.recommendations.push('Koreksi transkripsi bersama pendamping.');
  await render(data);
  const details = host.querySelector('.assessment-extra-advice'); details.open = true;
  await act(async () => details.querySelector('button').click());
  expect(el('result-tab-speech').getAttribute('aria-selected')).toBe('true');
});

test('null profile and non-finite measurements remain safe', async () => {
  const data = fixture(); data.profile = null; data.metrics.accuracy = NaN; data.metrics.wpm = Infinity;
  await render(data);
  expect(el('metric-accuracy').textContent).toContain('Belum tersedia');
  expect(el('metric-wpm').textContent).toContain('Belum tersedia');
});
