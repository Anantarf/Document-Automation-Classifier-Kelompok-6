import React from 'react';
import { useParams } from 'react-router-dom';
import { useDocument } from '../hooks/useDocument';
import { useDocumentFile } from '../hooks/useDocumentFile';
import { useDocumentText } from '../hooks/useDocumentText';
import { Document, Page, pdfjs } from 'react-pdf';

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
    <div className="grid grid-cols-3 gap-4">
      <div className="col-span-2">
        <div className="bg-white p-4 rounded shadow">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-lg font-medium">Document Preview</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="px-2 py-1 border rounded"
                disabled={currentPage <= 1}
              >
                Prev
              </button>
              <div className="text-sm">Page</div>
              <input
                type="number"
                value={currentPage}
                min={1}
                max={numPages}
                onChange={(e) =>
                  setCurrentPage(Math.max(1, Math.min(numPages, Number(e.target.value) || 1)))
                }
                className="w-16 border px-2 py-1 rounded text-sm"
              />
              <div className="text-sm">/ {numPages}</div>

              <button
                onClick={() => setCurrentPage((p) => Math.min(numPages, p + 1))}
                className="px-2 py-1 border rounded"
                disabled={currentPage >= numPages}
              >
                Next
              </button>

              <div className="ml-4 flex items-center gap-2">
                <button
                  onClick={() => setScale((s) => Math.max(0.25, s - 0.25))}
                  className="px-2 py-1 border rounded"
                >
                  -
                </button>
                <div className="text-sm">Zoom {Math.round(scale * 100)}%</div>
                <button
                  onClick={() => setScale((s) => Math.min(3, s + 0.25))}
                  className="px-2 py-1 border rounded"
                >
                  +
                </button>
              </div>

              {fileBlob && fileUrlRef.current && (
                <a
                  className="ml-4 text-sm text-blue-600"
                  href={fileUrlRef.current}
                  download={`document_${doc?.id}`}
                >
                  Download
                </a>
              )}
            </div>
          </div>

          <div className="mt-4 flex gap-4">
            <div className="flex-1 border p-2 rounded">
              {fileBlob && doc?.mime_type?.includes('pdf') ? (
                <div className="flex flex-col items-center">
                  <div className="w-full flex justify-center mb-2">
                    <Document
                      file={fileUrlRef.current}
                      onLoadSuccess={onDocumentLoadSuccess}
                      loading={<Spinner />}
                    >
                      <Page pageNumber={currentPage} scale={scale} loading={<Spinner />} />
                    </Document>
                  </div>
                </div>
              ) : fileBlob ? (
                <div>
                  <a href={fileUrlRef.current} className="text-blue-600" download>
                    Download file
                  </a>
                </div>
              ) : (
                <div className="text-sm text-gray-600">No preview available</div>
              )}
            </div>

            <div className="w-32 overflow-y-auto max-h-[60vh]">
              <div className="space-y-2">
                {Array.from({ length: Math.max(0, numPages) }, (_, i) => (
                  <Thumbnail key={i} pageNumber={i + 1} />
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded shadow mt-4">
          <h3 className="text-md font-medium">Metadata</h3>
          <pre className="text-sm mt-2">{doc ? JSON.stringify(doc, null, 2) : 'Loading...'}</pre>
        </div>
      </div>

      <div>
        <div className="bg-white p-4 rounded shadow">
          <h3 className="text-md font-medium">OCR / Extracted text</h3>
          <div className="mt-2 mb-2 flex gap-2">
            <input
              ref={searchInputRef}
              value={searchText}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchText(e.target.value)}
              placeholder="Cari di teks (highlight)"
              className="border px-2 py-1 rounded w-full text-sm"
            />
            <div className="flex items-center gap-1">
              <button
                onClick={prevMatch}
                className="px-2 py-1 border rounded"
                disabled={matchCount === 0}
              >
                Prev
              </button>
              <button
                onClick={nextMatch}
                className="px-2 py-1 border rounded"
                disabled={matchCount === 0}
              >
                Next
              </button>
            </div>
          </div>

          <div className="text-sm text-gray-600 mb-2">
            Matches: {matchCount}{' '}
            {matchCount > 0 && ` — ${(currentMatchIndex ?? 0) + 1} / ${matchCount}`}
          </div>

          <div className="mt-2 text-sm whitespace-pre-wrap max-h-[60vh] overflow-auto">
            {renderTextWithMatches(text, searchText)}
          </div>
        </div>
      </div>
    </div>
  );
}
