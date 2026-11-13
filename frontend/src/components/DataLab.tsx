import { useEffect, useState, type ChangeEvent } from "react";
import { AlertCircle, CheckCircle2, Download, FileUp, LoaderCircle } from "lucide-react";
import {
  apiClient,
  getApiError,
  type GeneratedDatasetFile,
  type GeneratedDatasetInfo,
} from "../services/api";
import { validateDatasetPreview, type DatasetPreview } from "../services/datasetPreview";

interface LocalPreview extends DatasetPreview {
  filename: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function categoryLabel(category: GeneratedDatasetFile["category"]): string {
  switch (category) {
    case "input_data":
      return "Input data";
    case "evaluation_labels":
      return "Evaluation labels · separate";
    case "database_seed":
      return "SQL seed";
    case "documentation":
      return "Documentation";
  }
}

export function DataLab() {
  const [dataset, setDataset] = useState<GeneratedDatasetInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [preview, setPreview] = useState<LocalPreview | null>(null);

  useEffect(() => {
    let active = true;
    apiClient.getGeneratedDatasetInfo()
      .then((result) => {
        if (active) setDataset(result);
      })
      .catch((error: unknown) => {
        if (active) setLoadError(getApiError(error));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const downloadFile = async (filename: string) => {
    setDownloading(filename);
    setDownloadError(null);
    try {
      const blob = await apiClient.downloadGeneratedDatasetFile(filename);
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (error) {
      setDownloadError(`${filename}: ${getApiError(error)}`);
    } finally {
      setDownloading(null);
    }
  };

  const previewFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    setPreview(null);
    if (!file.name.toLowerCase().endsWith(".json")) {
      setPreview({
        filename: file.name,
        rowCounts: {},
        totalRows: 0,
        errors: ["Choose the generated data.json file. CSV, SQL, and ground-truth files are not input datasets."],
      });
      input.value = "";
      return;
    }
    try {
      const contents: unknown = JSON.parse(await file.text());
      setPreview({ filename: file.name, ...validateDatasetPreview(contents) });
    } catch (error) {
      setPreview({
        filename: file.name,
        rowCounts: {},
        totalRows: 0,
        errors: [error instanceof Error ? `Could not read JSON: ${error.message}` : "Could not read the selected JSON file."],
      });
    } finally {
      input.value = "";
    }
  };

  const inputFiles = dataset?.files.filter((file) => file.category === "input_data") ?? [];
  const evaluationFiles = dataset?.files.filter((file) => file.category === "evaluation_labels") ?? [];
  const otherFiles = dataset?.files.filter(
    (file) => file.category !== "input_data" && file.category !== "evaluation_labels",
  ) ?? [];

  return (
    <section className="data-lab">
      <div className="data-lab-intro">
        <p className="eyebrow">Synthetic dataset</p>
        <h2>Export and inspect generated records</h2>
        <p>
          Download the generated files or preview <code>data.json</code> in this browser.
          Preview checks structure and relationships; it never uploads records or writes to a database.
        </p>
      </div>

      <section className="data-card">
        <div className="data-card-heading">
          <div>
            <h3>Generated dataset exports</h3>
            <p>Source records are available as JSON and per-entity CSV files.</p>
          </div>
          {dataset && (
            <span className={`dataset-status ${dataset.status === "FAILED" ? "dataset-status-error" : ""}`}>
              {dataset.status.replaceAll("_", " ")}
            </span>
          )}
        </div>
        {loading && <p className="data-message"><LoaderCircle className="spin" size={16} /> Loading generated files…</p>}
        {loadError && <div className="error-box" role="alert">{loadError}</div>}
        {!loading && !loadError && inputFiles.length === 0 && (
          <p className="muted">No generated files found. Run the synthetic data generator in the backend first.</p>
        )}
        {dataset && Object.keys(dataset.row_counts).length > 0 && (
          <div className="preview-counts generated-counts">
            {Object.entries(dataset.row_counts).map(([table, count]) => (
              <span key={table}><strong>{count.toLocaleString()}</strong>{table.replaceAll("_", " ")}</span>
            ))}
          </div>
        )}
        {inputFiles.length > 0 && (
          <div className="data-file-list">
            {inputFiles.map((file) => (
              <div className="data-file-row" key={file.filename}>
                <div>
                  <strong>{file.filename}</strong>
                  <small>{categoryLabel(file.category)} · {formatBytes(file.size_bytes)}</small>
                </div>
                <button
                  className="button button-secondary"
                  disabled={downloading !== null}
                  onClick={() => void downloadFile(file.filename)}
                  type="button"
                >
                  {downloading === file.filename
                    ? <LoaderCircle className="spin" size={15} />
                    : <Download size={15} />}
                  Download
                </button>
              </div>
            ))}
          </div>
        )}
        {otherFiles.length > 0 && (
          <details className="data-extra-files">
            <summary>SQL seed and documentation ({otherFiles.length})</summary>
            <div className="data-file-list">
              {otherFiles.map((file) => (
                <div className="data-file-row" key={file.filename}>
                  <div>
                    <strong>{file.filename}</strong>
                    <small>{categoryLabel(file.category)} · {formatBytes(file.size_bytes)}</small>
                  </div>
                  <button
                    className="button button-secondary"
                    disabled={downloading !== null}
                    onClick={() => void downloadFile(file.filename)}
                    type="button"
                  >
                    {downloading === file.filename
                      ? <LoaderCircle className="spin" size={15} />
                      : <Download size={15} />}
                    Download
                  </button>
                </div>
              ))}
            </div>
          </details>
        )}
        {evaluationFiles.length > 0 && (
          <details className="data-extra-files evaluation-files">
            <summary>Ground-truth evaluation labels ({evaluationFiles.length})</summary>
            <p className="muted">
              Keep these separate from model or workflow inputs. They contain expected labels for evaluation.
            </p>
            <div className="data-file-list">
              {evaluationFiles.map((file) => (
                <div className="data-file-row" key={file.filename}>
                  <div>
                    <strong>{file.filename}</strong>
                    <small>{categoryLabel(file.category)} · {formatBytes(file.size_bytes)}</small>
                  </div>
                  <button
                    className="button button-secondary"
                    disabled={downloading !== null}
                    onClick={() => void downloadFile(file.filename)}
                    type="button"
                  >
                    {downloading === file.filename
                      ? <LoaderCircle className="spin" size={15} />
                      : <Download size={15} />}
                    Download
                  </button>
                </div>
              ))}
            </div>
          </details>
        )}
        {downloadError && <div className="error-box inline-error" role="alert">{downloadError}</div>}
      </section>

      <section className="data-card">
        <div className="data-card-heading">
          <div>
            <h3>Local import preview</h3>
            <p>Select the generated JSON to inspect row counts and foreign-key integrity.</p>
          </div>
          <FileUp aria-hidden="true" size={21} />
        </div>
        <label className="button button-primary file-picker">
          <FileUp size={16} /> Choose data.json
          <input accept=".json,application/json" onChange={(event) => void previewFile(event)} type="file" />
        </label>
        <p className="muted data-privacy-note">This is a browser-only preview. Nothing is sent to the backend or persisted.</p>
        {preview && (
          <div className="preview-result" aria-live="polite">
            <div className="preview-result-heading">
              {preview.errors.length === 0
                ? <CheckCircle2 aria-hidden="true" size={19} />
                : <AlertCircle aria-hidden="true" size={19} />}
              <div>
                <strong>{preview.filename}</strong>
                <small>
                  {preview.errors.length === 0
                    ? `${preview.totalRows.toLocaleString()} rows checked`
                    : `${preview.errors.length} issue${preview.errors.length === 1 ? "" : "s"} found`}
                </small>
              </div>
            </div>
            {Object.keys(preview.rowCounts).length > 0 && (
              <div className="preview-counts">
                {Object.entries(preview.rowCounts).map(([table, count]) => (
                  <span key={table}><strong>{count.toLocaleString()}</strong>{table.replaceAll("_", " ")}</span>
                ))}
              </div>
            )}
            {preview.errors.length > 0 ? (
              <ul className="preview-errors">
                {preview.errors.slice(0, 20).map((error) => <li key={error}>{error}</li>)}
                {preview.errors.length > 20 && <li>And {preview.errors.length - 20} more validation issues.</li>}
              </ul>
            ) : (
              <p className="preview-success">Required tables, unique primary keys, and foreign-key references look valid.</p>
            )}
          </div>
        )}
      </section>
    </section>
  );
}
