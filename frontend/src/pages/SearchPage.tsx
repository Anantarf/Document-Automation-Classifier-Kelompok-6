import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getYears, getMonths, searchDocuments } from '../api/documents';
import api from '../api/axios';
import { useAuth } from '../contexts/AuthContext';
import {
  Folder,
  FileText,
  ChevronRight,
  Home,
  ArrowLeft,
  Trash2,
  Edit2,
  Save,
  X,
  Eye,
  Download,
  Search,
  BookOpen,
} from 'lucide-react';
import { Document } from '../types';
import PDFPreview from '../components/PDFPreview';

// --- Types ---
type ViewLevel = 'root' | 'jenis' | 'tahun' | 'bulan';
type Breadcrumb = { label: string; value: string; level: ViewLevel };

export default function ArchivePage() {
  const [path, setPath] = useState<Breadcrumb[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [localSearch, setLocalSearch] = useState('');
  const [globalSearch, setGlobalSearch] = useState('');
  const [debouncedGlobalSearch, setDebouncedGlobalSearch] = useState('');
  const qc = useQueryClient();
  const { user } = useAuth(); // Auth Context

  // Debounce global search untuk performa lebih baik
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedGlobalSearch(globalSearch);
    }, 300); // Tunggu 300ms setelah user berhenti mengetik

    return () => clearTimeout(timer);
  }, [globalSearch]);

  // Helper to get current context
  const currentLevel =
    path.length === 0
      ? 'root'
      : path.length === 1
        ? 'jenis'
        : path.length === 2
          ? 'tahun'
          : 'bulan';

  const currentJenis = path.find((p) => p.level === 'jenis')?.value;
  const currentTahun = path.find((p) => p.level === 'tahun')?.value;
  const currentBulan = path.find((p) => p.level === 'bulan')?.value;

  const isGlobalSearch = debouncedGlobalSearch.trim().length > 0;

  // --- Queries ---
  const { data: years = [] } = useQuery(['years', currentJenis], () => getYears(currentJenis), {
    enabled: !isGlobalSearch && currentLevel === 'jenis' && !!currentJenis,
  });

  const { data: months = [] } = useQuery(
    ['months', currentTahun, currentJenis],
    () => getMonths(Number(currentTahun), currentJenis!),
    { enabled: !isGlobalSearch && currentLevel === 'tahun' && !!currentTahun },
  );

  // Context-sensitive Docs Query - Now enabled for all levels with folder context
  const { data: documentsData, isLoading: isLoadingDocs } = useQuery(
    ['docs', currentTahun, currentJenis, currentBulan, localSearch, debouncedGlobalSearch],
    () =>
      searchDocuments({
        // If global search, ignore filters
        jenis: isGlobalSearch ? undefined : currentJenis,
        year: isGlobalSearch ? undefined : currentTahun,
        bulan: isGlobalSearch ? undefined : currentBulan,
        q: isGlobalSearch ? debouncedGlobalSearch : localSearch,
        limit: 100,
      }),
    {
      enabled: isGlobalSearch || currentLevel !== 'root',
      keepPreviousData: false, // Langsung ganti data, jangan keep previous
    },
  );

  const documents = documentsData?.items || [];

  // --- Mutations ---
  const deleteMutation = useMutation(
    async (id: number) => {
      if (!confirm('Apakah anda yakin ingin menghapus dokumen ini?')) throw new Error('Cancelled');
      await api.delete(`/documents/${id}`);
    },
    {
      onSuccess: () => {
        qc.invalidateQueries(['docs']);
        setSelectedDoc(null);
      },
    },
  );

  const updateMutation = useMutation(
    async (data: { id: number; updates: any }) => {
      const { id, updates } = data;
      await api.patch(`/documents/${id}`, updates);
    },
    {
      onSuccess: () => {
        qc.invalidateQueries(['docs']);
        alert('Berhasil diperbarui');
      },
    },
  );

  // --- Navigation Handlers ---
  const handleNavigate = (item: Breadcrumb) => {
    setPath((prev) => [...prev, item]);
    setLocalSearch('');
    setSelectedDoc(null);
    setGlobalSearch(''); // Clear global search on nav
  };

  const handleBreadcrumbClick = (index: number) => {
    setPath((prev) => prev.slice(0, index + 1));
    setSelectedDoc(null);
    setGlobalSearch('');
  };

  const handleGlobalSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setGlobalSearch(e.target.value);
    setSelectedDoc(null);
    // If user starts typing, we conceptually "leave" the folder view,
    // but we don't clear path so they can clear search to go back.
  };

  const handleRename = () => {
    if (!selectedDoc) return;
    const newPerihal = prompt('Masukkan Perihal baru:', selectedDoc.perihal || '');
    if (newPerihal !== null && newPerihal !== selectedDoc.perihal) {
      updateMutation.mutate({ id: selectedDoc.id, updates: { perihal: newPerihal } });
    }
  };

  // --- Renders ---

  // 1. Breadcrumbs
  const renderBreadcrumbs = () => {
    if (isGlobalSearch)
      return (
        <div className="flex items-center gap-2 text-sm font-medium text-slate-500 mb-6 bg-white p-3 rounded-xl border border-slate-200 shadow-sm">
          <Search size={16} className="text-primary-500" />
          <span className="text-slate-900 font-bold">
            Hasil Pencarian: "{debouncedGlobalSearch}"
          </span>
        </div>
      );

    return (
      <div className="flex items-center gap-2 text-sm font-medium text-slate-500 mb-6 bg-white p-3 rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <button
          onClick={() => setPath([])}
          className={`p-1.5 rounded-lg hover:bg-primary-50 transition-colors ${path.length === 0 ? 'text-primary-600 bg-primary-50' : 'text-slate-500 hover:text-primary-600'}`}
          title="Pengarsipan"
        >
          <BookOpen size={18} className="shrink-0" />
        </button>
        {path.map((p, i) => (
          <div key={p.value} className="flex items-center gap-2 whitespace-nowrap">
            <ChevronRight size={14} className="text-slate-300 shrink-0" />
            <button
              onClick={() => (i < path.length - 1 ? handleBreadcrumbClick(i) : null)}
              className={`${i === path.length - 1 ? 'text-slate-900 font-bold pointer-events-none' : 'hover:text-primary-600 transition-colors'}`}
            >
              {p.label}
            </button>
          </div>
        ))}
      </div>
    );
  };

  // 2. Folder Views
  const renderFolders = () => {
    if (isGlobalSearch) return null; // Hide folders if searching

    if (currentLevel === 'root') {
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto mt-10">
          <button
            onClick={() => handleNavigate({ label: 'Surat Masuk', value: 'masuk', level: 'jenis' })}
            className="p-8 bg-blue-50 border-2 border-blue-100 rounded-2xl hover:bg-blue-100 hover:border-blue-300 hover:shadow-lg transition-all group text-left"
          >
            <div className="w-16 h-16 bg-blue-600 text-white rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-md">
              <Folder size={32} fill="currentColor" className="opacity-90" />
            </div>
            <h3 className="text-xl font-bold text-blue-900">Surat Masuk</h3>
            <p className="text-blue-700 mt-1 text-sm">Arsip dokumen dari instansi luar</p>
          </button>
          <button
            onClick={() =>
              handleNavigate({ label: 'Surat Keluar', value: 'keluar', level: 'jenis' })
            }
            className="p-8 bg-slate-50 border-2 border-slate-100 rounded-2xl hover:bg-slate-100 hover:border-slate-300 hover:shadow-lg transition-all group text-left"
          >
            <div className="w-16 h-16 bg-slate-700 text-white rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-md">
              <Folder size={32} fill="currentColor" className="opacity-90" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Surat Keluar</h3>
            <p className="text-slate-600 mt-1 text-sm">Arsip dokumen internal kelurahan</p>
          </button>
          <button
            onClick={() =>
              handleNavigate({ label: 'Dokumen Lainnya', value: 'lainnya', level: 'jenis' })
            }
            className="p-8 bg-slate-50 border-2 border-slate-200 rounded-2xl hover:bg-slate-100 hover:border-slate-300 hover:shadow-lg transition-all group text-left col-span-1 md:col-span-2 lg:col-span-1"
          >
            <div className="w-16 h-16 bg-slate-500 text-white rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-md">
              <Folder size={32} fill="currentColor" className="opacity-90" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Dokumen Lainnya</h3>
            <p className="text-slate-600 mt-1 text-sm">Arsip dokumen umum lainnya</p>
          </button>
        </div>
      );
    }

    if (currentLevel === 'jenis') {
      if (years.length === 0) return <EmptyState msg="Belum ada arsip tahunan" />;
      return (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {years.map((y) => (
            <button
              key={y}
              onClick={() => handleNavigate({ label: String(y), value: String(y), level: 'tahun' })}
              className="flex flex-col items-center justify-center p-6 bg-white border border-slate-200 rounded-xl hover:border-primary-400 hover:shadow-md transition-all group"
            >
              <Folder
                size={48}
                className="text-primary-200 fill-primary-50 group-hover:text-primary-500 group-hover:fill-primary-100 transition-colors"
              />
              <span className="mt-3 font-semibold text-slate-700 group-hover:text-primary-700">
                {y}
              </span>
            </button>
          ))}
        </div>
      );
    }

    if (currentLevel === 'tahun') {
      if (months.length === 0) return <EmptyState msg="Belum ada arsip bulanan" />;
      return (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {months.map((m) => (
            <button
              key={m}
              onClick={() => handleNavigate({ label: m, value: m, level: 'bulan' })}
              className="flex flex-col items-center justify-center p-6 bg-white border border-slate-200 rounded-xl hover:border-blue-400 hover:shadow-md transition-all group"
            >
              <Folder
                size={48}
                className="text-slate-300 fill-slate-50 group-hover:text-blue-500 group-hover:fill-blue-100 transition-colors"
              />
              <span className="mt-3 font-semibold text-slate-700 group-hover:text-blue-700">
                {m}
              </span>
            </button>
          ))}
        </div>
      );
    }

    return null;
  };

  // 3. File List View (only shown at bulan level or Global Search)
  const renderFiles = () => {
    // Show files ONLY at bulan level (most specific folder) OR during global search
    if (!isGlobalSearch && currentLevel !== 'bulan') return null;

    // If a document is selected, show full modal preview
    if (selectedDoc) {
      return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-2 sm:p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-7xl max-h-[95vh] overflow-hidden flex flex-col animate-fade-in">
            {/* Modal Header */}
            <div className="p-4 sm:p-6 border-b border-slate-200 flex items-center justify-between bg-slate-50 shrink-0">
              <h2 className="text-lg sm:text-xl font-bold text-slate-900 truncate">
                {selectedDoc.perihal}
              </h2>
              <div className="flex items-center gap-1 sm:gap-2">
                {user?.role === 'admin' && (
                  <button
                    onClick={handleRename}
                    className="p-2 text-slate-600 hover:text-primary-600 hover:bg-slate-100 rounded-lg transition-all"
                    title="Ubah Nama/Perihal"
                  >
                    <Edit2 size={18} />
                  </button>
                )}
                <button
                  onClick={() => {
                    const token = localStorage.getItem('token');
                    const url = `${api.defaults.baseURL}/documents/${selectedDoc.id}/file`;
                    const link = document.createElement('a');
                    link.href = url;
                    link.setAttribute('download', selectedDoc.perihal || 'dokumen');
                    if (token) {
                      fetch(url, { headers: { Authorization: `Bearer ${token}` } })
                        .then((res) => res.blob())
                        .then((blob) => {
                          const blobUrl = window.URL.createObjectURL(blob);
                          link.href = blobUrl;
                          link.click();
                          window.URL.revokeObjectURL(blobUrl);
                        });
                    } else {
                      link.click();
                    }
                  }}
                  className="p-2 text-slate-600 hover:text-green-600 hover:bg-slate-100 rounded-lg transition-all"
                  title="Download"
                >
                  <Download size={18} />
                </button>
                {user?.role === 'admin' && (
                  <button
                    onClick={() => deleteMutation.mutate(selectedDoc.id)}
                    className="p-2 text-slate-600 hover:text-red-600 hover:bg-slate-100 rounded-lg transition-all"
                    title="Hapus Dokumen"
                  >
                    <Trash2 size={18} />
                  </button>
                )}
                <button
                  onClick={() => setSelectedDoc(null)}
                  className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-all ml-1 sm:ml-2"
                  title="Tutup"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-hidden flex flex-col lg:flex-row gap-4 lg:gap-0">
              {/* Preview - Full width on mobile, 2/3 on desktop */}
              <div className="flex-1 bg-slate-100 p-4 sm:p-6 overflow-y-auto flex items-center justify-center min-h-[400px] lg:min-h-auto">
                {selectedDoc.mime_type === 'application/pdf' ? (
                  <PDFPreview docId={selectedDoc.id} />
                ) : (
                  <div className="flex flex-col items-center justify-center text-slate-500">
                    <FileText size={80} className="opacity-20 mb-4" />
                    <p className="font-semibold text-lg">
                      Preview tidak tersedia untuk format DOCX.
                    </p>
                    <p className="text-sm mt-2">Silakan download untuk melihat dokumen.</p>
                  </div>
                )}
              </div>

              {/* Metadata Sidebar - Full width on mobile, 1/3 on desktop */}
              <div className="w-full lg:w-1/3 bg-slate-50 border-t lg:border-t-0 lg:border-l border-slate-200 p-4 sm:p-6 overflow-y-auto">
                <h3 className="font-bold text-slate-900 mb-4 text-sm sm:text-base">
                  Informasi Surat
                </h3>
                <div className="space-y-3 sm:space-y-4">
                  {[
                    { label: 'Perihal', value: selectedDoc.perihal },
                    { label: 'Sifat Surat', value: selectedDoc.sifat },
                    {
                      label: 'Jenis Surat',
                      value:
                        selectedDoc.jenis === 'masuk'
                          ? 'Surat Masuk'
                          : selectedDoc.jenis === 'keluar'
                            ? 'Surat Keluar'
                            : 'Dokumen Lainnya',
                    },
                    { label: 'Tahun', value: selectedDoc.tahun },
                    { label: 'Tanggal Surat', value: selectedDoc.tanggal_surat },
                    { label: 'Pengirim', value: selectedDoc.pengirim },
                    { label: 'Penerima', value: selectedDoc.penerima },
                  ].map(({ label, value }) =>
                    value ? (
                      <div key={label} className="border-b border-slate-200 pb-3 last:border-b-0">
                        <p className="text-xs font-semibold text-slate-500 uppercase mb-1">
                          {label}
                        </p>
                        <p className="text-sm text-slate-900 break-words">{String(value)}</p>
                      </div>
                    ) : null,
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    // DOCUMENT LIST - Show when at bulan level or global search (no document selected)
    return (
      <div className="w-full">
        {isLoadingDocs ? (
          <div className="text-center py-12 text-slate-500">Memuat dokumen...</div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            {isGlobalSearch ? 'Tidak ada hasil ditemukan' : 'Tidak ada dokumen'}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {documents.map((d) => (
              <button
                key={d.id}
                onClick={() => setSelectedDoc(d)}
                className="p-4 bg-white border border-slate-200 rounded-xl hover:border-blue-400 hover:shadow-lg transition-all text-left group"
              >
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-blue-50 rounded-lg text-blue-600 shrink-0 group-hover:bg-blue-100 transition-colors">
                    <FileText size={20} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-slate-900 text-sm truncate group-hover:text-blue-600 transition-colors">
                      {d.perihal || 'Tanpa Perihal'}
                    </p>
                    <p className="text-xs text-slate-500 mt-1 truncate">
                      {d.nomor_surat || 'Tanpa Nomor'}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">{d.tanggal_surat || d.tahun}</p>
                    {isGlobalSearch && (
                      <span className="inline-block mt-2 px-2 py-1 rounded bg-slate-100 text-[10px] text-slate-600 uppercase tracking-wide font-medium">
                        {d.jenis === 'masuk'
                          ? 'Masuk'
                          : d.jenis === 'keluar'
                            ? 'Keluar'
                            : 'Lainnya'}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  const EmptyState = ({ msg }: { msg: string }) => (
    <div className="flex flex-col items-center justify-center py-20 text-slate-400">
      <Folder size={64} className="opacity-20 mb-4" />
      <p className="text-lg font-medium">{msg}</p>
    </div>
  );

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Pengarsipan</h1>
          <p className="text-slate-600 text-sm mt-2 font-normal leading-relaxed">
            Kelola arsip surat masuk dan keluar.
          </p>
        </div>

        {/* Global Search Box */}
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Cari semua dokumen..."
            className="w-full pl-12 pr-12 py-3 bg-white border border-slate-200 rounded-xl shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-400 transition-all text-sm font-medium hover:border-slate-300"
            value={globalSearch}
            onChange={handleGlobalSearch}
          />
          {isGlobalSearch && (
            <button
              onClick={() => setGlobalSearch('')}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 p-1 rounded-md transition-colors"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-col flex-1 overflow-hidden">
        {renderBreadcrumbs()}

        <div className="flex-1 overflow-y-auto min-h-0 rounded-2xl space-y-6">
          {/* Show folders if not in global search mode */}
          {!isGlobalSearch && renderFolders()}

          {/* Show files if at bulan level or in global search */}
          {renderFiles()}
        </div>
      </div>
    </div>
  );
}
