import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion } from 'framer-motion'
import { CloudUpload, FolderOpen, X } from 'lucide-react'

const MAX_BYTES = 20 * 1024 * 1024
const ACCEPT = {
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/webp': ['.webp'],
}

interface UploadZoneProps {
  disabled?: boolean
  file?: File | null
  previewUrl?: string | null
  onFileAccepted: (file: File) => void
  onClear?: () => void
  onError: (message: string) => void
}

export function UploadZone({
  disabled,
  file,
  previewUrl,
  onFileAccepted,
  onClear,
  onError,
}: UploadZoneProps) {
  const onDrop = useCallback(
    (accepted: File[], rejected: unknown[]) => {
      if (rejected.length > 0) {
        onError('Invalid file. Use JPG, PNG, or WEBP under 20 MB.')
        return
      }
      const next = accepted[0]
      if (!next) return
      if (next.size > MAX_BYTES) {
        onError('File exceeds the 20 MB limit.')
        return
      }
      onFileAccepted(next)
    },
    [onError, onFileAccepted],
  )

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: ACCEPT,
    multiple: false,
    disabled,
    maxSize: MAX_BYTES,
    noClick: true,
    noKeyboard: true,
  })

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.12 }}
      className="container-app"
    >
      <div
        {...getRootProps()}
        className={[
          'glass-panel relative overflow-hidden rounded-3xl transition',
          isDragActive ? 'ring-2 ring-accent shadow-[0_0_40px_rgba(59,130,246,0.2)]' : '',
          disabled ? 'pointer-events-none opacity-50' : '',
        ].join(' ')}
      >
        <input {...getInputProps()} />

        {file && previewUrl ? (
          <div className="p-4 sm:p-5">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="min-w-0 text-left">
                <p className="truncate text-sm font-semibold text-white">{file.name}</p>
                <p className="text-xs text-muted">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
              </div>
              <button
                type="button"
                disabled={disabled}
                onClick={(e) => {
                  e.stopPropagation()
                  onClear?.()
                }}
                className="rounded-full p-2 text-muted transition hover:bg-white/8 hover:text-white"
                aria-label="Remove image"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="checkerboard flex max-h-[320px] items-center justify-center rounded-2xl p-3">
              <img
                src={previewUrl}
                alt="Upload preview"
                className="max-h-[290px] max-w-full rounded-xl object-contain"
              />
            </div>
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                disabled={disabled}
                onClick={(e) => {
                  e.stopPropagation()
                  open()
                }}
                className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10"
              >
                <FolderOpen className="h-4 w-4 text-accent" />
                Change Image
              </button>
            </div>
          </div>
        ) : (
          <div className="flex min-h-[260px] flex-col items-center justify-center border border-dashed border-accent/45 px-6 py-12 sm:min-h-[300px] sm:rounded-[1.4rem] sm:m-1">
            <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-soft text-accent">
              <CloudUpload className="h-8 w-8" strokeWidth={1.75} />
            </div>
            <p className="text-base font-semibold text-white sm:text-lg">
              {isDragActive ? 'Drop your image here' : 'Drag & Drop your image here or'}
            </p>
            <button
              type="button"
              disabled={disabled}
              onClick={(e) => {
                e.stopPropagation()
                open()
              }}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-semibold text-white shadow-[0_10px_30px_rgba(59,130,246,0.35)] transition hover:bg-[#2563eb]"
            >
              <FolderOpen className="h-4 w-4" />
              Choose Image
            </button>
            <p className="mt-4 text-xs text-muted">JPG, PNG, WEBP up to 20MB</p>
          </div>
        )}
      </div>
    </motion.section>
  )
}
