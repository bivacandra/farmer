# 📜 Catatan Riwayat Versi (Changelog) - Tantra Farmer Macro

Semua perubahan, penambahan fitur, dan perbaikan bug pada proyek **Tantra Farmer Macro** didokumentasikan di dalam file ini.
Format ini mengacu pada prinsip [Keep a Changelog](https://keepachangelog.com/id/1.0.0/).

---

## [v1.2.3] - 2026-11-26

### 🛠️ Fixed & Improved
- **Pembedaan Warna & Palet pada Template Matcher (Color Fidelity & Histogram Weighting)**:
  - Menyelesaikan masalah false-positive di mana item yang memiliki siluet/bentuk 3D identik namun berbeda warna/tier (seperti Medali Perunggu vs Medali Emas, Pustika vs Ziva Pustika, Potion merah vs biru) terdeteksi sama saat salah satu di-blacklist.
  - Menambahkan pembobotan `calc_color_fidelity` yang memeriksa perbedaan per-kanal RGB (fokus area 75% grafik item) dan irisan histogram warna 32-bin.
  - Menyelaraskan pemotongan batas slot (`inner_slot` dan `inner_icon`) secara simetris untuk menjaga ketajaman detail ikon dan akurasi pergeseran posisi (jitter/shift 1-2px).

---

## [v1.2.2] - 2026-11-26

### 🛠️ Fixed
- **Perbaikan Error Pemanggilan OCR pada Blacklist Tarik Gudang**:
  - Memperbaiki `AttributeError: 'OCREngine' object has no attribute 'get_item_name_from_tooltip'` saat memeriksa slot Storage ke Inventory.
  - Penarikan dari gudang kini sepenuhnya menggunakan pencocokan visual template ikon (`match_item_in_whitelist`) yang cepat, presisi, dan konsisten dengan sistem Blacklist Simpan & Jual.

---

## [v1.2.1] - 2026-11-26

### 🟢 Added & Improved
- **Fitur Blacklist Penarikan Gudang (Storage $\to$ Inventory) (Resolve #15)**:
  - Menambahkan tab antarmuka baru: **`🚫 Blacklist Tarik Gudang`** untuk mencegah item-item berharga atau cadangan di gudang (seperti Ore, Potion cadangan, Equip simpanan) ikut terambil ke tas dan tidak sengaja terjual.
  - Mendukung pemotongan ikon langsung dari **Slot Gudang (Storage 120 slot)** maupun **Slot Tas (Inventory 24 slot)**, penambahan gambar file manual, serta fallback pencocokan nama via OCR tooltip.
  - Pengaturan threshold match tersendiri di tab Pengaturan (`storage_withdraw_blacklist_match_threshold`).

### 🛠️ Fixed
- **Optimasi Stabilitas Auto Loop Kamera di PC Low-Spec / Mini-PC (Resolve #14)**:
  - Menghadirkan opsi **Mode PC Low-Spec** (dioptimasi khusus untuk Core i3 / RAM 4GB seperti Mini-PC Wearnes MP-8101).
  - Mengatasi masalah kamera berputar-putar tanpa henti dengan:
    1. Memperpanjang jeda pasca *zoom-out* agar animasi kamera mundur terproses penuh sebelum pencarian NPC dimulai.
    2. Memberikan jeda stabilisasi rotasi (*settle delay*) setelah tombol putar dilepas agar GPU terintegrasi sempat merender frame yang tajam tanpa efek kabur (*motion blur / frame drop*).
    3. Impuls putaran lebih halus (durasi tekan tombol lebih pendek) untuk mencegah sudut NPC Ashuri terlewati.
    4. Menambahkan *Recovery Sweep Pass* otomatis jika pada putaran pertama NPC belum terdeteksi.

---

## [v1.2.0] - 2026-11-25

### 🟢 Added & Improved
- **Mode Otomasi Penuh: Siklus Tarik Gudang & Jual ke NPC Merchant (Issue / Task 5)**:
  - Mengotomasi seluruh siklus secara terus-menerus (*end-to-end loop*):
    1. Buka gudang via NPC *Tradesman Abahan* -> Ambil barang sampai tas penuh.
    2. Tutup jendela gudang (`Esc`).
    3. Bergerak lurus ke pedagang (*Jeweler Ashuri*) menggunakan tombol keyboard (`W`) tanpa perlu klik tanah, menghindari hambatan peti toko (*vending stall*).
    4. Buka dialog toko *Jeweler Ashuri* -> Jual semua barang di inventaris.
    5. Tutup dialog toko (`Esc`).
    6. Bergerak mundur kembali ke gudang (*Tradesman Abahan*) menggunakan tombol keyboard (`S`) secara presisi tanpa memutar kamera.
    7. Ulangi siklus secara otomatis hingga gudang kosong atau pengguna menekan hotkey stop (`F12`).
- **Penyelarasan Kamera Otomatis (*Auto Camera Alignment & Zoom-Out*)**:
  - Kamera otomatis melakukan *full zoom-out* (gulir ke bawah) saat makro dimulai.
  - Memutar sudut pandang (panah kiri) hingga garis lurus antara *Tradesman Abahan* dan *Jeweler Ashuri* sejajar dan terkunci secara otomatis.
- **Deteksi Presisi & Cepat Berbasis Binary IoU Matching**:
  - Membedakan nama NPC target dengan akurasi tinggi menggunakan perbandingan bentuk font pixel (IoU ~0.95+), mencegah salah klik pada NPC lain di sekitar seperti *Craftsman Kirika* (skor IoU < 0.20 langsung ditolak).
  - Akselerasi C pada pemindaian warna kuning teks via `ImageChops`, mempercepat deteksi dari 1.200 ms menjadi ~140 ms per frame.
  - Penyesuaian titik klik model karakter NPC tepat di tengah horizontal bawah namanya.
- **Dukungan UI & Shortcut Baru**:
  - Menambahkan radio button Mode *🔄 Siklus Penuh: Tarik Gudang & Jual ke NPC*.
  - Menambahkan tombol aksi cepat *🔄 Auto Loop [F7]* di GUI beserta shortcut keyboard global *F7*.
  - Tab Pengaturan baru untuk durasi jalan (`walk_to_merchant_sec`, `walk_to_storage_sec`) dan opsi penyesuaian navigasi.

---

## [v1.1.2] - 2026-11-24

### 🟢 Added & Improved
- **UI Slider Kecepatan Mouse & Peningkatan Kecepatan Hingga 10x (Issue #13)**:
  - Mengganti pengisian angka desimal manual yang membingungkan dengan komponen Slider Geser Horizontal (`tk.Scale`) 10 level kecepatan: dari *Level 1 (Pelan & Stabil)* hingga *Level 10 (Maksimal 10x Cepat)*.
  - Menjadikan transisi jeda kursor (*settle delay*, durasi *drag*, dan jeda *post-action*) adaptif proporsional terhadap slider, mempercepat pemindahan item hingga ~`0.05` detik per item pada kecepatan maksimal.
- **Installer Windows Resmi (`TantraFarmer-Setup.exe`)**:
  - Menghadirkan installer otomatis via Inno Setup lengkap dengan pembuatan icon shortcut di Desktop dan Start Menu.
  - Menjamin path instalasi tetap permanen di PC pengguna, sehingga setiap pembaruan versi via auto-update selalu tepat sasaran.
- **Deteksi Folder Sementara (Unextracted ZIP Guard)**:
  - Menambahkan dialog peringatan jika pengguna menjalankan makro langsung dari dalam preview ZIP atau folder sementara Windows (`Temp`), mengingatkan pengguna untuk mengekstrak folder terlebih dahulu agar pengaturan dan pembaruan versi tersimpan permanen.

### 🛠️ Fixed
- **Penyegaran Shortcut Keyboard Otomatis (*Auto Re-hook*) (Issue #12)**:
  - Memperbaiki masalah shortcut keyboard (seperti `F9`, `F10`) yang macet / tidak merespon setelah Auto Hunt Loop dihentikan.
  - Aplikasi secara otomatis mendaftarkan ulang seluruh low-level keyboard hook (`WH_KEYBOARD_LL`) di setiap kali makro selesai atau dihentikan.
  - Perbaikan closure thread callback pada shortcut untuk menghindari hambatan eksekusi tugas di antarmuka Tkinter.
- **Keandalan Skrip Auto-Updater**:
  - Skrip batch updater kini menggunakan *Absolute Path* lengkap dari executable yang sedang aktif dan perintah jeda non-interaktif aman (`ping 127.0.0.1`) agar penggantian file executable tidak gagal saat dijalankan di latar belakang (*detached process*).

---

## [v1.1.1] - 2026-11-22

### 🛠️ Fixed & Improved
- **Jeda dan Verifikasi Slot Kosong saat Penjualan ke NPC Merchant (Issue #11)**:
  - Memperbaiki bug visual dan desync item hilang di kursor akibat proses penjualan yang terlalu cepat.
  - Setelah menekan `Enter` untuk konfirmasi penjualan, bot kini secara aktif memverifikasi citra slot inventaris (`is_slot_empty`) hingga item benar-benar terkonfirmasi lenyap dari tas sebelum berpindah ke slot berikutnya.
  - Menambahkan safety timeout (`sell_wait_timeout_sec`, default 2.0s) agar bot tidak macet jika koneksi server game lag.
  - Menambahkan jeda stabilisasi kursor pasca jual (`sell_post_delay_sec`, default 0.35s) yang dapat dikustomisasi di Tab Pengaturan.

---

## [v1.1.0] - 2026-11-22

### 🟢 Added & Improved
- **Mode Compact untuk Layar 1366x768 & Game 800x600 (Issue #8)**:
  - Tombol toggle satu-klik *"🗕 Mode Compact"* / *"🗖 Mode Normal"* pada header aplikasi.
  - Pada Mode Compact, lebar jendela disesuaikan menjadi ~`520px` dan otomatis menempel di samping kanan jendela game (*Snap-to-Game*), mencegah tumpang tindih (*overlap*) pada layar resolusi `1366x768`.
  - Batas minimum ukuran jendela (`minsize`) diperkecil menjadi `(460, 480)` sehingga pengguna bebas mengatur ukuran jendela makro.
  - Tata letak Dashboard dibuat responsif dengan pemisahan baris tombol aksi dan bantuan penempatan jendela.
  - Preferensi mode compact disimpan otomatis di [config.json](file:///home/simple/Personals/tantra/farmer/config.json) (`ui.compact_mode`).
- **Kustomisasi Shortcut Keyboard Semua Fitur (Issue #9)**:
  - Panel konfigurasi baru *"⌨️ Pengaturan Shortcut / Global Hotkeys"* di Tab Pengaturan (Settings).
  - Pengguna dapat mengganti shortcut untuk seluruh aksi: *Mulai Makro* (default `F11`), *Hentikan Makro* (default `F12`), *Storage ke Tas* (`F9`), *Tas ke NPC Merchant* (`F10`), dan *Tutup Popup* (`F8`).
  - Sangat berguna bagi pengguna Remote Desktop (AnyDesk, TeamViewer, RDP) yang tombol `F11`/`F12`-nya sering tertahan atau bentrok.
  - Saat disimpan, hotkey langsung terdaftar ulang secara *live* tanpa perlu restart aplikasi.
  - Seluruh label tombol dan badge status di antarmuka otomatis dinamis menampilkan tombol shortcut yang aktif.

### 🛠️ Fixed
- **Safety Stop Karakter Mati (Respawn Dialog Detection) (Issue #10)**:
  - Melepas pembatasan `is_foreground()` pada pemeriksaan pasif kematian, sehingga deteksi kematian tetap aktif memindai game meskipun pengguna sedang fokus pada jendela lain atau mengontrol lewat Remote Desktop.
  - Memindai seluruh area klien game (*Full Client Match*) tanpa pemotongan statis sehingga kompatibel penuh dengan resolusi game `800x600` maupun `1024x768` di mana pun dialog respawn berada.
  - Menghentikan proses Auto Skill seketika saat deteksi kematian terpicu.
  - Memperbaiki bug status badge di mana badge peringatan merah `🚨 KARAKTER MATI` sebelumnya tertimpa kembali menjadi status `IDLE` oleh blok `finally`.

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
