import { useState } from 'react';
import { uploadPdf } from '../services/api';

export default function UploadPanel({ onSessionReady }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setStatus('Uploading and parsing document...');

    try {
      const data = await uploadPdf(file);
      setStatus(data.status);
      onSessionReady(data.session_id, data.filename);
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const isError = status.startsWith('Error');

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 h-fit">
      <h1 className="text-2xl font-bold text-slate-800 mb-6">PhantomVault</h1>

      <form onSubmit={handleUpload} className="flex flex-col gap-4">
        <label className="text-sm font-semibold text-slate-600">1. Upload Document</label>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => { setFile(e.target.files[0]); setStatus(''); }}
          className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
        <button
          type="submit"
          disabled={!file || isUploading}
          className="bg-blue-600 text-white py-2 px-4 rounded-md font-medium hover:bg-blue-700 transition-colors disabled:bg-slate-300"
        >
          {isUploading ? 'Processing…' : 'Process PDF'}
        </button>
        {status && (
          <p className={`text-sm font-medium ${isError ? 'text-red-600' : 'text-emerald-600'}`}>
            {status}
          </p>
        )}
      </form>
    </div>
  );
}
