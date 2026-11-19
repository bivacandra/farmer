# 📜 Catatan Riwayat Versi (Changelog) - Tantra Farmer Macro

Semua perubahan, penambahan fitur, dan perbaikan bug pada proyek **Tantra Farmer Macro** didokumentasikan di dalam file ini.
Format ini mengacu pada prinsip [Keep a Changelog](https://keepachangelog.com/id/1.0.0/).

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
