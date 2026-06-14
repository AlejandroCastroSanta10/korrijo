"use client";

import { useRef, useState } from "react";
import { Upload, X, FileText } from "lucide-react";
import { cn, formatBytes } from "@/lib/utils";

interface DropzoneProps {
  /** Ficheros seleccionados. */
  value: File[];
  onChange: (files: File[]) => void;
  /** Permite varios ficheros (contexto). Si es false, el nuevo reemplaza al previo. */
  multiple?: boolean;
  /** Atributo 'accept' del input nativo (p.ej. ".pdf,.xlsx,.txt,.md,.csv"). */
  accept?: string;
  disabled?: boolean;
  /** Texto principal del área de subida. */
  label: string;
  /** Marca el borde en rojo cuando la validación del padre falla. */
  invalid?: boolean;
  id?: string;
}

/** Evita duplicados al añadir (mismo nombre y tamaño). */
function mergeFiles(existing: File[], incoming: File[]): File[] {
  const seen = new Set(existing.map((f) => `${f.name}:${f.size}`));
  const extra = incoming.filter((f) => !seen.has(`${f.name}:${f.size}`));
  return [...existing, ...extra];
}

export default function Dropzone({
  value,
  onChange,
  multiple = false,
  accept,
  disabled = false,
  label,
  invalid = false,
  id,
}: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  const addFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const list = Array.from(files);
    onChange(multiple ? mergeFiles(value, list) : [list[list.length - 1]]);
  };

  const removeAt = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const open = () => {
    if (!disabled) inputRef.current?.click();
  };

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        id={id}
        onClick={open}
        disabled={disabled}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          if (!disabled) addFiles(e.dataTransfer.files);
        }}
        className={cn(
          "flex min-h-44 w-full flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-input bg-input/20 px-6 py-12 text-center transition-colors",
          "hover:bg-input/40 focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 outline-none",
          dragActive && "border-ring bg-input/40",
          invalid && "border-destructive",
          disabled && "pointer-events-none opacity-50",
        )}
      >
        <Upload className="size-9 text-muted-foreground" strokeWidth={1.5} />
        <span className="text-base font-medium text-foreground">{label}</span>
        <span className="text-sm text-muted-foreground">
          O haz clic para seleccionar
        </span>
      </button>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        className="hidden"
        // Limpiamos el value para poder re-seleccionar el mismo fichero tras quitarlo.
        onChange={(e) => {
          addFiles(e.target.files);
          e.target.value = "";
        }}
      />

      {value.length > 0 && (
        <ul className="flex flex-col gap-2">
          {value.map((file, index) => (
            <li
              key={`${file.name}:${file.size}`}
              className="flex items-center justify-between gap-3 rounded-xl border border-input bg-input/30 px-3 py-2"
            >
              <div className="flex min-w-0 items-center gap-2">
                <FileText className="size-4 shrink-0 text-muted-foreground" />
                <span className="truncate text-sm text-foreground">
                  {file.name}
                </span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatBytes(file.size)}
                </span>
              </div>
              <button
                type="button"
                onClick={() => removeAt(index)}
                disabled={disabled}
                aria-label={`Quitar ${file.name}`}
                className="shrink-0 rounded-full p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-50"
              >
                <X className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
