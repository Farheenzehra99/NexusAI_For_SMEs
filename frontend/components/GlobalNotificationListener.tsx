"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, X } from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";

export default function GlobalNotificationListener() {
  const [liveNotification, setLiveNotification] = useState<any>(null);
  const { t } = useLanguage();

  useEffect(() => {
    // Connect to SSE stream
    const evtSource = new EventSource("http://localhost:8000/api/notifications/stream");
    
    evtSource.addEventListener("notification", (event) => {
      try {
        // Data format received is JSON encoded in a string
        // The backend emits Python dict str, we need to handle that or 
        // properly format it. Assuming backend sends valid JSON:
        let strData = event.data.replace(/'/g, '"');
        // Simple heuristic to fix python boolean string reps to json
        strData = strData.replace(/True/g, 'true').replace(/False/g, 'false');
        
        const data = JSON.parse(strData);
        setLiveNotification(data);
        
        // Play sound
        const audio = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
        audio.play().catch(e => console.log("Audio play blocked by browser:", e));

        // Auto-hide after 5 seconds
        setTimeout(() => {
          setLiveNotification(null);
        }, 5000);
      } catch (err) {
        console.error("Error parsing notification stream data", err);
      }
    });

    evtSource.onerror = (err) => {
      console.error("SSE Error", err);
    };

    return () => {
      evtSource.close();
    };
  }, []);

  return (
    <AnimatePresence>
      {liveNotification && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.9 }}
          className="fixed bottom-6 right-6 z-50 max-w-sm w-full bg-[#0e1522]/90 backdrop-blur-xl border border-emerald-500/30 rounded-2xl p-4 shadow-[0_10px_40px_rgba(16,185,129,0.2)]"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-400 flex-shrink-0">
              <Bell size={20} className="animate-pulse" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-white">{liveNotification.title}</h4>
              <p className="text-xs text-slate-400 mt-1 line-clamp-2">{liveNotification.message}</p>
            </div>
            <button 
              onClick={() => setLiveNotification(null)}
              className="p-1 text-slate-500 hover:text-white transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
