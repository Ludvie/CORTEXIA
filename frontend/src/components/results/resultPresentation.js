// Presentation only: quality gates and findings come from the assessment API.
export const isNumber = value => typeof value === 'number' && Number.isFinite(value);
export const numberLabel = (value, digits = 1) => isNumber(value)
  ? value.toLocaleString('id-ID', {maximumFractionDigits: digits}) : '—';

export function resultState(metrics = {}) {
  const audio = metrics.speech_reliable === true;
  const gaze = metrics.gaze_usable === true;
  return {audio, gaze, combined: audio && gaze && metrics.multimodal?.multimodal_complete === true};
}

export function practiceFor(profile = '') {
  profile = typeof profile === 'string' ? profile : '';
  if (profile.includes('ketepatan')) return {to: '/pronunciation', title: 'Latihan ketepatan kata', goal: 'Membiasakan bunyi dan urutan kata.'};
  if (profile.includes('fokus')) return {to: '/reading?mode=gaze', title: 'Latihan mengikuti baris', goal: 'Membantu pandangan mengikuti alur bacaan.'};
  return {to: '/reading', title: 'Latihan membaca bersama', goal: 'Membangun ritme membaca yang nyaman.'};
}

export function profileExplanation(metrics = {}) {
  const {audio, gaze} = resultState(metrics), signals = metrics.multimodal?.signals || {};
  const observations = [];
  if (audio && signals.word_accuracy_low === true) observations.push('Transkripsi menunjukkan perbedaan antara kata yang terbaca dan teks bacaan.');
  if (audio && signals.fluency_low === true) observations.push('Kecepatan membaca berada di bawah acuan latihan awal.');
  if (gaze && signals.gaze_irregular === true) observations.push('Pola tatapan menandai alur membaca yang perlu ditinjau.');
  if (observations.length) return observations.slice(0, 2).join(' ');
  if (!audio && !gaze) return 'Data sesi belum memenuhi syarat untuk menentukan aspek membaca yang perlu dilatih.';
  return 'Ringkasan ini memakai pengamatan yang memenuhi syarat kualitas. Gunakan temuan sesi sebagai panduan latihan bersama pendamping.';
}

export const FLUENCY_FIELDS = [
  ['wpm', 'Kecepatan ujaran', 'kata/menit', 'Words per Minute (WPM)', 'Jumlah kata transkrip otomatis dibagi rentang dari ujaran pertama hingga terakhir, termasuk jeda di antaranya. Hening awal dan akhir tidak dihitung.'],
  ['articulation_rate_syllables_per_sec', 'Laju pengucapan', 'suku kata/detik', 'Articulation Rate', 'Perkiraan suku kata dibagi total durasi segmen suara yang terdeteksi VAD.'],
  ['mlr_syllables_per_run', 'Panjang rangkaian ujaran', 'suku kata/rangkaian', 'Mean Length of Run', 'Perkiraan suku kata dibagi jumlah rangkaian ujaran yang dipisahkan jeda minimal 250 ms.'],
  ['pause_frequency_per_min', 'Frekuensi jeda', 'jeda/menit', 'Pause Frequency', 'Jumlah jeda minimal 250 ms per menit rentang ujaran.'],
  ['mean_pause_duration_sec', 'Rata-rata durasi jeda', 'detik', 'Mean Pause Duration', 'Rata-rata panjang jeda minimal 250 ms. Tidak tersedia bila tidak ada jeda; bukan nol.'],
];
