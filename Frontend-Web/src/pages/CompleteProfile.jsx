import { useState } from "react";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist/legacy/build/pdf.mjs";
import pdfWorkerUrl from "pdfjs-dist/legacy/build/pdf.worker.mjs?url";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { TrendingUp } from "lucide-react";

GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

async function extractPdfText(file, onProgress) {
  const buffer = await file.arrayBuffer();
  const loadingTask = getDocument({ data: new Uint8Array(buffer) });
  const pdf = await loadingTask.promise;
  const totalPages = pdf.numPages || 0;
  const pages = [];

  for (let pageNumber = 1; pageNumber <= totalPages; pageNumber += 1) {
    const page = await pdf.getPage(pageNumber);
    const content = await page.getTextContent();
    const pageText = content.items
      .map((item) => (item && typeof item.str === "string" ? item.str : ""))
      .join(" ")
      .trim();

    if (pageText) pages.push(pageText);

    if (typeof onProgress === "function" && totalPages > 0) {
      const progress = 20 + (pageNumber / totalPages) * 65;
      onProgress(Math.min(progress, 85));
    }
  }

  if (typeof pdf.destroy === "function") {
    await pdf.destroy();
  }

  return pages.join("\n").trim();
}

export default function CompleteProfile() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);

  const [file, setFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isAutoFilled, setIsAutoFilled] = useState(false);
  const [uploadSummary, setUploadSummary] = useState(null);

  const createEmpty = () => ({ name: "", amount: "", type: "fixed" });

  const [income, setIncome] = useState([createEmpty()]);
  const [expenses, setExpenses] = useState([createEmpty()]);
  const [savings, setSavings] = useState([createEmpty()]);
  const [liabilities, setLiabilities] = useState([]);

  // ================= DYNAMIC =================

  const addField = (setter, data) => {
    setter([...data, createEmpty()]);
  };

  const updateField = (i, field, value, data, setter) => {
    const updated = [...data];
    updated[i][field] = value;
    setter(updated);
  };

  // ================= VALIDATION =================

  const validate = () => {
    if (isAutoFilled) return true;

    if (!income.length) return alert("Add at least 1 income");
    if (!expenses.length) return alert("Add at least 1 expense");
    if (!savings.length) return alert("Add at least 1 saving");

    return true;
  };

  // ================= PDF HANDLER =================

  const handleFileUpload = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    if (
      selectedFile.type !== "application/pdf" &&
      !selectedFile.name.toLowerCase().endsWith(".pdf")
    ) {
      alert("Please upload a PDF bank statement.");
      e.target.value = "";
      return;
    }

    setFile(selectedFile);
    setProcessing(true);
    setProgress(10);
    setIsAutoFilled(false);
    setUploadSummary(null);

    try {
      setProgress(20);
      const statementText = await extractPdfText(selectedFile, setProgress);

      if (!statementText) {
        throw new Error(
          "No readable text was found in the PDF. If it is scanned, try a text-based bank statement."
        );
      }

      setProgress(90);

      const formData = new FormData();
      formData.append("document_type", "bank_statement");
      formData.append("statement_text", statementText);
      formData.append("source_filename", selectedFile.name);

      const res = await api.post("/documents/upload", formData);

      const payload = res.data || {};
      const responseData = payload.income ? payload : payload.data || payload;

      const normalizeItems = (items, fallbackType = "fixed") =>
        Array.isArray(items)
          ? items
              .filter((item) => item && item.name)
              .map((item) => ({
                name: item.name || "",
                amount: item.amount ?? "",
                type: item.type || fallbackType,
              }))
          : [];

      const extractedIncome = normalizeItems(responseData.income, "fixed");
      const extractedExpenses = normalizeItems(responseData.expenses, "variable");
      const extractedSavings = normalizeItems(responseData.savings, "fixed");
      const extractedLiabilities = normalizeItems(responseData.liabilities, "fixed");

      const hasStructuredData =
        extractedIncome.length ||
        extractedExpenses.length ||
        extractedSavings.length ||
        extractedLiabilities.length;

      if (hasStructuredData) {
        setIncome(extractedIncome);
        setExpenses(extractedExpenses);
        setSavings(extractedSavings);
        setLiabilities(extractedLiabilities);
        setUploadSummary(responseData.summary || null);
        setIsAutoFilled(true);
      } else {
        setUploadSummary(null);
        alert(
          payload.message ||
            "The backend accepted the statement text, but it did not return structured financial data."
        );
      }

      setProgress(100);

      setTimeout(() => {
        setProcessing(false);
      }, 500);

    } catch (err) {
      console.error("PDF ERROR:", err);
      alert(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          "Failed to process bank statement"
      );
      setProgress(0);
      setProcessing(false);
    }
  };

  // ================= SUBMIT =================

  const handleSubmit = async () => {
    if (!validate()) return;

    setLoading(true);

    try {
      const clean = (arr) =>
        arr
          .filter((i) => i.name && i.amount)
          .map((i) => ({
            name: i.name,
            amount: Number(i.amount),
            type: i.type,
          }));

      const payload = {
        income: clean(income),
        expenses: clean(expenses),
        savings: clean(savings),
        liabilities: clean(liabilities),
      };

      console.log("FINAL PAYLOAD:", payload);

      await api.post("/finance/submit", payload);

      navigate("/dashboard");

    } catch (err) {
      console.error("Submit Error:", err);

      if (err.response?.status === 401) {
        alert("Session expired");
        navigate("/login");
      } else {
        alert(err.response?.data?.detail || "Failed to save data");
      }

    } finally {
      setLoading(false);
    }
  };

  // ================= UI =================

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">

      {/* PROCESSING OVERLAY */}
      {processing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl w-[300px] text-center">
            <h3 className="font-semibold mb-2">Converting PDF to text...</h3>

            <div className="w-full bg-gray-200 h-2 rounded">
              <div
                className="bg-blue-600 h-2 rounded transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>

            <p className="text-sm mt-2">{Math.round(progress)}%</p>
            <p className="text-xs text-gray-500 mt-2">
              Conversion happens in your browser before upload.
            </p>
          </div>
        </div>
      )}

      <div className="w-full max-w-3xl">

        {/* LOGO */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="size-12 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
            <TrendingUp className="text-white size-6" />
          </div>
          <span className="text-2xl font-bold">FinArmor</span>
        </div>

        {/* CARD */}
        <div className="bg-white rounded-3xl shadow-xl p-8">

          <h2 className="text-2xl font-bold text-center mb-2">
            Upload or Enter Financial Data
          </h2>

          <p className="text-gray-500 text-center mb-6">
            Upload your bank statement OR enter manually
          </p>

          {/* FILE */}
          <div className="mb-6">
            <label className="text-sm text-gray-500">
              Upload Bank Statement
            </label>

            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileUpload}
              className="mt-2"
            />

            {file && (
              <p className="text-xs text-gray-400 mt-2">
                Selected file: {file.name}
              </p>
            )}

            {uploadSummary && (
              <div className="mt-3 rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-700">
                Extracted {uploadSummary.transactions || 0} transactions across{" "}
                {uploadSummary.months || 0} months.
              </div>
            )}

            {isAutoFilled && (
              <p className="text-green-600 text-sm mt-2">
                Data extracted. Please verify below.
              </p>
            )}
          </div>

          {/* SECTIONS */}
          <Section title="Income" data={income} setData={setIncome} addField={addField} updateField={updateField} />
          <Section title="Expenses" data={expenses} setData={setExpenses} addField={addField} updateField={updateField} />
          <Section title="Savings" data={savings} setData={setSavings} addField={addField} updateField={updateField} />
          <Section title="Liabilities" data={liabilities} setData={setLiabilities} addField={addField} updateField={updateField} />

          <button onClick={handleSubmit} className="btn mt-6 w-full">
            {loading ? "Saving..." : "Finish"}
          </button>

        </div>
      </div>
    </div>
  );
}

// ================= COMPONENTS =================

function Section({ title, data, setData, addField, updateField }) {
  return (
    <div className="mb-4">
      <div className="flex justify-between mb-2">
        <h3 className="font-semibold">{title}</h3>
        <button onClick={() => addField(setData, data)} className="text-blue-600 text-sm">
          + Add
        </button>
      </div>

      {data.map((item, i) => (
        <div key={i} className="grid grid-cols-3 gap-2 mb-2">
          <input
            placeholder="Name"
            value={item.name}
            onChange={(e) => updateField(i, "name", e.target.value, data, setData)}
            className="input"
          />
          <input
            type="number"
            placeholder="Amount"
            value={item.amount}
            onChange={(e) => updateField(i, "amount", e.target.value, data, setData)}
            className="input"
          />
          <select
            value={item.type}
            onChange={(e) => updateField(i, "type", e.target.value, data, setData)}
            className="input"
          >
            <option value="fixed">Fixed</option>
            <option value="variable">Variable</option>
          </select>
        </div>
      ))}
    </div>
  );
}
