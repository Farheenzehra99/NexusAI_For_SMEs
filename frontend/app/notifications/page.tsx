"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, CheckCircle2, AlertTriangle, Info, Clock, Check } from "lucide-react";
import Sidebar from "@/components/Sidebar";

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/notifications")
      .then(res => res.json())
      .then(data => {
        setNotifications(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const markAsRead = async (id: number) => {
    setNotifications(notifications.map(n => n.id === id ? { ...n, is_read: true } : n));
    await fetch(`http://localhost:8000/api/notifications/${id}/read`, { method: "POST" });
  };

  const markAllRead = async () => {
    const unreadIds = notifications.filter(n => !n.is_read).map(n => n.id);
    setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    for (const id of unreadIds) {
      await fetch(`http://localhost:8000/api/notifications/${id}/read`, { method: "POST" });
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case "alert": return <AlertTriangle className="text-rose-400" size={24} />;
      case "success": return <CheckCircle2 className="text-emerald-400" size={24} />;
      default: return <Info className="text-blue-400" size={24} />;
    }
  };

  const getBgClass = (type: string, isRead: boolean) => {
    if (isRead) return "bg-white/5 border-white/5";
    switch (type) {
      case "alert": return "bg-rose-500/10 border-rose-500/20";
      case "success": return "bg-emerald-500/10 border-emerald-500/20";
      default: return "bg-blue-500/10 border-blue-500/20";
    }
  };

  return (
    <Sidebar>
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="flex items-center justify-between mb-8">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <Bell className="text-emerald-400" size={32} />
              Notifications
            </h1>
            <p className="text-sm text-slate-400 mt-1">Stay updated with your AI workforce</p>
          </motion.div>

          <motion.button
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={markAllRead}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 text-slate-300 rounded-lg transition-colors border border-white/10 text-sm font-medium"
          >
            <Check size={16} />
            Mark all read
          </motion.button>
        </div>

        {loading ? (
          <div className="text-center text-slate-400 py-10">Loading notifications...</div>
        ) : (
          <div className="space-y-4">
            <AnimatePresence>
              {notifications.map((notif, idx) => (
                <motion.div
                  key={notif.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`group p-6 rounded-2xl border transition-all duration-300 backdrop-blur-sm flex items-start gap-5 ${getBgClass(notif.type, notif.is_read)}`}
                >
                  <div className="mt-1 p-3 rounded-full bg-black/20 shadow-inner">
                    {getIcon(notif.type)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                      <h3 className={`font-semibold text-lg truncate ${notif.is_read ? "text-slate-300" : "text-white"}`}>
                        {notif.title}
                      </h3>
                      <div className="flex items-center gap-1.5 text-xs text-slate-400 whitespace-nowrap bg-black/20 px-2.5 py-1 rounded-full">
                        <Clock size={12} />
                        {new Date(notif.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </div>
                    </div>
                    
                    <p className={`mt-2 text-sm leading-relaxed ${notif.is_read ? "text-slate-400" : "text-slate-300"}`}>
                      {notif.message}
                    </p>

                    {!notif.is_read && (
                      <div className="mt-4 flex gap-3">
                        <button 
                          onClick={() => markAsRead(notif.id)}
                          className="text-xs font-medium px-4 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30 transition-colors"
                        >
                          Mark as read
                        </button>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            
            {notifications.length === 0 && (
              <div className="text-center py-20 text-slate-500">
                <Bell size={48} className="mx-auto mb-4 opacity-20" />
                <p>No notifications yet.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </Sidebar>
  );
}
