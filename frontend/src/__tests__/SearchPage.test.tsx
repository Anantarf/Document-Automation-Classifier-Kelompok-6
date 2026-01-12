import React from 'react'
import { render, screen } from '@testing-library/react'
import SearchPage from '../pages/SearchPage'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const qc = new QueryClient()

test('renders search page inputs', () => {
  render(
    <QueryClientProvider client={qc}>
      <SearchPage />
    </QueryClientProvider>
  )

  expect(screen.getByPlaceholderText(/Nomor \/ perihal/i)).toBeInTheDocument()
  expect(screen.getByPlaceholderText(/Tahun/i)).toBeInTheDocument()
})
