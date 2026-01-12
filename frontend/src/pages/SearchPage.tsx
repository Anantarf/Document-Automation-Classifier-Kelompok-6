import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getYears, getMonths, searchDocuments } from '../api/documents';
import api from '../api/axios';
import { 
    Folder, FileText, ChevronRight, Home, ArrowLeft, 
    Trash2, Edit2, Save, X, Eye, Download, Search
} from 'lucide-react';
import { Document } from '../types';

// --- Types ---
type ViewLevel = 'root' | 'jenis' | 'tahun' | 'bulan';
type Breadcrumb = { label: string; value: string; level: ViewLevel };

export default function ArchivePage() {
    const [path, setPath] = useState<Breadcrumb[]>([]);
    const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
    const [localSearch, setLocalSearch] = useState('');
    const [globalSearch, setGlobalSearch] = useState('');
    const qc = useQueryClient();

    // Helper to get current context
    const currentLevel = path.length === 0 ? 'root' 
                       : path.length === 1 ? 'jenis' 
                       : path.length === 2 ? 'tahun' 
                       : 'bulan';
    
    const currentJenis = path.find(p => p.level === 'jenis')?.value;
    const currentTahun = path.find(p => p.level === 'tahun')?.value;
    const currentBulan = path.find(p => p.level === 'bulan')?.value;

    const isGlobalSearch = globalSearch.trim().length > 0;

    // --- Queries ---
    const { data: years = [] } = useQuery(
        ['years', currentJenis], 
        () => getYears(currentJenis),
        { enabled: !isGlobalSearch && currentLevel === 'jenis' && !!currentJenis }
    );

    const { data: months = [] } = useQuery(
        ['months', currentTahun, currentJenis],
        () => getMonths(Number(currentTahun), currentJenis!),
        { enabled: !isGlobalSearch && currentLevel === 'tahun' && !!currentTahun }
    );

    // Context-sensitive Docs Query
    const { data: documentsData, isLoading: isLoadingDocs } = useQuery(
        ['docs', currentTahun, currentJenis, currentBulan, localSearch, globalSearch],
        () => searchDocuments({ 
            // If global search, ignore filters
            jenis: isGlobalSearch ? undefined : currentJenis, 
            year: isGlobalSearch ? undefined : currentTahun, 
            bulan: isGlobalSearch ? undefined : currentBulan,
            q: isGlobalSearch ? globalSearch : localSearch, 
            limit: 100 
        }),
        { enabled: isGlobalSearch || currentLevel === 'bulan' }
    );

    const documents = documentsData?.items || [];

    // --- Mutations ---
    const deleteMutation = useMutation(async (id: number) => {
        if (!confirm('Apakah anda yakin ingin menghapus dokumen ini?')) throw new Error('Cancelled');
        await api.delete(`/documents/${id}`);
    }, {
        onSuccess: () => {
            qc.invalidateQueries(['docs']);
            setSelectedDoc(null);
        }
    });

    const updateMutation = useMutation(async (data: { id: number, updates: any }) => {
        const { id, updates } = data;
        await api.patch(`/documents/${id}`, updates);
    }, {
        onSuccess: () => {
            qc.invalidateQueries(['docs']);
            alert('Berhasil diperbarui');
        }
    });

    // --- Navigation Handlers ---
    const handleNavigate = (item: Breadcrumb) => {
        setPath(prev => [...prev, item]);
        setLocalSearch(''); 
        setSelectedDoc(null);
        setGlobalSearch(''); // Clear global search on nav
    };

    const handleBreadcrumbClick = (index: number) => {
        setPath(prev => prev.slice(0, index + 1)); 
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
        if (isGlobalSearch) return (
            <div className="flex items-center gap-2 text-sm font-medium text-slate-500 mb-6 bg-white p-3 rounded-xl border border-slate-200 shadow-sm">
                 <Search size={16} className="text-primary-500" />
                 <span className="text-slate-900 font-bold">Hasil Pencarian: "{globalSearch}"</span>
            </div>
        );

        return (
            <div className="flex items-center gap-2 text-sm font-medium text-slate-500 mb-6 bg-white p-3 rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
                <button 
                    onClick={() => setPath([])}
                    className={`flex items-center gap-1 hover:text-primary-600 transition-colors ${path.length === 0 ? 'text-primary-600' : ''}`}
                >
                    <Home size={16} />
                    <span className="hidden sm:inline">Beranda</span>
                </button>
                {path.map((p, i) => (
                    <div key={p.value} className="flex items-center gap-2 whitespace-nowrap">
                        <ChevronRight size={14} className="text-slate-300" />
                        <button 
                             onClick={() => i < path.length - 1 ? handleBreadcrumbClick(i) : null}
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
                        className="p-8 bg-emerald-50 border-2 border-emerald-100 rounded-2xl hover:bg-emerald-100 hover:border-emerald-300 hover:shadow-lg transition-all group text-left"
                    >
                        <div className="w-16 h-16 bg-emerald-200 text-emerald-700 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <Folder size={32} fill="currentColor" className="opacity-80" />
                        </div>
                        <h3 className="text-xl font-bold text-emerald-900">Surat Masuk</h3>
                        <p className="text-emerald-700 mt-1 text-sm">Arsip dokumen dari instansi luar</p>
                    </button>
                    <button 
                        onClick={() => handleNavigate({ label: 'Surat Keluar', value: 'keluar', level: 'jenis' })}
                        className="p-8 bg-amber-50 border-2 border-amber-100 rounded-2xl hover:bg-amber-100 hover:border-amber-300 hover:shadow-lg transition-all group text-left"
                    >
                        <div className="w-16 h-16 bg-amber-200 text-amber-700 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <Folder size={32} fill="currentColor" className="opacity-80" />
                        </div>
                        <h3 className="text-xl font-bold text-amber-900">Surat Keluar</h3>
                        <p className="text-amber-700 mt-1 text-sm">Arsip dokumen internal kelurahan</p>
                    </button>
                    <button 
                        onClick={() => handleNavigate({ label: 'Dokumen Lainnya', value: 'lainnya', level: 'jenis' })}
                        className="p-8 bg-slate-50 border-2 border-slate-100 rounded-2xl hover:bg-slate-100 hover:border-slate-300 hover:shadow-lg transition-all group text-left col-span-1 md:col-span-2 lg:col-span-1"
                    >
                        <div className="w-16 h-16 bg-slate-200 text-slate-700 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <Folder size={32} fill="currentColor" className="opacity-80" />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900">Dokumen Lainnya</h3>
                        <p className="text-slate-700 mt-1 text-sm">Arsip dokumen umum lainnya</p>
                    </button>
                </div>
            );
        }

        if (currentLevel === 'jenis') {
            if (years.length === 0) return <EmptyState msg="Belum ada arsip tahunan" />;
            return (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                    {years.map(y => (
                        <button 
                            key={y}
                            onClick={() => handleNavigate({ label: String(y), value: String(y), level: 'tahun' })}
                            className="flex flex-col items-center justify-center p-6 bg-white border border-slate-200 rounded-xl hover:border-primary-400 hover:shadow-md transition-all group"
                        >
                             <Folder size={48} className="text-primary-200 fill-primary-50 group-hover:text-primary-500 group-hover:fill-primary-100 transition-colors" />
                             <span className="mt-3 font-semibold text-slate-700 group-hover:text-primary-700">{y}</span>
                        </button>
                    ))}
                </div>
            );
        }

        if (currentLevel === 'tahun') {
            if (months.length === 0) return <EmptyState msg="Belum ada arsip bulanan" />;
            return (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                    {months.map(m => (
                        <button 
                            key={m}
                            onClick={() => handleNavigate({ label: m, value: m, level: 'bulan' })}
                            className="flex flex-col items-center justify-center p-6 bg-white border border-slate-200 rounded-xl hover:border-primary-400 hover:shadow-md transition-all group"
                        >
                             <Folder size={48} className="text-amber-200 fill-amber-50 group-hover:text-amber-500 group-hover:fill-amber-100 transition-colors" />
                             <span className="mt-3 font-semibold text-slate-700 group-hover:text-amber-700">{m}</span>
                        </button>
                    ))}
                </div>
            );
        }
        
        return null; 
    };

    // 3. File List View (for 'bulan' level or Global Search)
    const renderFiles = () => {
        // Show files if we are in a month folder OR if we are doing a global search
        if (!isGlobalSearch && currentLevel !== 'bulan') return null;

        return (
            <div className="flex flex-col h-full overflow-hidden">
                {/* Local Search Bar (Only shown if NOT global search, to avoid confusion) */}
                {!isGlobalSearch && (
                    <div className="mb-4 relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input 
                            type="text"
                            placeholder="Filter dokumen dalam folder ini..."
                            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                            value={localSearch}
                            onChange={(e) => setLocalSearch(e.target.value)}
                        />
                    </div>
                )}

                <div className="flex-1 flex gap-6 min-h-0">
                    {/* List */}
                    <div className={`${selectedDoc ? 'w-1/3 hidden lg:block' : 'w-full'} bg-white border border-slate-200 rounded-xl overflow-y-auto`}>
                        {isLoadingDocs ? (
                            <div className="p-8 text-center text-slate-500">Memuat...</div>
                        ) : documents.length === 0 ? (
                            <EmptyState msg={isGlobalSearch ? "Tidak ada hasil ditemukan" : "Tidak ada dokumen"} />
                        ) : (
                            <div className="divide-y divide-slate-100">
                                {documents.map(d => (
                                    <div 
                                        key={d.id}
                                        onClick={() => setSelectedDoc(d)}
                                        className={`p-4 cursor-pointer transition-colors hover:bg-slate-50 ${selectedDoc?.id === d.id ? 'bg-primary-50 border-l-4 border-primary-500' : 'border-l-4 border-transparent'}`}
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="p-2 bg-slate-100 rounded text-slate-500 shrink-0">
                                                <FileText size={20} />
                                            </div>
                                            <div className="min-w-0">
                                                <p className="font-semibold text-slate-900 text-sm truncate">{d.perihal || 'Tanpa Perihal'}</p>
                                                <p className="text-xs text-slate-500 mt-1">{d.nomor_surat || 'Tanpa Nomor'} • {d.tanggal_surat || d.tahun}</p>
                                                {/* Show Folder Context if Global Search */}
                                                {isGlobalSearch && (
                                                    <span className="inline-block mt-1 px-1.5 py-0.5 rounded bg-slate-100 text-[10px] text-slate-500 uppercase tracking-wide">
                                                        {d.jenis === 'masuk' ? 'Surat Masuk' : 'Surat Keluar'} / {d.tahun}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Preview Panel */}
                    {selectedDoc && (
                         <div className={`${selectedDoc ? 'w-full lg:w-2/3' : 'hidden'} bg-white border border-slate-200 rounded-xl flex flex-col overflow-hidden animate-fade-in`}>
                             {/* Preview Header */}
                             <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                                 <div className="flex items-center gap-3">
                                     <button onClick={() => setSelectedDoc(null)} className="lg:hidden p-1 hover:bg-slate-200 rounded">
                                         <ArrowLeft size={18} />
                                     </button>
                                     <h3 className="font-bold text-slate-800 truncate max-w-sm">{selectedDoc.perihal}</h3>
                                 </div>
                                 <div className="flex items-center gap-2">
                                     <button 
                                        onClick={handleRename}
                                        className="p-2 text-slate-600 hover:text-primary-600 hover:bg-white rounded-lg border border-transparent hover:border-slate-200 transition-all" 
                                        title="Ubah Nama/Perihal"
                                     >
                                         <Edit2 size={18} />
                                     </button>
                                     <a 
                                        href={`http://localhost:8000/documents/${selectedDoc.id}/file`} 
                                        target="_blank" 
                                        rel="noreferrer"
                                        className="p-2 text-slate-600 hover:text-green-600 hover:bg-white rounded-lg border border-transparent hover:border-slate-200 transition-all"
                                        title="Download"
                                     >
                                         <Download size={18} />
                                     </a>
                                     <button 
                                        onClick={() => deleteMutation.mutate(selectedDoc.id)}
                                        className="p-2 text-slate-600 hover:text-red-600 hover:bg-white rounded-lg border border-transparent hover:border-slate-200 transition-all"
                                        title="Hapus Dokumen"
                                     >
                                         <Trash2 size={18} />
                                     </button>
                                 </div>
                             </div>

                             {/* Preview Content */}
                             <div className="flex-1 bg-slate-100 p-4 relative">
                                 {selectedDoc.mime_type === 'application/pdf' ? (
                                      <iframe 
                                        src={`http://localhost:8000/documents/${selectedDoc.id}/file#toolbar=0`} 
                                        className="w-full h-full rounded-lg shadow-sm bg-white" 
                                        title="Preview" 
                                      />
                                 ) : (
                                     <div className="flex flex-col items-center justify-center h-full text-slate-500">
                                         <FileText size={64} className="opacity-20 mb-4" />
                                         <p>Preview tidak tersedia untuk format ini.</p>
                                         <a href={`http://localhost:8000/documents/${selectedDoc.id}/file`} className="text-primary-600 hover:underline mt-2">Download untuk melihat</a>
                                     </div>
                                 )}
                             </div>

                             {/* Metadata Footer */}
                             <div className="p-4 border-t border-slate-200 bg-white text-sm grid grid-cols-2 gap-4">
                                 <div>
                                     <span className="text-slate-400 block text-xs">Nomor Surat</span>
                                     <span className="font-mono text-slate-700">{selectedDoc.nomor_surat || '-'}</span>
                                 </div>
                                 <div>
                                     <span className="text-slate-400 block text-xs">Tanggal Surat</span>
                                     <span className="text-slate-700">{selectedDoc.tanggal_surat || '-'}</span>
                                 </div>
                                 <div>
                                     <span className="text-slate-400 block text-xs">Pengirim</span>
                                     <span className="text-slate-700">{selectedDoc.pengirim || '-'}</span>
                                 </div>
                                 <div>
                                     <span className="text-slate-400 block text-xs">Penerima</span>
                                     <span className="text-slate-700">{selectedDoc.penerima || '-'}</span>
                                 </div>
                             </div>
                         </div>
                    )}
                </div>
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
                     <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Pengarsipan</h1>
                     <p className="text-slate-500 text-sm">Kelola arsip surat masuk dan keluar.</p>
                </div>
                
                {/* Global Search Box */}
                <div className="relative w-full sm:w-72">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input 
                        type="text"
                        placeholder="Cari semua dokumen..."
                        className="w-full pl-10 pr-10 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-sm"
                        value={globalSearch}
                        onChange={handleGlobalSearch}
                    />
                    {isGlobalSearch && (
                        <button 
                            onClick={() => setGlobalSearch('')}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                            <X size={14} />
                        </button>
                    )}
                </div>
            </div>

            {renderBreadcrumbs()}
            
            <div className="flex-1 overflow-y-auto min-h-0 rounded-2xl">
                {isGlobalSearch || currentLevel === 'bulan' ? renderFiles() : renderFolders()}
            </div>
        </div>
    );
}
