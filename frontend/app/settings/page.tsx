"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { User, Sliders, Key, Shield, Save } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { useLanguage } from "@/context/LanguageContext";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");
  const { language, setLanguage, t } = useLanguage();
  const [emailNotifs, setEmailNotifs] = useState(true);
  const [proactive, setProactive] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/api/settings")
      .then(res => res.json())
      .then(data => {
        setEmailNotifs(data.email_notifications);
        setProactive(data.proactive_actions);
      })
      .catch(err => console.error(err));
  }, []);

  const tabs = [
    { id: "profile", label: t("settings.profile"), icon: User },
    { id: "preferences", label: t("settings.preferences"), icon: Sliders },
    { id: "api", label: t("settings.api_keys"), icon: Key },
    { id: "security", label: t("settings.security"), icon: Shield },
  ];

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch("http://localhost:8000/api/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language,
          email_notifications: emailNotifs,
          proactive_actions: proactive
        })
      });
      // Simulate fake save delay for UI feel
      await new Promise(resolve => setTimeout(resolve, 600));
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sidebar>
      <div className="max-w-4xl mx-auto space-y-8">
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="text-3xl font-bold tracking-tight text-white">{t("settings.title")}</h1>
          <p className="text-sm text-slate-400 mt-1">{t("settings.subtitle")}</p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Tabs Sidebar */}
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="md:col-span-1 space-y-2"
          >
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors relative outline-none ${isActive ? "text-white" : "text-slate-400 hover:text-white hover:bg-white/5"}`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="settingsTab"
                      className="absolute inset-0 bg-white/10 rounded-xl border border-white/10"
                      transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    />
                  )}
                  <tab.icon size={18} className="relative z-10" />
                  <span className="relative z-10">{tab.label}</span>
                </button>
              );
            })}
          </motion.div>

          {/* Tab Content */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="md:col-span-3"
          >
            <div className="bg-[#0e1522]/60 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-xl min-h-[400px] flex flex-col">
              <div className="flex-1">
                <AnimatePresence mode="wait">
                  {activeTab === "profile" && (
                    <motion.div
                      key="profile"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.2 }}
                      className="space-y-6"
                    >
                      <h2 className="text-lg font-bold text-white mb-6">{t("settings.profile")} Settings</h2>
                      
                      <div className="grid gap-6">
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-slate-300">Full Name</label>
                          <input type="text" defaultValue="Ahmed Ali" className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
                        </div>
                        
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-slate-300">Email Address</label>
                          <input type="email" defaultValue="ahmed@aligarments.com" className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
                        </div>

                        <div className="space-y-2">
                          <label className="text-sm font-medium text-slate-300">Company Name</label>
                          <input type="text" defaultValue="Ali Garments" className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {activeTab === "preferences" && (
                    <motion.div
                      key="preferences"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.2 }}
                    >
                      <h2 className="text-lg font-bold text-white mb-6">{t("settings.preferences")}</h2>
                      
                      <div className="space-y-6">
                        <div className="space-y-3">
                          <label className="text-sm font-medium text-slate-300">{t("settings.language")}</label>
                          <p className="text-xs text-slate-400">{t("settings.language_desc")}</p>
                          <select 
                            value={language}
                            onChange={(e) => setLanguage(e.target.value as any)}
                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all appearance-none cursor-pointer"
                          >
                            <option value="en">English (US)</option>
                            <option value="ur">Urdu (اردو)</option>
                            <option value="roman_ur">Roman Urdu</option>
                          </select>
                        </div>

                        <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5">
                          <div>
                            <p className="font-medium text-white">Email Notifications</p>
                            <p className="text-xs text-slate-400 mt-1">Receive daily summary emails from your agents.</p>
                          </div>
                          <div 
                            className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors ${emailNotifs ? 'bg-emerald-500' : 'bg-slate-700'}`}
                            onClick={() => setEmailNotifs(!emailNotifs)}
                          >
                            <motion.div layout className="w-4 h-4 rounded-full bg-white absolute top-1" style={{ left: emailNotifs ? "24px" : "4px" }} />
                          </div>
                        </div>

                        <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5">
                          <div>
                            <p className="font-medium text-white">Proactive AI Actions</p>
                            <p className="text-xs text-slate-400 mt-1">Allow agents to take low-risk actions automatically.</p>
                          </div>
                          <div 
                            className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors ${proactive ? 'bg-emerald-500' : 'bg-slate-700'}`}
                            onClick={() => setProactive(!proactive)}
                          >
                            <motion.div layout className="w-4 h-4 rounded-full bg-white absolute top-1" style={{ left: proactive ? "24px" : "4px" }} />
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {activeTab === "api" && (
                    <motion.div
                      key="api"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.2 }}
                    >
                      <h2 className="text-lg font-bold text-white mb-6">API Configuration</h2>
                      <p className="text-sm text-slate-400 mb-6">Manage your API keys for custom integrations.</p>
                      
                      <div className="space-y-4">
                        <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between">
                          <div>
                            <p className="font-medium text-white">Production Key</p>
                            <p className="text-xs text-slate-500 font-mono mt-1">sk-prod-************************</p>
                          </div>
                          <button className="px-3 py-1.5 text-xs font-medium text-emerald-400 bg-emerald-500/10 rounded-lg hover:bg-emerald-500/20 transition-colors">
                            Reveal
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {activeTab === "security" && (
                    <motion.div
                      key="security"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.2 }}
                    >
                      <h2 className="text-lg font-bold text-white mb-6">Security Settings</h2>
                      <div className="space-y-4">
                        <button className="w-full text-left p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
                          <p className="font-medium text-white">Change Password</p>
                          <p className="text-xs text-slate-400 mt-1">Update your account password securely.</p>
                        </button>
                        <button className="w-full text-left p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
                          <p className="font-medium text-white">Two-Factor Authentication</p>
                          <p className="text-xs text-slate-400 mt-1">Add an extra layer of security to your account.</p>
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="mt-8 pt-6 border-t border-white/5 flex justify-end">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleSave}
                  className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white font-semibold rounded-xl transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)]"
                >
                  <Save size={18} />
                  {saving ? "Saving..." : t("settings.save")}
                </motion.button>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </Sidebar>
  );
}
