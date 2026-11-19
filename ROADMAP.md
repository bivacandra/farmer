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

### 🎯 Versi Berikutnya (v1.0.7 - Planned)
- [ ] **Tombol Cepat Buka Issue/Feedback di GUI**:
  - Tombol langsung di Tab 7 (Pengaturan) yang membuka halaman GitHub Issues di browser default pengguna.
- [ ] **Auto Potion / HP & MP Guard (Opsional)**:
  - Pemindaian bar HP/MP karakter secara periodik.
  - Otomatis menekan hotkey potion (misal `1` atau `2`) jika HP turun di bawah persentase tertentu.
- [ ] **Notifikasi Audio / Bell Suara**:
  - Membunyikan nada "beep" atau notifikasi Windows saat:
    - Gudang Storage (120 slot) penuh.
    - Karakter terputus (*disconnected*) dari server game.

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
