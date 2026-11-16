# Product Requirements Document (PRD): FARMER - Makro Manajemen Inventaris & Penjualan NPC Game Tantra

## 1. Ringkasan Proyek (Overview)

Pembuatan aplikasi makro otomatisasi berbasis deteksi visual (gambar dan teks) untuk game Tantra. Aplikasi ini bertujuan untuk mengotomatiskan pengelolaan inventaris pemain, termasuk memindahkan barang antara Inventaris dan Gudang (Storage), serta menjual barang jarahan (drop monster) ke NPC Merchant.

## 2. Ruang Lingkup (Scope of Work)

Makro harus mampu melakukan tiga tugas utama:

1. **Inventory ke Storage:** Memindahkan item dari tas pemain ke dalam gudang.
2. **Storage ke Inventory:** Menarik item dari gudang ke tas pemain.
3. **Inventory ke NPC:** Menjual item dari tas pemain ke NPC Merchant.

## 3. Persyaratan Fungsional (Functional Requirements)

* **FR-1: Mekanisme Pemindahan Barang (Drag-and-Drop)**
* Sistem menyimulasikan penahanan tombol kiri mouse (*mouse down*), pergerakan kursor (*mouse move*), dan pelepasan tombol (*mouse up*) di slot tujuan.


* **FR-2: Deteksi Status Slot (Berisi vs Kosong)**
* Makro memindai matriks kotak pada jendela *Storage* dan *Inventory*.
* Makro membedakan kotak berisi piksel gambar item dan kotak kosong, sehingga item hanya dipindahkan ke kotak kosong.


* **FR-3: Pembacaan Kuantitas Item (OCR / Tooltip Reading)**
* Makro mengarahkan kursor (*hover*) ke item untuk memunculkan kotak informasi (*tooltip*).
* Makro membaca teks di *tooltip* (contoh: "Quantity 17") menggunakan *Optical Character Recognition* (OCR).


* **FR-4: Filter Pemindahan Gudang (Syarat Kuantitas)**
* Untuk tugas "Inventory ke Storage", sistem hanya menarik item jarahan jika jumlahnya tepat **100** (Quantity == 100).


* **FR-5: Whitelist & Blacklist Penjualan (Sistem Penandaan)**
* Sistem menggunakan daftar potongan gambar item (ikon item) terdaftar untuk menentukan apakah item aman dijual atau harus dilewati.


* **FR-6: Alur Penjualan Item ke NPC Merchant**
* Berdasarkan daftar jual (whitelist), makro melakukan *drag-and-drop* item dari jendela *Inventory* ke area tengah jendela *Merchant*.


* Sistem harus mendeteksi munculnya kotak dialog konfirmasi ("Message") yang menampilkan teks seperti "Will you sell [Nama Item]?" beserta tombol "OK" dan "Cancel".


* Setelah *pop-up* terdeteksi, makro menyimulasikan penekanan tombol `Enter` pada keyboard untuk mengonfirmasi penjualan.


* Makro memverifikasi *pop-up* tertutup, lalu melanjutkan perulangan ke slot item berikutnya di inventaris.



## 4. Persyaratan Non-Fungsional (Non-Functional Requirements)

* **NFR-1: Pengaturan Kecepatan Eksekusi (Speed Control)**
* Aplikasi menyediakan UI atau file konfigurasi untuk mengatur jeda waktu (*delay/sleep*) seperti jeda antar klik, durasi *drag*, jeda *hover* untuk *tooltip*, dan jeda tunggu munculnya *pop-up* konfirmasi penjualan.


* **NFR-2: Keamanan dan Kompatibilitas**
* Sistem mendeteksi layar pasif tanpa menginjeksi RAM klien game.
* Mendukung resolusi layar standar dan mengkalibrasi posisi jendela *Inventory*, *Storage*, *Merchant*, dan lokasi *pop-up* konfirmasi berdasarkan tangkapan layar.





## 5. Saran Implementasi Teknis (Untuk Agen AI/Programmer)

* **Bahasa Pemrograman:** Python.
* **Pustaka Penangkapan Layar:** `mss` atau `cv2` (OpenCV).
* **Deteksi Teks (OCR):** `Tesseract-OCR` (pytesseract) atau `EasyOCR` untuk membaca *tooltip* dan mendeteksi teks "Will you sell" pada kotak konfirmasi.


* **Kontrol Mouse & Keyboard:** `pyautogui` untuk logika *drag-and-drop* dan pengiriman perintah tombol `Enter`. Gunakan modul tingkat perangkat keras (seperti Arduino) jika game memblokir input virtual.


* **Logika Jeda Penjualan:** Tambahkan fungsi `wait_for_image` atau `wait_for_text` setelah melakukan *drop* item ke jendela merchant. Skrip harus menunggu hingga UI *pop-up* konfirmasi terdeteksi sebelum menekan `Enter`, untuk mencegah tombol `Enter` tertekan sebelum UI siap.