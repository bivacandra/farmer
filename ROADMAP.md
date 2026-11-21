# 🗺️ Roadmap & Backlog Pengembangan - Tantra Farmer Macro

Dokumen ini berisi rencana pengembangan, ide fitur baru (*wishlist*), dan kanal feedback untuk rilis **Tantra Farmer Macro** mendatang.

---

## 📌 Alur Penyampaian Feedback & Bug Report

Bagi pengguna atau tester yang menemukan kendala (*bug*) atau memiliki usulan fitur baru (*feature request*):
1. **GitHub Issues (Direkomendasikan)**: 
   👉 [Buat Issue Baru di GitHub](https://github.com/bivacandra/farmer/issues/new)
   - Gunakan label `bug` jika melaporkan kesalahan sistem / error.
   - Gunakan label `enhancement` jika mengusulkan fitur atau peningkatan baru.
2. **Sertakan Bukti Pendukung**:
   - Cuplikan baris teks dari file `farmer.log` atau `crash.log`.
   - Screenshot tampilan game Tantra saat error terjadi.

---

## 🚀 Rencana Rilis Mendatang

### 🎯 Versi Terbaru (v1.1.0 - Released)
- [x] **Mode Compact untuk Layar Resolusi 1366x768 & Game 800x600 (Issue #8)**:
  - Toggle satu-klik Mode Compact (~520px) dengan auto-snap ke samping game dan layout responsif tanpa tumpang tindih.
- [x] **Kustomisasi Shortcut Keyboard Semua Fitur (Issue #9)**:
  - Panel konfigurasi hotkey di Tab Pengaturan untuk mengganti tombol Start, Stop, dan task lainnya (cocok untuk pengguna Remote Desktop).
- [x] **Safety Stop Karakter Mati Tidak Berhenti (Issue #10)**:
  - Deteksi respawn dialog kematian tanpa hambatan foreground focus dan kompatibel penuh dengan resolusi 800x600 maupun 1024x768.

### 🎯 Versi Sebelumnya (v1.0.7 - v1.0.9)
- [x] **Tombol Zero-In Game Window (0, 0) (Issue #2)**:
  - Tombol pada Dashboard dan Kalibrasi Area untuk memposisikan window game Tantra tepat ke sudut kiri atas (0, 0).
- [x] **Tombol Snap Makro ke Samping Window Game (Issue #3)**:
  - Tombol untuk menempelkan window makro persis di samping kanan window game sehingga game dan makro berdampingan rapi tanpa tumpang tindih.
- [x] **Scrollable Frame & Tampilan Pengaturan Responsif (Issue #4)**:
  - Tab Pengaturan & Delay serta Kalibrasi Area kini dilengkapi vertical scrollbar dan dukungan mouse wheel, mencegah konten terpotong pada layar resolusi standar/laptop.
- [x] **Penyederhanaan UI Blacklist (Issue #5)**:
  - Menghilangkan tombol import file gambar manual pada Blacklist Gudang dan Blacklist NPC; acuan murni menggunakan tombol potong langsung dari slot tas ("Potong dari Slot Tas").
- [x] **Multi-Template / Non-Overwriting Blacklist (Issue #1)**:
  - Jangan menimpa file blacklist yang sudah ada saat menambahkan template dengan nama yang sama. Sistem otomatis menerapkan auto-increment suffix (`_2`, `_3`, dst.) sehingga template varian bertambah tanpa menghilangkan data sebelumnya.
- [x] **Filter Nama Pop-up Storage (Issue #6)**:
  - Daftar popup modal penghalang storage (Notice, Lucky Number, Raffle, Quiz) dengan auto-close aman (klik judul popup -> tekan Esc 1x) dan alat pemotong judul popup visual dari layar game.
- [x] **Safety Stop saat Karakter Mati (Respawn Pop-up) (Issue #7)**:
  - Menghentikan makro secara otomatis jika muncul popup "If you click 'OK', you will respawn at the last saved location" dengan visual alert merah dan bunyi peringatan.

---

## 💡 Wishlist & Ide Pengembangan Jangka Panjang (Backlog)

### 🎒 Manajemen Tas & Gudang
- [ ] **Filter Jumlah Penumpukan (Quantity Threshold)**:
  - Opsi memindahkan item ke gudang hanya jika stack sudah mencapai jumlah tertentu (misal 100 pcs).
- [ ] **Pemberian Nama/Tag pada Ikon Blacklist**:
  - Memungkinkan user mengedit nama item langsung dari UI daftar ikon tanpa mengubah nama file manual.
- [ ] **Multi-Tab Cargo / Storage**:
  - Dukungan untuk berpindah tab cargo di game jika server Tantra mendukung beberapa tab storage.

### ⚡ Auto Skill & Hunting
- [ ] **Prioritas Urutan Skill (Skill Combo Sequencing)**:
  - Menentukan urutan eksekusi skill tertentu (misal: Buff F1 -> Buff F2 -> Attack 1 -> Attack 2).
- [ ] **Jeda Smart Attack (Non-Spam saat Mengambil Drop)**:
  - Menunda spam skill selama beberapa milidetik saat bot sedang memindahkan drop tas ke gudang.

### 🛡️ Keamanan & Stabilitas
- [ ] **Randomized Delay (Anti-Pattern Jitter)**:
  - Menambahkan variasi acak ($\pm 10\text{--}30\text{ ms}$) pada klik mouse dan penekanan tombol agar gerakannya lebih alami.
- [ ] **Mode Ringan untuk Laptop Spek Rendah**:
  - Opsi menonaktifkan rendering visual live-preview atau memperlambat FPS polling internal untuk menghemat CPU/RAM di laptop jadul.

---

## 🏷️ Status Prioritas Fitur

| Prioritas | Fitur | Target Versi | Status |
| :--- | :--- | :---: | :---: |
| 🔴 Tinggi | Shortcut langsung ke GitHub Issues di GUI | v1.0.7 | Siap Diterapkan |
| 🟡 Sedang | Notifikasi Audio saat Storage Penuh | v1.0.7 | Backlog |
| 🟡 Sedang | Auto Potion HP/MP Monitor | v1.1.0 | Riset |
| 🟢 Rendah | Randomized Delay Jitter | v1.1.0 | Rencana |
