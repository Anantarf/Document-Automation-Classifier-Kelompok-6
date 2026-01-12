import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock hooks used by DocumentView
vi.mock('../hooks/useDocument', () => ({
  useDocument: () => ({
    data: { id: 1, source_filename: 'doc.pdf', mime_type: 'application/pdf' },
  }),
}));
vi.mock('../hooks/useDocumentFile', () => ({
  useDocumentFile: () => ({ data: new Blob(['%PDF-1.4'], { type: 'application/pdf' }) }),
}));
vi.mock('../hooks/useDocumentText', () => ({
  useDocumentText: () => ({ data: 'This is a sample OCR text with several matches: foo bar foo.' }),
}));

import DocumentView from '../pages/DocumentView';

describe('DocumentView keyboard shortcuts', () => {
  beforeEach(() => {
    // Render fresh for each test
    render(<DocumentView />);
  });

  it('focuses the search input when pressing f', async () => {
    const input = screen.getByPlaceholderText('Cari di teks (highlight)');
    expect(document.activeElement).not.toBe(input);

    fireEvent.keyDown(window, { key: 'f' });
    await waitFor(() => expect(document.activeElement).toBe(input));
  });

  it('does not trigger navigation when typing inside the search input', async () => {
    const input = screen.getByPlaceholderText('Cari di teks (highlight)') as HTMLInputElement;
    input.focus();
    expect(document.activeElement).toBe(input);

    // Typing 'n' should not blur the input or move focus
    fireEvent.keyDown(window, { key: 'n' });
    await waitFor(() => expect(document.activeElement).toBe(input));
  });
});
