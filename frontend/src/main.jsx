import React from "react";
import ReactDOM from "react-dom/client";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  FileText,
  History,
  Image as ImageIcon,
  Loader2,
  ShieldCheck,
  UploadCloud
} from "lucide-react";

import "./styles.css";

const API_BASE = "http://localhost:8000";

const FIELD_OPTIONS = [
  ["name", "Name"],
  ["dob", "Date of Birth"],
  ["address", "Address"],
  ["phone", "Phone Number"],
  ["email", "Email Address"],
  ["aadhaar", "Aadhaar Number"],
  ["pan", "PAN Number"]
];

function riskColor(level) {
  if (level === "High") return "border-red-200 bg-red-50 text-red-700";
  if (level === "Medium") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

function App() {
  const [file, setFile] = React.useState(null);
  const [extraction, setExtraction] = React.useState(null);
  const [selectedFields, setSelectedFields] = React.useState([]);
  const [redaction, setRedaction] = React.useState(null);
  const [history, setHistory] = React.useState([]);
  const [showHistory, setShowHistory] = React.useState(false);  
  const [loading, setLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    try {
      const response = await fetch(`${API_BASE}/history`);
      const data = await response.json();
      setHistory(data.history || []);
    } catch {
      setHistory([]);
    }
  }

  async function handleExtract(event) {
    event.preventDefault();
    if (!file) {
      setError("Please choose a PDF, PNG, JPG, JPEG, CSV, or XLSX file.");
      return;
    }

    setLoading(true);
    setError("");
    setExtraction(null);
    setRedaction(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/extract`, {
        method: "POST",
        body: formData
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Extraction failed.");

      setExtraction(data);
      const detectedKeys = new Set(data.attributes.map((item) => item.key));
      setSelectedFields(FIELD_OPTIONS.map(([key]) => key).filter((key) => detectedKeys.has(key)));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function applyPreferences(nextFields = selectedFields) {
    if (!extraction) return;
    setSaving(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/redact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: extraction.filename,
          original_text: extraction.original_text,
          attributes: extraction.attributes,
          selected_fields: nextFields,
          photo_detected: extraction.photo_detected,
          source_type: extraction.source_type,
          table_rows: extraction.table_rows
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Redaction failed.");
      setRedaction(data);
      loadHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function toggleField(key) {
    const next = selectedFields.includes(key)
      ? selectedFields.filter((item) => item !== key)
      : [...selectedFields, key];
    setSelectedFields(next);
  }

  function downloadRedactedText() {
    const output = redaction?.export_text || redaction?.redacted_text;
    if (!output) return;
    const extension = redaction?.export_extension || "txt";
    const mime = extension === "csv" ? "text/csv;charset=utf-8" : "text/plain;charset=utf-8";
    const blob = new Blob([output], { type: mime });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `docshield-personalized-redacted.${extension}`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const rows = redaction?.attribute_rows || extraction?.attributes || [];
  const outputText = redaction?.export_text || redaction?.redacted_text;

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-lg bg-slate-950 text-white">
              <ShieldCheck size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold">DocShield AI</h1>
              <p className="text-sm text-slate-500">Personalized Privacy Protection System</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1 text-sm text-slate-600">
            <CheckCircle2 size={16} />
            Rule-based OCR privacy MVP
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[340px_1fr]">
        <aside className="space-y-6">
          <Panel title="Upload Document" icon={<UploadCloud size={18} />}>
            <form onSubmit={handleExtract}>
              <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-9 text-center hover:border-slate-500">
                <UploadCloud className="mb-3 text-slate-500" size={34} />
                <span className="max-w-full truncate font-semibold">{file ? file.name : "Choose document"}</span>
                <span className="mt-1 text-sm text-slate-500">PDF, PNG, JPG, JPEG, CSV, XLSX</span>
                <input
                  type="file"
                  className="hidden"
                  accept=".pdf,.png,.jpg,.jpeg,.csv,.xlsx"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                />
              </label>
              <button
                type="submit"
                disabled={loading}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-3 font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {loading ? <Loader2 className="animate-spin" size={18} /> : <FileText size={18} />}
                {loading ? "Extracting..." : "Extract Attributes"}
              </button>
            </form>
            {error && (
              <div className="mt-4 flex gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <AlertTriangle size={18} />
                <span>{error}</span>
              </div>
            )}
          </Panel>

          <Panel title="Sensitive Field Selection" icon={<ShieldCheck size={18} />}>
            <div className="space-y-3">
              {FIELD_OPTIONS.map(([key, label]) => {
                const available = extraction?.attributes?.some((item) => item.key === key);
                return (
                  <label
                    key={key}
                    className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                      available ? "border-slate-200 bg-white" : "border-slate-100 bg-slate-50 text-slate-400"
                    }`}
                  >
                    <span>{label}</span>
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-slate-950"
                      checked={selectedFields.includes(key)}
                      disabled={!available}
                      onChange={() => toggleField(key)}
                    />
                  </label>
                );
              })}
            </div>
            <button
              type="button"
              disabled={!extraction || saving}
              onClick={() => applyPreferences()}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-teal-700 px-4 py-3 font-semibold text-white hover:bg-teal-600 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {saving ? <Loader2 className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
              {saving ? "Applying..." : "Apply Privacy Choices"}
            </button>
          </Panel>
        </aside>

        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            <Metric label="Attributes" value={extraction?.attributes?.length || 0} />
            <Metric label="Selected Fields" value={selectedFields.length} />
            <Metric label="Risk Score" value={`${redaction?.risk_score ?? 0}/100`} />
            <div className={`rounded-lg border p-5 shadow-sm ${riskColor(redaction?.risk_level || "Low")}`}>
              <p className="text-sm opacity-80">Risk Level</p>
              <p className="mt-2 text-3xl font-bold">{redaction?.risk_level || "Low"}</p>
            </div>
          </div>

          <Panel title="Risk Analysis" icon={<AlertTriangle size={18} />}>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-sm text-slate-500">Selected Sensitive Fields</p>
                <p className="mt-2 font-semibold">
                  {selectedFields.length
                    ? selectedFields.map((key) => FIELD_OPTIONS.find(([value]) => value === key)?.[1]).join(", ")
                    : "None selected"}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="flex items-center gap-2 text-sm text-slate-500">
                  <ImageIcon size={16} />
                  Photo Detected
                </p>
                <p className="mt-2 font-semibold">{extraction?.photo_detected ? "Yes" : "No"}</p>
              </div>
            </div>
          </Panel>

          <Panel title="Extracted Attributes" icon={<FileText size={18} />}>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="bg-slate-100 text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Attribute</th>
                    <th className="px-3 py-2">Value</th>
                    <th className="px-3 py-2">Sensitive</th>
                    <th className="px-3 py-2">Masked Value</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((item) => {
                    const sensitive = redaction ? item.sensitive : selectedFields.includes(item.key);
                    const masked = redaction ? item.masked_value : item.value;
                    return (
                      <tr key={`${item.key}-${item.start}-${item.value}`} className="border-t border-slate-100">
                        <td className="px-3 py-2 font-semibold">{item.label}</td>
                        <td className="px-3 py-2">{item.value}</td>
                        <td className="px-3 py-2">{sensitive ? "Yes" : "No"}</td>
                        <td className="px-3 py-2">{masked}</td>
                      </tr>
                    );
                  })}
                  {rows.length === 0 && (
                    <tr>
                      <td className="px-3 py-5 text-center text-slate-500" colSpan="4">
                        Upload a document to extract personal attributes.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Panel>

          <div className="grid gap-6 xl:grid-cols-2">
            <TextPanel title="Original OCR Text" text={extraction?.original_text} />
            <Panel title="Redacted Output" icon={<Download size={18} />}>
              <button
                type="button"
                disabled={!outputText}
                onClick={downloadRedactedText}
                className="mb-3 flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
              >
                <Download size={16} />
                Download {redaction?.export_extension?.toUpperCase() || "TXT"}
              </button>
              <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm leading-6 text-slate-100">
                {outputText || "Apply privacy choices to generate safe output."}
              </pre>
            </Panel>
          </div>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">

  <div
    className="mb-4 flex cursor-pointer items-center justify-between"
    onClick={() => setShowHistory(!showHistory)}
  >
    <div className="flex items-center gap-2">
      <History size={18} />
      <h2 className="text-lg font-bold">Scan History</h2>
    </div>
     {showHistory ? (
       <ChevronUp size={20} className="text-slate-600" />
   ) : (
     <ChevronDown size={20} className="text-slate-600" />
)}
    
  </div>

  {showHistory && (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-left text-sm">
        <thead className="bg-slate-100 text-slate-600">
          <tr>
            <th className="px-3 py-2">File</th>
            <th className="px-3 py-2">Attributes</th>
            <th className="px-3 py-2">Selected Fields</th>
            <th className="px-3 py-2">Risk</th>
            <th className="px-3 py-2">Time</th>
          </tr>
        </thead>

        <tbody>
          {history.map((scan) => (
            <tr key={scan.id} className="border-t border-slate-100">
              <td className="px-3 py-2 font-semibold">
                {scan.filename}
              </td>

              <td className="px-3 py-2">
                {scan.attributes.map((item) => item.label).join(", ") || "None"}
              </td>

              <td className="px-3 py-2">
                {scan.selected_fields.join(", ") || "None"}
              </td>

              <td className="px-3 py-2">
                {scan.risk_score}/100 {scan.risk_level}
              </td>

              <td className="px-3 py-2">
                {scan.created_at}
              </td>
            </tr>
          ))}

          {history.length === 0 && (
            <tr>
              <td
                className="px-3 py-5 text-center text-slate-500"
                colSpan="5"
              >
                No scans saved yet.
              </td>
            </tr>
          )}
        </tbody>

      </table>
    </div>
  )}

</section>
        </div>
      </section>
    </main>
  );
}

function Panel({ title, icon, children }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <span className="text-slate-500">{icon}</span>
        <h2 className="text-lg font-bold">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-bold">{value}</p>
    </div>
  );
}

function TextPanel({ title, text }) {
  return (
    <Panel title={title} icon={<FileText size={18} />}>
      <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm leading-6 text-slate-100">
        {text || "No text found yet."}
      </pre>
    </Panel>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
