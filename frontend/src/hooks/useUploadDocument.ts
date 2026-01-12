import { useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadDocument } from "../api/documents";

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation((form: FormData) => uploadDocument(form), {
    onSuccess: () => {
      // Invalidate search so uploaded doc shows up in search results
      qc.invalidateQueries(["search-docs"]);
    },
  });
}
