import api from './axios';
import type { Document } from '../types';

export type SearchResult = {
  items: Document[];
  total: number;
};

export type SearchParams = Record<string, string | number | boolean | undefined>;

export async function searchDocuments(params: SearchParams): Promise<SearchResult> {
  const res = await api.get<Document[]>('/search/', { params });
  const total = Number(res.headers['x-total-count'] ?? res.data.length);
  return { items: res.data, total };
}

export async function uploadDocument(formData: FormData) {
  const { data } = await api.post('/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function getYears(jenis?: string): Promise<number[]> {
  const { data } = await api.get<number[]>('/search/years', { params: { jenis } });
  return data;
}

export async function getMonths(tahun: number, jenis: string): Promise<string[]> {
  const { data } = await api.get<string[]>('/search/months', { params: { tahun, jenis } });
  return data;
}
