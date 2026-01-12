import { useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadDocument } from '../api/documents';

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation((form: FormData) => uploadDocument(form), {
    onSuccess: () => {
      // Invalidate search so uploaded doc shows up in search results
      // Match SearchPage.tsx query key pattern
      qc.invalidateQueries(['docs']);
      qc.invalidateQueries(['years']);
      qc.invalidateQueries(['months']);
    },
  });
}
