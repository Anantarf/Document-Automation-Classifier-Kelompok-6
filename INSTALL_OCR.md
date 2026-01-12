# Instalasi OCR untuk PDF Scan

## Masalah yang Muncul

Jika Anda melihat error berikut:

```
pdf2image.exceptions.PDFInfoNotInstalledError: Unable to get page count. Is poppler installed and in PATH?
```

Ini berarti **Poppler** (dependency eksternal) belum terinstall. Program tetap akan berjalan, tapi **OCR untuk PDF scan tidak akan berfungsi**.

---

## Solusi 1: Install Poppler (Recommended untuk OCR)

### Windows:

1. **Download Poppler untuk Windows:**

   - Kunjungi: https://github.com/oschwartz10612/poppler-windows/releases/
   - Download versi terbaru (misalnya: `Release-24.02.0-0.zip`)

2. **Extract dan Setup:**

   ```powershell
   # Extract ke folder (contoh: C:\poppler)
   # Folder struktur: C:\poppler\Library\bin\
   ```

3. **Tambahkan ke PATH:**

   - Buka **Environment Variables** (Windows + R → `sysdm.cpl` → Advanced → Environment Variables)
   - Edit **Path** di System Variables
   - Tambahkan: `C:\poppler\Library\bin`
   - Klik **OK** dan restart terminal/IDE

4. **Verifikasi:**

   ```powershell
   # Buka terminal baru
   pdftoppm -v
   # Seharusnya muncul versi Poppler
   ```

5. **Restart aplikasi:**
   ```powershell
   .\run.bat
   ```

---

## Solusi 2: Nonaktifkan OCR (Jika tidak butuh)

Jika Anda tidak memerlukan OCR untuk PDF scan, cukup **kosongkan** atau **hapus** variable `TESSERACT_CMD` di file `.env`:

```env
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_CMD=
```

Program akan tetap berjalan normal, hanya saja PDF scan tidak akan di-OCR.

---

## Catatan Penting:

- **PDF dengan teks biasa** (bukan scan) tetap bisa diekstrak tanpa Poppler
- **DOCX** tidak memerlukan Poppler
- OCR hanya diperlukan untuk **PDF hasil scan/gambar**
- Setelah perbaikan ini, program **tidak akan crash** meskipun Poppler tidak ada

---

## Troubleshooting

### Error tetap muncul setelah install Poppler:

1. Pastikan PATH sudah ditambahkan dengan benar
2. Restart terminal dan IDE sepenuhnya
3. Cek dengan `pdftoppm -v` di terminal baru

### Ingin skip OCR sepenuhnya:

Edit `.env`:

```env
TESSERACT_CMD=
```

### Log muncul "OCR failed" tapi aplikasi jalan:

Ini normal jika Poppler tidak terinstall. Aplikasi akan tetap berfungsi untuk PDF non-scan dan DOCX.
