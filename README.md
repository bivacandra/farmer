# Tantra Farmer Macro - Manajemen Inventaris & Penjualan NPC

Aplikasi makro otomatisasi berbasis deteksi visual (gambar dan teks OCR) untuk game **Tantra Online** (Kathana - The Reign of Shadow).

Makro ini mengotomatiskan pengelolaan inventaris pemain:
1. **Inventory ke Storage (Gudang):** Memindahkan item jarahan dari tas pemain ke dalam gudang hanya jika jumlahnya tepat **100** (Quantity == 100).
2. **Storage ke Inventory:** Menarik item dari gudang ke tas pemain hingga tas penuh.
3. **Inventory ke NPC Merchant:** Menjual item jarahan (drop monster) yang terdaftar di **Whitelist** ke toko NPC Merchant dengan deteksi otomatis kotak dialog konfirmasi ("Will you sell [Item]?") dan konfirmasi tombol `Enter`.

---

## 🎯 Fitur & Pemenuhan Kebutuhan (PRD)

* **FR-1: Drag-and-Drop Halus:** Menyimulasikan `mouse down` di slot asal, pergerakan mouse interpolasi, dan `mouse up` di slot target.
* **FR-2: Deteksi Status Slot (Berisi vs Kosong):** Memindai matriks kotak slot inventaris (6x5) dan storage (10x10) untuk memastikan item hanya dipindahkan ke kotak yang benar-benar kosong.
* **FR-3: Pembacaan Kuantitas Tooltip (OCR):** Mengarahkan kursor (*hover*) untuk memunculkan tooltip dan membaca teks `Quantity XX` menggunakan regex & OCR (Tesseract / EasyOCR).
* **FR-4: Filter Kuantitas Gudang:** Hanya memindahkan item ke gudang jika jumlahnya pas 100 (dapat disesuaikan di konfigurasi).
* **FR-5: Whitelist Penjualan Item:** Menggunakan sistem pencocokan potongan gambar ikon item di folder `assets/whitelist/` dengan fallback OCR nama item.
* **FR-6: Alur Jual Otomatis ke NPC:** Drag item whitelist ke tengah jendela Merchant -> deteksi visual pop-up "Will you sell" & tombol OK -> tekan `Enter` otomatis -> verifikasi pop-up tertutup.
* **NFR-1: Speed Control:** Semua jeda (*hover delay*, durasi *drag*, *popup timeout*, dll.) dapat dikonfigurasi melalui GUI atau file `config.json`.
* **NFR-2: Kompatibilitas DirectX / DirectInput:** Mendukung `pydirectinput` dan `pyautogui` agar klik mouse dan tombol keyboard terbaca oleh client game DirectX tanpa injeksi RAM.

---

## 🚀 Panduan Menjalankan di Windows

### Persyaratan Sistem
1. **Python 3.10+** (pastikan opsi *"Add Python to PATH"* dicentang saat install).
2. Game Tantra dijalankan dalam mode **Windowed** dengan resolusi standar **1024x768** (judul jendela: `"Kathana - The Reign of Shadow"`).
3. (Opsional untuk OCR Akurat): Install **Tesseract-OCR** di Windows.

### Cara Menjalankan
Cukup buka folder ini di Windows Explorer dan **dobel-klik file:**
```bat
run_macro.bat
```
Atau melalui terminal Windows (PowerShell / CMD):
```bash
pip install -r requirements.txt
python gui.py
```

---

## ⌨️ Kontrol Hotkey Global
 
* **`F11`**: Memulai Makro (Start)
* **`F12`**: Menghentikan Makro (Stop)
* **`Esc`**: Pembatalan Darurat (*Emergency Abort*)

*Hotkey ini aktif secara global di Windows meskipun jendela game Tantra sedang difokuskan.*

---

## 🖼️ Pengelolaan Whitelist Item Jual (FR-5)

Agar makro mengetahui item apa saja yang boleh dijual ke NPC:
1. Buka tab **"Whitelist Jual (FR-5)"** di aplikasi GUI.
2. Anda dapat:
   * Menekan tombol **"✂️ Potong Icon dari Slot Tas"**: Cukup masukkan nomor kolom (1-6) dan baris (1-5) dari tas Anda, makro akan langsung memotong ikon item tersebut dan menyimpannya.
   * Atau klik **"➕ Tambah Gambar Icon..."** untuk memilih file potongan gambar `.png` yang Anda miliki.
   * Atau letakkan gambar ikon item secara langsung ke folder `assets/whitelist/`.

---

## ⚙️ Penyesuaian Pengaturan (`config.json`)

Anda dapat mengubah pengaturan langsung dari tab **"Pengaturan & Delay"** di GUI atau melalui file `config.json`:

```json
{
  "delays": {
    "hover_delay_sec": 0.35,
    "drag_duration_sec": 0.25,
    "click_delay_sec": 0.1,
    "popup_wait_timeout_sec": 2.0,
    "post_action_delay_sec": 0.25
  },
  "rules": {
    "storage_deposit_quantity": 100,
    "sell_whitelist_match_threshold": 0.78,
    "auto_confirm_sell": true,
    "use_ocr_name_fallback": true
  }
}
```

---

## 🧪 Pengujian Offline / Diagnostik

Untuk memverifikasi modul deteksi pop-up, template matching, dan parsing OCR tanpa membuka game:
```bash
python test_macro.py
```
Hasil uji offline akan memvalidasi template tombol OK pop-up, pencocokan ikon whitelist, serta parser kuantitas tooltip.
