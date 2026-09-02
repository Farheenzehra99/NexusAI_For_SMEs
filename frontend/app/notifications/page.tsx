"use client";

import { motion } from "framer-motion";
import { Bell, CheckCircle2, AlertCircle, Info, Clock, Trash2 } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { useState } from "react";

const initialNotifications = [
  { id: 1, type: "alert", title: "Critical Inventory Alert", message: "Embroidered Kurti White (AG-KT-001) stock is down to 5 units.", time: "10 mins ago", unread: true },
  { id: 2, type: "info", title: "Marketing Campaign Paused", message: "Khan Fabrics Counter campaign was automatically paused by the Marketing Agent due to low ROI.", time: "1 hour ago", unread: true },
  { id: 3, type: "success", title: "Weekly Report Generated", message: "Your customized business health report for week 34 is ready.", time: "3 hours ago", unread: false },
  { id: 4, type: "alert", title: "Surge in Delivery Complaints", message: "Support Agent detected a 200% increase in courier complaints.", time: "5 hours ago", unread: false },
  { id: 5, type: "info", title: "System Update", message: "NexusAI core models have been updated to the latest version.", time: "1 day ago", unread: false },
];

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  show: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState(initialNotifications);

  const removeNotification = (id: number) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const markAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, unread: false })));
  };

  return (
    <Sidebar>
      <div className="max-w-4xl mx-auto space-y-8">
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white">Notifications</h1>
            <p className="text-sm text-slate-400 mt-1">Stay updated with your AI Workforce</p>
          </div>
          <motion.button 
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={markAllRead}
            className="px-4 py-2 bg-white/5 hover:bg-white/10 text-sm font-medium rounded-xl transition-colors border border-white/5"
          >
            Mark all as read
          </motion.button>
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="space-y-4"
        >
          {notifications.map((n) => (
            <motion.div 
              key={n.id}
              variants={itemVariants}
              layout
              className={`relative p-5 rounded-2xl border backdrop-blur-md overflow-hidden group ${n.unread ? 'bg-[#152033]/80 border-emerald-500/20' : 'bg-[#0e1522]/60 border-white/5'}`}
            >
              {n.unread && <div className="absolute top-0 left-0 bottom-0 w-1 bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)]" />}
              
              <div className="flex items-start gap-4">
                <div className={`p-2 rounded-xl flex-shrink-0 ${n.type === 'alert' ? 'bg-red-500/10 text-red-400' : n.type === 'success' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>
                  {n.type === 'alert' ? <AlertCircle size={20} /> : n.type === 'success' ? <CheckCircle2 size={20} /> : <Info size={20} />}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-4">
                    <h3 className={`text-base font-semibold ${n.unread ? 'text-white' : 'text-slate-300'}`}>{n.title}</h3>
                    <span className="text-xs text-slate-500 flex items-center gap-1 flex-shrink-0">
                      <Clock size={12} /> {n.time}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400 mt-1">{n.message}</p>
                </div>

                <motion.button
                  whileHover={{ scale: 1.1, color: "#ef4444" }}
                  whileTap={{ scale: 0.9 }}
                  onClick={() => removeNotification(n.id)}
                  className="p-2 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                >
                  <Trash2 size={16} />
                </motion.button>
              </div>
            </motion.div>
          ))}
          
          {notifications.length === 0 && (
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }}
              className="py-20 text-center text-slate-500"
            >
              <Bell size={48} className="mx-auto mb-4 opacity-20" />
              <p>You&apos;re all caught up!</p>
            </motion.div>
          )}
        </motion.div>
      </div>
    </Sidebar>
  );
}
