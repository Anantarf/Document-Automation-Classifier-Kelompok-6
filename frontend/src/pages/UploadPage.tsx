import React, { useCallback, useState } from 'react';
import { useUploadDocument } from '../hooks/useUploadDocument';
import { useDropzone } from 'react-dropzone';
import { useForm } from 'react-hook-form';
import {
  Upload,
  X,
  CheckCircle,
  AlertCircle,
  FileText,
  Loader2,
  ArrowRight,
  Save,
  Eye,
} from 'lucide-react';
import api from '../api/axios';
import { useNotification } from '../contexts/NotificationContext';

export default function UploadPage() {
  const { register, handleSubmit, reset, setValue } = useForm();
  const {
    mutate,
    isLoading: isUploading,
    isSuccess,
    isError,
    error,
    reset: resetMutation,
  } = useUploadDocument();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState('');

  const { addNotification } = useNotification();

  // Cleanup object URL on unmount or file change
  React.useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  React.useEffect(() => {
    if (isSuccess) {
      addNotification(`Dokumen berhasil diupload`);
    }
  }, [isSuccess]);

  // File size limit (must match backend: 50 MB)
  const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles?.[0]) {
        const selectedFile = acceptedFiles[0];

        // Validasi ukuran file sebelum lanjut
        if (selectedFile.size > MAX_FILE_SIZE) {
          setAnalyzeError(
            `File terlalu besar (${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB). Maksimal ${(MAX_FILE_SIZE / (1024 * 1024)).toFixed(0)} MB.`,
          );
          setFile(null);
          setPreviewUrl(null);
          return;
        }

        setFile(selectedFile);
        setAnalyzeError('');
        resetMutation();

        // Create visual preview
        if (selectedFile.type === 'application/pdf') {
          const url = URL.createObjectURL(selectedFile);
          setPreviewUrl(url);
        } else {
          setPreviewUrl(null); // No preview for DOCX yet
        }

        // Analyze file to pre-fill form
        setIsAnalyzing(true);
        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
          const res = await api.post('/upload/analyze', formData);
          const { parsed } = res.data;

          if (parsed) {
            if (parsed.nomor) setValue('nomor', parsed.nomor);
            if (parsed.sifat) setValue('sifat', parsed.sifat); // Visual only
            if (parsed.tahun) setValue('tahun', parsed.tahun);
            if (parsed.jenis) setValue('jenis', parsed.jenis || '');
            if (parsed.perihal) setValue('perihal', parsed.perihal);
            if (parsed.tanggal_surat) setValue('tanggal_surat', parsed.tanggal_surat);
            if (parsed.pengirim) setValue('pengirim', parsed.pengirim);
            if (parsed.penerima) setValue('penerima', parsed.penerima);
          }
        } catch (err) {
          console.error('Analysis failed', err);
          setAnalyzeError('Gagal menganalisis file otomatis. Silakan isi manual.');
        } finally {
          setIsAnalyzing(false);
        }
      }
    },
    [resetMutation, setValue],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles: 1,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
  });

  const onSubmit = (data: any) => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    if (data.tahun) formData.append('tahun', data.tahun);
    if (data.jenis) formData.append('jenis', data.jenis);
    if (data.nomor) formData.append('nomor', data.nomor);
    if (data.perihal) formData.append('perihal', data.perihal);
    if (data.tanggal_surat) formData.append('tanggal_surat', data.tanggal_surat);
    if (data.pengirim) formData.append('pengirim', data.pengirim);
    if (data.penerima) formData.append('penerima', data.penerima);

    mutate(formData);
  };

  const handleReset = () => {
    setFile(null);
    setPreviewUrl(null);
    reset();
    resetMutation();
  };

  // If successfully uploaded, show success screen
  if (isSuccess) {
    return (
      <div className="max-w-2xl mx-auto animate-fade-in py-12">
        <div className="bg-green-50 border border-green-100 rounded-2xl p-8 text-center shadow-sm">
          <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle size={32} />
          </div>
          <h3 className="text-xl font-bold text-green-800 mb-2">Upload Berhasil!</h3>
          <p className="text-green-700 mb-6">Dokumen telah tersimpan dan diklasifikasikan.</p>

          <div className="flex justify-center gap-3">
            <button
              onClick={handleReset}
              className="bg-green-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-green-700 transition shadow-sm"
            >
              Upload Lagi
            </button>
            <button
              onClick={() => (window.location.href = '/search')}
              className="bg-white text-green-700 border border-green-200 px-6 py-2 rounded-lg font-semibold hover:bg-green-50 transition shadow-sm"
            >
              Lihat Arsip
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto animate-fade-in h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Upload & Review</h1>
          <p className="text-slate-500 text-sm">Review dokumen sebelum disimpan ke arsip.</p>
        </div>
      </div>

      {!file ? (
        <div
          className="flex-none bg-white rounded-2xl border-2 border-dashed border-slate-300 hover:border-primary-500 hover:bg-slate-50/50 transition-all cursor-pointer p-8 flex flex-col items-center justify-center min-h-[300px]"
          {...getRootProps()}
        >
          <input {...getInputProps()} />
          <div className="text-center max-w-md">
            <div className="w-16 h-16 bg-primary-50 text-user-primary rounded-2xl flex items-center justify-center mx-auto mb-4 text-primary-600">
              <Upload size={32} />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 mb-1">Unggah Dokumen Surat</h3>
            <p className="text-slate-500 mb-2">Klik atau drag file PDF/DOCX kesini.</p>
            <p className="text-xs text-slate-400">Sistem akan otomatis membaca metadata surat.</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
          {/* Left: Preview */}
          <div className="bg-slate-800 rounded-xl overflow-hidden shadow-lg flex flex-col relative">
            <div className="bg-slate-900 px-4 py-3 flex items-center justify-between shadow-md z-10">
              <div className="flex items-center gap-3 text-white overflow-hidden">
                <FileText size={18} className="text-slate-400 shrink-0" />
                <span className="text-sm font-medium truncate">{file.name}</span>
              </div>
              <button
                onClick={handleReset}
                className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 bg-slate-200 relative">
              {previewUrl ? (
                <iframe
                  src={previewUrl}
                  className="w-full h-full border-none"
                  title="Document Preview"
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500">
                  <FileText size={48} className="mb-2 opacity-50" />
                  <p>Preview tidak tersedia untuk format ini.</p>
                  <p className="text-xs mt-1">(Hanya PDF yang mendukung preview langsung)</p>
                </div>
              )}

              {/* Analyzing Overlay */}
              {isAnalyzing && (
                <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center text-primary-600">
                  <Loader2 size={40} className="animate-spin mb-4" />
                  <p className="font-semibold animate-pulse">Sedang membaca dokumen...</p>
                  <p className="text-xs text-slate-500 mt-1">Ekstrak Nomor, Sifat, & Tanggal</p>
                </div>
              )}
            </div>
          </div>

          {/* Right: Form */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-card flex flex-col h-full overflow-hidden">
            <div className="p-6 border-b border-slate-100">
              <h3 className="font-bold text-lg text-slate-900 flex items-center gap-2">
                <span className="w-1.5 h-6 bg-primary-600 rounded-full inline-block"></span>
                Review Data
              </h3>
              <p className="text-slate-500 text-sm mt-1">
                Data diisi otomatis. Silakan koreksi jika perlu.
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              {analyzeError && (
                <div className="p-3 bg-amber-50 text-amber-700 text-xs rounded-lg flex gap-2">
                  <AlertCircle size={14} className="mt-0.5 shrink-0" />
                  {analyzeError}
                </div>
              )}

              <form id="upload-form" onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label-text">Sifat Surat</label>
                    {/* Display Sifat here, but save it as 'sifat' (UI only?) - wait, DB doesn't have sifat column. 
                                    User wants PREVIEW to show Sifat. 
                                    Let's allow user to edit Sifat here visually? 
                                    But we have no column for Sifat. 
                                    Let's assume this field is purely for User Verification of 'Urgency'.
                                    Actually, if we don't save Sifat, showing it is useless.
                                    Maybe user wants to put Sifat into Perihal? Or just view it.
                                    I will map this visible input to 'sifat_preview' (read only). 
                                */}
                    <input
                      {...register('sifat')}
                      className="input-field input-disabled"
                      placeholder="-"
                      readOnly
                    />
                  </div>
                  <div>
                    <label className="label-text">Tahun</label>
                    <input
                      {...register('tahun')}
                      className="input-field input-disabled"
                      placeholder="-"
                      readOnly
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label-text">Jenis Surat</label>
                    <select {...register('jenis')} className="input-field cursor-pointer bg-white">
                      <option value="masuk">Surat Masuk</option>
                      <option value="keluar">Surat Keluar</option>
                      <option value="lainnya">Dokumen Lainnya</option>
                    </select>
                  </div>
                  <div>
                    <label className="label-text">Tanggal Surat</label>
                    <input
                      {...register('tanggal_surat')}
                      className="input-field input-disabled"
                      placeholder="-"
                      readOnly
                    />
                  </div>
                </div>

                {/* Hidden inputs to ensure persistence of non-displayed data */}
                <input type="hidden" {...register('perihal')} />
                <input type="hidden" {...register('pengirim')} />
                <input type="hidden" {...register('penerima')} />
                {/* Restore Nomor as hidden so folder slug is generated correctly */}
                <input type="hidden" {...register('nomor')} />
              </form>
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3 shrink-0">
              <button
                onClick={handleReset}
                className="px-5 py-2.5 rounded-lg border border-slate-300 text-slate-600 font-medium hover:bg-white hover:border-slate-400 transition-colors text-sm"
              >
                Batal
              </button>
              <button
                type="submit"
                form="upload-form"
                disabled={isUploading}
                className="px-6 py-2.5 rounded-lg bg-primary-600 text-white font-bold hover:bg-primary-700 transition-all shadow-lg shadow-primary-500/30 flex items-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isUploading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Menyimpan...
                  </>
                ) : (
                  <>
                    <Save size={16} />
                    {isAnalyzing ? 'Simpan (Menganalisis...)' : 'Simpan Arsip'}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
