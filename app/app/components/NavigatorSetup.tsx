"use client";

import { useState } from "react";

export default function NavigatorSetup() {
    const [file, setFile] = useState<File | null>(null);
    const [sleepHours, setSleepHours] = useState<number | "">("");
    const [deadlines, setDeadlines] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [sessions, setSessions] = useState<any[] | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        const formData = new FormData();
        if (file) {
            formData.append("calendar", file);
        }
        formData.append("sleepHours", String(sleepHours));
        formData.append("deadlines", deadlines);

        try {
            const response = await fetch("http://localhost:8000/generate-plan", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Error: ${response.statusText}`);
            }

            const data = await response.json();
            setSessions(data.sessions || data);
        } catch (err: any) {
            setError(err.message || "Failed to generate plan");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-lg mx-auto bg-slate-900/80 backdrop-blur-md rounded-xl border border-slate-700 shadow-2xl p-6 text-white text-sm">
            <h2 className="text-xl font-bold mb-4 text-emerald-400 uppercase tracking-widest text-center">Navigator Setup</h2>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                <div className="flex flex-col gap-1">
                    <label className="font-semibold text-slate-300">Upload Calendar (.ics)</label>
                    <input
                        type="file"
                        accept=".ics"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                        className="w-full file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-emerald-500/20 file:text-emerald-400 hover:file:bg-emerald-500/30 bg-slate-800 p-2 rounded border border-slate-600 focus:outline-none focus:border-emerald-500"
                    />
                </div>

                <div className="flex flex-col gap-1">
                    <label className="font-semibold text-slate-300">Target Sleep (Hours)</label>
                    <input
                        type="number"
                        value={sleepHours}
                        onChange={(e) => setSleepHours(Number(e.target.value))}
                        placeholder="e.g. 7"
                        className="w-full bg-slate-800 border border-slate-600 rounded p-2 focus:outline-none focus:border-emerald-500"
                    />
                </div>

                <div className="flex flex-col gap-1">
                    <label className="font-semibold text-slate-300">Deadlines</label>
                    <textarea
                        value={deadlines}
                        onChange={(e) => setDeadlines(e.target.value)}
                        placeholder="List your impending tasks and deadlines..."
                        rows={4}
                        className="w-full bg-slate-800 border border-slate-600 rounded p-2 focus:outline-none focus:border-emerald-500 resize-none"
                    />
                </div>

                <button
                    type="submit"
                    disabled={loading}
                    className="w-full mt-2 py-3 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-900 font-bold uppercase tracking-wider rounded transition-colors"
                >
                    {loading ? "Generating..." : "Generate Focus Plan"}
                </button>
            </form>

            {error && (
                <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded text-red-200">
                    {error}
                </div>
            )}

            {sessions && (
                <div className="mt-6 border-t border-slate-700 pt-4">
                    <h3 className="font-bold text-emerald-400 mb-2 uppercase tracking-wide">Recommended Sessions</h3>
                    <ul className="flex flex-col gap-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
                        {Array.isArray(sessions) && sessions.length > 0 ? (
                            sessions.map((session, index) => (
                                <li key={index} className="p-3 bg-slate-800 rounded border border-slate-600 whitespace-pre-wrap font-mono text-xs text-slate-300">
                                    {JSON.stringify(session, null, 2)}
                                </li>
                            ))
                        ) : (
                            <li className="text-slate-400 italic">No recommendations received.</li>
                        )}
                    </ul>
                </div>
            )}
        </div>
    );
}
