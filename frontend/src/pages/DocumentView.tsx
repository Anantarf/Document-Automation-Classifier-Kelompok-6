import React from 'react';
import { useParams } from 'react-router-dom';
import { useDocument } from '../hooks/useDocument';
import { useDocumentFile } from '../hooks/useDocumentFile';
import { useDocumentText } from '../hooks/useDocumentText';
import { Document, Page, pdfjs } from 'react-pdf';
import {
  ChevronRight,
  Download,
  FileText,
  ZoomIn,
  ZoomOut,
  Search,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';

// Point pdfjs worker to CDN (vite dev) or local in production; using CDN here for simplicity
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@3.12.313/build/pdf.worker.min.js`;

function Spinner() {
  return (
    <div className="flex items-center justify-center h-24">
      <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-400 border-t-transparent" />
    </div>
  );
}

export default function DocumentView() {
  const { id } = useParams();
  const docId = id ? Number(id) : null;
  const { data: doc } = useDocument(docId, Boolean(docId));
  const { data: fileBlob } = useDocumentFile(docId, Boolean(docId));
  const { data: text } = useDocumentText(docId, Boolean(docId));

  const [numPages, setNumPages] = React.useState<number>(0);
  const [currentPage, setCurrentPage] = React.useState<number>(1);
  const [scale, setScale] = React.useState<number>(1.0);

  const [searchText, setSearchText] = React.useState<string>('');

  const matchRefs = React.useRef<Array<HTMLSpanElement | null>>([]);
  const [matchCount, setMatchCount] = React.useState<number>(0);
  const [currentMatchIndex, setCurrentMatchIndex] = React.useState<number | null>(null);

  // Cache blob URL and clean up - improved cleanup on unmount
  const fileUrlRef = React.useRef<string | undefined>(undefined);
  React.useEffect(() => {
    // Clean previous URL if exists
    if (fileUrlRef.current) {
      URL.revokeObjectURL(fileUrlRef.current);
      fileUrlRef.current = undefined;
    }

    // Create new URL if blob available
    if (fileBlob && typeof URL.createObjectURL === 'function') {
      fileUrlRef.current = URL.createObjectURL(fileBlob);
    }

    // Cleanup on unmount or blob change
    return () => {
      if (fileUrlRef.current) {
        try {
          URL.revokeObjectURL(fileUrlRef.current);
        } catch (e) {
          // Ignore errors during cleanup
          console.warn('Error revoking object URL:', e);
        }
        fileUrlRef.current = undefined;
      }
    };
  }, [fileBlob, docId]);

  const onDocumentLoadSuccess = (pdf: { numPages?: number }) => {
    setNumPages(pdf.numPages || 0);
    setCurrentPage(1);
  };

  React.useEffect(() => {
    if (!text || !searchText) {
      setMatchCount(0);
      setCurrentMatchIndex(null);
      matchRefs.current = [];
      return;
    }
    const escaped = searchText.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&');
    const re = new RegExp(escaped, 'gi');
    const matches = text.match(re) || [];
    setMatchCount(matches.length);
    setCurrentMatchIndex(matches.length > 0 ? 0 : null);
    matchRefs.current = [];
  }, [text, searchText]);

  function goToMatch(index: number) {
    if (matchCount === 0) return;
    const idx = ((index % matchCount) + matchCount) % matchCount;
    setCurrentMatchIndex(idx);
    const el = matchRefs.current[idx];
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add('ring', 'ring-yellow-300');
      setTimeout(() => el.classList.remove('ring', 'ring-yellow-300'), 1000);
    }
  }

  const nextMatch = React.useCallback(() => {
    if (matchCount === 0) return;
    goToMatch((currentMatchIndex ?? 0) + 1);
  }, [matchCount, currentMatchIndex]);
  const prevMatch = React.useCallback(() => {
    if (matchCount === 0) return;
    goToMatch((currentMatchIndex ?? 0) - 1);
  }, [matchCount, currentMatchIndex]);

  // keyboard shortcuts: ← → for page, f to focus search, n/p for next/prev match
  const searchInputRef = React.useRef<HTMLInputElement | null>(null);
  React.useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // ignore when modifier keys are pressed
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      const target = e.target as HTMLElement | null;
      const targetTag = target?.tagName || '';
      const isTyping =
        targetTag === 'INPUT' ||
        targetTag === 'TEXTAREA' ||
        (target && (target as HTMLElement).isContentEditable);

      // 'f' should always focus the search input (prevent default)
      if (e.key.toLowerCase() === 'f') {
        if (searchInputRef.current) {
          searchInputRef.current.focus();
          e.preventDefault();
        }
        return;
      }

      // If user is typing into an input/textarea/contenteditable, don't intercept navigation keys
      if (isTyping) return;

      if (e.key === 'ArrowLeft') {
        setCurrentPage((p) => Math.max(1, p - 1));
      } else if (e.key === 'ArrowRight') {
        setCurrentPage((p) => Math.min(numPages, p + 1));
      } else if (e.key.toLowerCase() === 'n') {
        nextMatch();
      } else if (e.key.toLowerCase() === 'p') {
        prevMatch();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [numPages, currentMatchIndex, matchCount, nextMatch, prevMatch]);

  function renderTextWithMatches(content: string | null | undefined, q: string | null | undefined) {
    if (!content) return <div className="text-sm text-gray-600">No extracted text available</div>;
    if (!q) return <div className="text-sm text-gray-800 whitespace-pre-wrap">{content}</div>;

    const escaped = q.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&');
    const parts = content.split(new RegExp(`(${escaped})`, 'gi'));
    let matchIndex = 0;

    return (
      <div className="text-sm text-gray-800 whitespace-pre-wrap">
        {parts.map((part, i) => {
          if (part.match(new RegExp(`^${escaped}$`, 'i'))) {
            const idx = matchIndex++;
            return (
              <mark
                ref={(el) => (matchRefs.current[idx] = el)}
                data-match-index={idx}
                key={i}
                className="bg-yellow-200"
              >
                {part}
              </mark>
            );
          }
          return <span key={i}>{part}</span>;
        })}
      </div>
    );
  }

  function Thumbnail({ pageNumber }: { pageNumber: number }) {
    const ref = React.useRef<HTMLDivElement | null>(null);
    const [visible, setVisible] = React.useState(false);

    React.useEffect(() => {
      const el = ref.current;
      if (!el) return;
      const obs = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) setVisible(true);
          }
        },
        { root: null, threshold: 0.1 },
      );
      obs.observe(el);
      return () => obs.disconnect();
    }, []);

    return (
      <div
        ref={ref}
        className={`cursor-pointer p-1 rounded border ${currentPage === pageNumber ? 'ring ring-blue-300' : ''}`}
        onClick={() => setCurrentPage(pageNumber)}
      >
        <div className="text-xs text-gray-600 mb-1">Page {pageNumber}</div>
        <div className="bg-white w-full h-24 flex items-center justify-center">
          {visible && fileUrlRef.current ? (
            <Document
              file={fileUrlRef.current}
              loading={<div className="h-12 w-full bg-gray-100" />}
            >
              <Page pageNumber={pageNumber} width={120} />
            </Document>
          ) : (
            <div className="h-12 w-full bg-gray-100 animate-pulse" />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h1 className="text-2xl font-bold text-slate-900">{doc?.perihal || 'Dokumen'}</h1>
        <p className="text-slate-600 text-sm mt-2">
          ID: {doc?.id} • Tipe: {doc?.mime_type || 'Unknown'}
        </p>
      </div>

      {/* Tabs Navigation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Preview Area */}
        <div className="lg:col-span-2 space-y-4">
          {/* Preview Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Pratinjau Dokumen</h2>
              {fileBlob && fileUrlRef.current && (
                <a
                  href={fileUrlRef.current}
                  download={`document_${doc?.id}`}
                  className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-lg text-sm font-medium transition-colors"
                >
                  <Download size={16} />
                  Download
                </a>
              )}
            </div>

            {/* Preview Content */}
            <div className="p-6">
              {fileBlob && doc?.mime_type?.includes('pdf') ? (
                <div className="space-y-4">
                  {/* Page Controls */}
                  <div className="flex items-center justify-between gap-4 flex-wrap bg-slate-50 p-4 rounded-lg">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                        disabled={currentPage <= 1}
                        className="p-2 border border-slate-300 rounded-lg hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronUp size={18} />
                      </button>
                      <div className="flex items-center gap-2 min-w-[120px]">
                        <span className="text-sm font-medium text-slate-600">Halaman</span>
                        <input
                          type="number"
                          value={currentPage}
                          min={1}
                          max={numPages}
                          onChange={(e) =>
                            setCurrentPage(
                              Math.max(1, Math.min(numPages, Number(e.target.value) || 1)),
                            )
                          }
                          className="w-12 border border-slate-300 px-2 py-1 rounded text-sm text-center"
                        />
                        <span className="text-sm text-slate-600">/ {numPages}</span>
                      </div>
                      <button
                        onClick={() => setCurrentPage((p) => Math.min(numPages, p + 1))}
                        disabled={currentPage >= numPages}
                        className="p-2 border border-slate-300 rounded-lg hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronDown size={18} />
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setScale((s) => Math.max(0.5, s - 0.25))}
                        className="p-2 border border-slate-300 rounded-lg hover:bg-slate-100 transition-colors"
                      >
                        <ZoomOut size={18} />
                      </button>
                      <span className="text-sm font-medium text-slate-600 min-w-[60px] text-center">
                        {Math.round(scale * 100)}%
                      </span>
                      <button
                        onClick={() => setScale((s) => Math.min(2.5, s + 0.25))}
                        className="p-2 border border-slate-300 rounded-lg hover:bg-slate-100 transition-colors"
                      >
                        <ZoomIn size={18} />
                      </button>
                    </div>
                  </div>

                  {/* PDF Viewer */}
                  <div className="bg-slate-100 rounded-lg p-4 flex flex-col items-center min-h-[400px] max-h-[600px] overflow-y-auto">
                    <Document
                      file={fileUrlRef.current}
                      onLoadSuccess={onDocumentLoadSuccess}
                      loading={<Spinner />}
                    >
                      <Page pageNumber={currentPage} scale={scale} loading={<Spinner />} />
                    </Document>
                  </div>

                  {/* Thumbnails */}
                  {numPages > 1 && (
                    <div className="border-t border-slate-200 pt-4">
                      <p className="text-sm font-medium text-slate-600 mb-3">Halaman lain</p>
                      <div className="grid grid-cols-4 sm:grid-cols-6 gap-2 max-h-[120px] overflow-x-auto">
                        {Array.from({ length: Math.min(numPages, 20) }, (_, i) => (
                          <Thumbnail key={i} pageNumber={i + 1} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : fileBlob ? (
                <div className="text-center py-12">
                  <FileText size={48} className="mx-auto text-slate-400 mb-4" />
                  <p className="text-slate-600">Format file tidak mendukung pratinjau</p>
                </div>
              ) : (
                <div className="text-center py-12">
                  <FileText size={48} className="mx-auto text-slate-400 mb-4" />
                  <p className="text-slate-600">File tidak tersedia</p>
                </div>
              )}
            </div>
          </div>

          {/* OCR / Text Search Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Pencarian Teks</h3>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex gap-2">
                <input
                  ref={searchInputRef}
                  value={searchText}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setSearchText(e.target.value)
                  }
                  placeholder="Cari dalam teks dokumen..."
                  className="flex-1 border border-slate-300 px-3 py-2 rounded-lg text-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-400 outline-none"
                />
                {matchCount > 0 && (
                  <div className="text-sm font-medium text-slate-600 flex items-center gap-1 px-3 py-2 bg-slate-50 rounded-lg min-w-max">
                    {currentMatchIndex !== null ? `${currentMatchIndex + 1}` : '-'} / {matchCount}
                  </div>
                )}
              </div>

              {matchCount > 0 && (
                <div className="flex gap-2">
                  <button
                    onClick={prevMatch}
                    className="flex-1 px-3 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-center gap-2 text-sm font-medium"
                  >
                    <ChevronUp size={16} />
                    Sebelumnya
                  </button>
                  <button
                    onClick={nextMatch}
                    className="flex-1 px-3 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-center gap-2 text-sm font-medium"
                  >
                    <ChevronDown size={16} />
                    Berikutnya
                  </button>
                </div>
              )}

              <div className="max-h-[300px] overflow-y-auto bg-slate-50 rounded-lg p-4 text-sm text-slate-700 leading-relaxed">
                {text ? (
                  renderTextWithMatches(text, searchText)
                ) : (
                  <p className="text-slate-500">Teks tidak tersedia</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar: Metadata */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden sticky top-4">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Metadata</h3>
            </div>
            <div className="p-6 space-y-4">
              {doc ? (
                <>
                  <div className="space-y-3">
                    {[
                      { label: 'Nomor Surat', key: 'nomor_surat' },
                      { label: 'Perihal', key: 'perihal' },
                      { label: 'Sifat', key: 'sifat' },
                      { label: 'Jenis', key: 'jenis' },
                      { label: 'Tahun', key: 'tahun' },
                      { label: 'Tanggal Surat', key: 'tanggal_surat' },
                      { label: 'Pengirim', key: 'pengirim' },
                      { label: 'Penerima', key: 'penerima' },
                    ].map(({ label, key }) =>
                      (doc as any)[key] ? (
                        <div key={key} className="border-b border-slate-100 pb-3 last:border-b-0">
                          <p className="text-xs font-semibold text-slate-500 uppercase mb-1">
                            {label}
                          </p>
                          <p className="text-sm text-slate-900 break-words">
                            {String((doc as any)[key])}
                          </p>
                        </div>
                      ) : null,
                    )}
                  </div>
                </>
              ) : (
                <div className="text-sm text-slate-500 text-center py-8">Loading...</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
