# 📜 Catatan Riwayat Versi (Changelog) - Tantra Farmer Macro

Semua perubahan, penambahan fitur, dan perbaikan bug pada proyek **Tantra Farmer Macro** didokumentasikan di dalam file ini.
Format ini mengacu pada prinsip [Keep a Changelog](https://keepachangelog.com/id/1.0.0/).

---

## [v1.0.9] - 2026-11-19

### 🛠️ Fixed & Improved
- **Popup Guard Aktif di Setiap Putaran Auto Hunt Loop**:
  - Memperbaiki masalah di mana Auto Hunt Loop tidak mendeteksi popup penutup jika tidak ada item baru di tas yang siap dipindahkan ke gudang (`items_to_transfer` kosong).
  - Pengecekan `dismiss_storage_popup()` kini aktif di awal setiap siklus Auto Hunt dan dipindai secara responsif tiap ~1.5 detik di sela-sela interval tunggu, sehingga popup Notice / Quiz / Raffle langsung terdeteksi & ditutup seketika.
- **Pencarian Popup di Seluruh Layar (Full Screen Match)**:
  - Melepas batas crop pencarian `(650x600)` sehingga popup yang digeser ke posisi mana pun di jendela game Tantra (`1024x768`) tetap dapat terdeteksi dan ditutup secara presisi.

---

## [v1.0.8] - 2026-11-19

### 🛠️ Fixed
- **Pelepasan Global Hook ESC (Fix Makro Berhenti Sendiri saat Tutup Popup)**:
  - Memperbaiki bug di mana makro tiba-tiba berhenti (`Macro stopped by user`) saat bot mengirim tombol `Esc` untuk menutup popup Notice/Quiz.
  - Hook global `Esc` dilepaskan sepenuhnya sehingga `Esc` tidak lagi memicu abort makro. Tombol penghenti resmi makro tetap murni menggunakan **`[F12]`**.
  - Pengiriman tombol `Esc` oleh bot kini dikirim langsung melalui Win32 message (`PostMessageW WM_KEYDOWN VK_ESCAPE`) ke jendela game Tantra tanpa memicu event keyboard global.

---

## [v1.0.7] - 2026-11-19

### 🟢 Added
- **Filter Pop-Up Penutup Storage Mandiri (Issue #6)**:
  - Panel manajemen *"🛡️ Filter Pop-up Penutup Storage"* di Tab 4 untuk mendeteksi dan menutup popup modal (Notice, Lucky Number, Raffle, Quiz) secara cerdas.
  - Tombol *"✂️ Potong Judul Popup dari Layar..."* untuk memotong judul popup langsung dari layar game menggunakan visual selector interaktif.
  - Prosedur penutupan otomatis: makro memindai header popup yang terdaftar, mengklik tepat pada judul (bukan di tengah sehingga aman dari tombol berbayar Rupiah), lalu mengirimkan `Esc` 1x untuk menutup modal tanpa menutup jendela Storage.
- **Safety Stop saat Karakter Mati / Pop-Up Respawn (Issue #7)**:
  - Deteksi otomatis pop-up konfirmasi kematian karakter: `"If you click 'OK', you will respawn at the last saved location"`.
  - Jika terdeteksi saat Auto Hunt atau Auto Skill, makro seketika berhenti total (`Safety Stop`), mengubah status badge menjadi merah mencolok (`🚨 KARAKTER MATI`), memunculkan log peringatan, serta membunyikan alarm suara agar karakter tidak bergerak tanpa pengawasan.
- **Non-Overwriting Multi-Template Blacklist (Issue #1)**:
  - Saat menambahkan template blacklist (baik Gudang maupun Jual NPC) dengan nama yang sudah ada, sistem tidak lagi menimpa file lama. File otomatis diberi penomoran unik berurutan (`nama_2.png`, `nama_3.png`, dst.) sehingga varian template item bertambah dan tidak ada data sebelumnya yang hilang.
  - Jumlah total item terdaftar kini ditampilkan di judul frame Blacklist: *(X Item Terdaftar)* dan daftar item diurutkan secara alfabetis agar varian item yang sama berkumpul rapi.
- **Tombol Zero-In Window Game ke (0, 0) (Issue #2)**:
  - Tombol `📍 Zero-In (0, 0)` di Dashboard & Tab Kalibrasi Area untuk memposisikan window game Tantra tepat ke koordinat layar `(0, 0)` secara otomatis menggunakan Win32 `SetWindowPos`.
- **Tombol Snap Makro ke Samping Game (Issue #3)**:
  - Tombol `🧲 Snap Samping Game` di Dashboard & Tab Kalibrasi Area untuk menempelkan window makro persis di sisi kanan window game Tantra agar tidak saling menutupi.
- **Scrollable Frame pada Tab Pengaturan & Kalibrasi (Issue #4)**:
  - Tab Pengaturan & Delay dan Tab Kalibrasi Area kini menggunakan canvas scrollable dengan dukungan penuh *mouse wheel* dan scrollbar vertikal. Informasi aplikasi, konfigurasi delay, dan ganti password tidak lagi terpotong pada monitor resolusi kecil/laptop.
- **Adaptive Window Size**:
  - Ukuran window makro otomatis menyesuaikan dengan resolusi monitor pengguna.

### ⚡ Changed
- **Penyederhanaan Menu Blacklist (Issue #5)**:
  - Tombol manual *"Tambah Ikon Gambar..."* dihilangkan dari Tab Blacklist Gudang dan Tab Blacklist Jual NPC; seluruh proses penambahan blacklist difokuskan langsung menggunakan tombol *"✂️ Potong dari Slot Tas..."*.

---

## [v1.0.6] - 2026-11-17

### 🟢 Added
- **Sistem Auto-Updater Otomatis**: Aplikasi kini dapat mendeteksi versi terbaru langsung dari GitHub Releases secara senyap di latar belakang.
- **Pemberitahuan Update di UI**: Tombol notifikasi kuning `⚡ Update vX.X.X Tersedia!` di header aplikasi serta pop-up dialog konfirmasi update.
- **Modal Download dengan Progress Bar**: Menampilkan persentase unduhan (%) dan ukuran file (MB) secara real-time saat mendownload file `.exe` baru.
- **Transisi & Restart Mandiri**: Menggunakan skrip transisi `updater.bat` yang mengganti file `TantraFarmer.exe` lama dengan yang baru tanpa menghapus data kalibrasi `config.json` dan ikon blacklist yang sudah dipotong.
- **Tombol Cek Update Manual**: Disediakan tombol `🔄 Cek Pembaruan (Auto-Update)` pada Tab 7 (Pengaturan) agar user dapat memeriksa pembaruan kapan saja.

### ⚡ Changed
- Repositori diset ke **Public** sehingga auto-updater dapat mengunduh release aset tanpa memerlukan token autentikasi GitHub.
- Module `updater.py` ditambahkan ke `hidden_imports` pada `tantra_farmer.spec`.

---

## [v1.0.5] - 2026-11-17

### 🟢 Added
- **Informasi Versi Aplikasi Terpadu**:
  - Judul jendela aplikasi: `Tantra Farmer Macro v1.0.5`.
  - Badge hijau penanda versi di header samping judul utama.
  - Teks versi di bagian footer bawah aplikasi.
  - Kartu Informasi Aplikasi di Tab 7 (Pengaturan).
- **Shortcut Aksi Cepat Mandiri (Direct Action Hotkeys)**:
  - `[F9]`: Langsung menjalankan **Tarik Storage ke Tas** (`Storage -> Inventory`).
  - `[F10]`: Langsung menjalankan **Jual Tas ke NPC Merchant** (`Inventory -> NPC`).
  - Panel tombol aksi cepat di Dashboard: `📦 Tarik Storage -> Tas [F9]`, `💰 Jual Tas -> NPC [F10]`, dan `🛡️ Tutup Popup Storage [F8]`.
- **Fitur Pengaman Tutup Popup Storage (`F8`)**:
  - Mengatasi kendala jendela Storage tertutup pop-up modal (*Notice*, *Lucky Number*, *Raffle*, *Quiz*).
  - Prosedur aman: klik area teks/judul kiri atas objek (default `X=85, Y=55`) agar tidak memicu tombol berbayar Rupiah di tengah, lalu tekan `Esc` tepat 1x agar jendela Storage tidak ikut tertutup.
  - Opsi checkbox di Tab Storage: *"🛡️ Tutup Otomatis Popup sebelum proses Storage"*.

---

## [v1.0.4] - 2026-11-16

### 🛠️ Fixed
- **Active Window Guard pada Auto Hunt**: Memperbaiki bug di mana screenshot tas pada mode Auto Hunt menangkap tampilan latar belakang GUI aplikasi (bukan game) karena game belum berada di foreground saat loop dimulai.
- Ditambahkan fungsi `is_foreground()` di `window_manager.py` untuk memastikan game Tantra selalu aktif di baris depan sebelum melakukan screen capture.

---

## [v1.0.3] - 2026-11-16

### 🟢 Added
- **Log Real-Time Skor Matching Blacklist Gudang**:
  - Menampilkan skor kemiripan per slot di dashboard pada mode Auto Hunt:
    `[Auto Hunt] Slot #1 [B:1, K:1]: Match 'Amulet'=0.88 (Min:0.50) -> 🛑 BLACKLIST GUDANG`
  - Cache status per slot untuk mencegah banjir (*spam*) log setiap 1.5 detik jika kondisi tas tidak berubah.
- **Pengaturan Khusus Threshold Blacklist Gudang**: Opsi input mandiri di Tab 7: `Threshold Match Blacklist Gudang (0.5 - 1.0)`.

### ⚡ Changed
- **Peningkatan Algoritma Template Matcher (Scale C - Unresized Needle)**: Mengambil potongan tengah ikon asli (1:1 tanpa resizing) untuk mempertahankan ketajaman pixel art, meningkatkan skor kecocokan ikon dari ~0.35 menjadi $\ge 0.80$.

---

## [v1.0.2] - 2026-11-16

### 🟢 Added
- **Live Preview Alat Pemotong Ikon (Crop Tool)**: Menampilkan kotak seleksi dan preview gambar secara real-time saat mouse digeser, serta otomatis mengaktifkan jendela game agar tangkapan layar tidak berwarna abu-abu/blank.
- **Toleransi Kesetaraan Threshold**: Logika matching diperbarui agar jika skor $\ge$ threshold (contoh: `0.70 == 0.70`), item langsung dianggap Blacklist dan TIDAK dieksekusi/dijual.

### 🛠️ Fixed
- Memperbaiki `NameError: name 'container' is not defined` saat menekan tombol "Simpan Pengaturan" di Tab 7.

### ⚡ Changed
- Nilai default seluruh tombol pada `DEFAULT_SKILL_CONFIG` diatur ke `enabled: false` dengan interval `10.0` detik.

---

## [v1.0.1] - 2026-11-15

### 🛠️ Fixed
- **Startup Crash pada Executable Windows**: Memperbaiki error saat file `.exe` dijalankan akibat pemanggilan `simpledialog.askstring` sebelum root Tkinter siap.
- Mengganti dialog login popup dengan layar form login terintegrasi (*in-window login*) yang mulus dan stabil.

---

## [v1.0.0] - 2026-11-15

### 🟢 Added
- Rilis perdana executable standalone untuk Windows (`TantraFarmer.exe`).
- Proteksi keamanan password akses saat membuka aplikasi.
- Fitur Auto Move Inventory ke Storage (120 slot) dan Inventory ke NPC Merchant (Auto Sell).
- Fitur Auto Skill Macro (Slot 1–0, F1–F10, E/R/F) dengan countdown detik mundur real-time.
- Fitur sinkronisasi Auto Skill dengan Mode Auto Hunt.
- Alat kalibrasi koordinat area visual (Select Area) untuk Tas, Gudang, dan Toko Merchant.
- Pipeline GitHub Actions otomatis untuk kompilasi executable Windows (`Build and Release Windows Executable`).
