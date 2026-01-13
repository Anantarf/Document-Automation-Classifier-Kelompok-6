import React, { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUploadDocument } from '../hooks/useUploadDocument';
import { useDropzone } from 'react-dropzone';
import { useForm, FormProvider } from 'react-hook-form';
import { Upload, X, CheckCircle, AlertCircle, FileText, Loader2, Save } from 'lucide-react';
import api from '../api/axios';
import { useNotification } from '../contexts/NotificationContext';
import { MAX_FILE_SIZE } from '../config/constants';
import { MetadataField } from '../components/MetadataField';
import { useObjectUrl } from '../hooks/useObjectUrl';

export default function UploadPage() {
  const navigate = useNavigate();
  const methods = useForm();
  const { register, handleSubmit, reset, setValue } = methods;
  const {
    mutate,
    isLoading: isUploading,
    isSuccess,
    isError,
    error,
    reset: resetMutation,
  } = useUploadDocument();
  const [file, setFile] = useState<File | null>(null);
  const previewUrl = useObjectUrl(file);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState('');
  const { addNotification } = useNotification();

  // Notify on successful upload (hook already does this, but keep for safety)
  React.useEffect(() => {
    if (isSuccess) addNotification('Dokumen berhasil diupload');
  }, [isSuccess, addNotification]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (!acceptedFiles?.[0]) return;
      const selectedFile = acceptedFiles[0];

      // Validate size
      if (selectedFile.size > MAX_FILE_SIZE) {
        setAnalyzeError(
          `File terlalu besar (${(selectedFile.size / (1024 * 1024)).toFixed(
            1,
          )} MB). Maksimal ${(MAX_FILE_SIZE / (1024 * 1024)).toFixed(0)} MB.`,
        );
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setAnalyzeError('');
      resetMutation();

      // Preview for PDFs only – useObjectUrl hook handles it

      // Analyze metadata
      setIsAnalyzing(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      try {
        const res = await api.post('/upload/analyze', formData);
        const { parsed } = res.data;
        if (parsed) {
          if (parsed.nomor) setValue('nomor', parsed.nomor);
          if (parsed.sifat) setValue('sifat', parsed.sifat);
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
        resetMutation();
      } finally {
        setIsAnalyzing(false);
      }
    },
    [resetMutation, setValue],
  );

  const { getRootProps, getInputProps } = useDropzone({
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
    Object.entries(data).forEach(([k, v]) => {
      if (v) formData.append(k, v as string);
    });
    mutate(formData);
  };

  const handleReset = () => {
    setFile(null);
    setAnalyzeError('');
    reset();
    resetMutation();
  };

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
            <button onClick={handleReset} className="btn-primary">
              Upload Lagi
            </button>
            <button onClick={() => navigate('/search')} className="btn-secondary">
              Lihat Arsip
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <FormProvider {...methods}>
      <div className="max-w-7xl mx-auto animate-fade-in h-[calc(100vh-8rem)] flex flex-col">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Upload & Review</h1>
            <p className="text-slate-600 text-sm mt-2 font-normal leading-relaxed">
              Review dokumen sebelum disimpan ke arsip.
            </p>
          </div>
        </div>
        {!file ? (
          <div
            {...getRootProps()}
            className="flex-none bg-white rounded-2xl border-2 border-dashed border-slate-300 hover:border-primary-500 hover:bg-slate-50/50 transition-all cursor-pointer p-8 sm:p-12 flex flex-col items-center justify-center min-h-[280px] sm:min-h-[380px]"
          >
            <input {...getInputProps()} />
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-primary-50 text-user-primary rounded-2xl flex items-center justify-center mx-auto mb-4 text-primary-600">
                <Upload size={32} />
              </div>
              <h3 className="text-lg sm:text-xl font-semibold text-slate-900 mb-1">
                Unggah Dokumen Surat
              </h3>
              <p className="text-slate-500 mb-2 text-sm sm:text-base">
                Klik atau drag file PDF/DOCX kesini.
              </p>
              <p className="text-xs text-slate-400">Sistem akan otomatis membaca metadata surat.</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-6 min-h-0">
            {/* Left: Preview */}
            <div className="bg-slate-800 rounded-xl overflow-hidden shadow-lg flex flex-col relative order-2 sm:order-1">
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
            <div className="bg-white rounded-xl border border-slate-200 shadow-card flex flex-col h-full overflow-hidden order-1 sm:order-2">
              <div className="p-6 border-b border-slate-100">
                <h3 className="font-bold text-lg text-slate-900 flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-primary-600 rounded-full inline-block" /> Review
                  Data
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
                <form id="upload-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                  <MetadataField label="Sifat Surat" name="sifat" readOnly />
                  <MetadataField label="Tahun" name="tahun" readOnly />
                  <MetadataField label="Jenis Surat" name="jenis" />
                  <MetadataField label="Tanggal Surat" name="tanggal_surat" readOnly />
                  {/* Hidden fields */}
                  <input type="hidden" {...register('perihal')} />
                  <input type="hidden" {...register('pengirim')} />
                  <input type="hidden" {...register('penerima')} />
                  <input type="hidden" {...register('nomor')} />
                </form>
              </div>
              <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3 shrink-0">
                <button onClick={handleReset} className="btn-secondary py-2.5 text-sm">
                  Batal
                </button>
                <button
                  type="submit"
                  form="upload-form"
                  disabled={isUploading}
                  className="btn-primary py-2.5 flex items-center gap-2 text-sm"
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
    </FormProvider>
  );
}
