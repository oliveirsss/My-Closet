import { Shirt } from "lucide-react";

export function LoadingScreen() {
    return (
        <div className="fixed inset-0 bg-white z-[9999] flex flex-col items-center justify-center">
            <div className="relative flex flex-col items-center">
                {/* Logo wrapper with subtle pulse */}
                <div className="relative mb-8">
                    <div className="absolute inset-0 bg-emerald-100/50 rounded-full animate-[ping_3s_ease-in-out_infinite]"></div>
                    <div className="absolute inset-0 bg-emerald-50 rounded-full animate-[ping_2s_ease-in-out_infinite] delay-150"></div>
                    <div className="relative bg-white p-6 rounded-full shadow-xl border border-stone-50 z-10">
                        <Shirt className="w-12 h-12 text-emerald-600 animate-[pulse_3s_ease-in-out_infinite]" strokeWidth={1.5} />
                    </div>
                </div>

                {/* Typography */}
                <div className="space-y-3 text-center animate-in fade-in duration-700 slide-in-from-bottom-4">
                    <h1 className="text-2xl font-light tracking-[0.2em] text-stone-900 uppercase">
                        My Closet
                    </h1>
                    <div className="h-0.5 w-12 bg-emerald-500 mx-auto rounded-full opacity-50"></div>
                    <p className="text-xs font-medium text-stone-400 tracking-widest uppercase animate-pulse">
                        A organizar o teu estilo...
                    </p>
                </div>
            </div>
        </div>
    );
}
