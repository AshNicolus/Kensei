import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { FileUp, Loader2, Upload } from "lucide-react";
import { cn } from "@/shared/lib/utils";

interface DropzoneProps {
  onFile: (file: File) => void;
  uploading?: boolean;
  uploadProgress?: number;
  accept?: Record<string, string[]>;
  maxSizeMb?: number;
}

export function Dropzone({
  onFile,
  uploading,
  uploadProgress,
  accept = { "text/csv": [".csv"] },
  maxSizeMb = 200,
}: DropzoneProps) {
  const onDrop = useCallback(
    (files: File[]) => {
      if (files[0]) onFile(files[0]);
    },
    [onFile]
  );
  const { getRootProps, getInputProps, isDragActive, fileRejections } =
    useDropzone({
      onDrop,
      accept,
      maxFiles: 1,
      maxSize: maxSizeMb * 1024 * 1024,
      disabled: uploading,
    });

  return (
    <div>
      <div
        {...getRootProps()}
        className={cn(
          "border border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer select-none",
          isDragActive
            ? "border-primary/60 bg-primary/5"
            : "border-border hover:border-primary/40 hover:bg-accent/30",
          uploading && "pointer-events-none opacity-70"
        )}
      >
        <input {...getInputProps()} />
        <div className="grid place-items-center gap-3">
          <div className="size-12 rounded-full bg-primary/10 grid place-items-center">
            {uploading ? (
              <Loader2 className="size-5 text-primary animate-spin" />
            ) : isDragActive ? (
              <FileUp className="size-5 text-primary" />
            ) : (
              <Upload className="size-5 text-primary" />
            )}
          </div>
          {uploading ? (
            <div className="space-y-2 w-full max-w-xs">
              <p className="text-sm">Uploading…</p>
              {uploadProgress !== undefined && (
                <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${Math.round(uploadProgress * 100)}%` }}
                  />
                </div>
              )}
            </div>
          ) : (
            <>
              <div>
                <p className="text-sm font-medium">
                  {isDragActive
                    ? "Drop your CSV"
                    : "Drop a CSV here or click to browse"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Up to {maxSizeMb} MB · CSV only for now
                </p>
              </div>
            </>
          )}
        </div>
      </div>
      {fileRejections.length > 0 && (
        <p className="text-xs text-destructive mt-2">
          {fileRejections[0].errors[0].message}
        </p>
      )}
    </div>
  );
}
