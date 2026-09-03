"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { User, Building2, MapPin, Mail, LogOut, Check, Save, ShieldCheck, Sparkles } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { getMe, updateProfile, logoutUser, type AuthBusiness } from "@/lib/api";

export default function ProfilePage() {
  const [profile, setProfile] = useState<AuthBusiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [businessName, setBusinessName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [location, setLocation] = useState("");
  const [tagline, setTagline] = useState("");

  useEffect(() => {
    getMe()
      .then((data) => {
        setProfile(data);
        setBusinessName(data.name);
        setOwnerName(data.owner_name);
        setLocation(data.location || "");
        setTagline(data.tagline || "");
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const res = await updateProfile({
        business_name: businessName,
        owner_name: ownerName,
        location,
        tagline,
      });
      setProfile(res.business);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sidebar>
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
            <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
              <User className="text-emerald-400" size={32} />
              Owner &amp; Business Profile
            </h1>
            <p className="text-sm text-slate-400 mt-1">Manage your identity and SME company details</p>
          </motion.div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={logoutUser}
            className="flex items-center gap-2 px-4 py-2.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 rounded-xl text-sm font-semibold transition-colors shadow-lg"
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </motion.button>
        </div>

        {loading ? (
          <div className="text-center py-20 text-slate-400">Loading profile data...</div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
            {error}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Left Card: Summary */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="md:col-span-1 bg-[#0e1522]/80 border border-white/10 rounded-3xl p-6 backdrop-blur-xl flex flex-col items-center text-center relative overflow-hidden"
            >
              <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-emerald-400 to-emerald-600 flex items-center justify-center text-slate-950 font-black text-3xl shadow-[0_0_30px_rgba(16,185,129,0.3)] mb-4">
                {ownerName.slice(0, 2).toUpperCase() || "AA"}
              </div>

              <h2 className="text-xl font-bold text-white">{ownerName}</h2>
              <p className="text-xs text-emerald-400 font-semibold tracking-wider uppercase mt-1">
                Authorized SME Owner
              </p>

              <div className="w-full mt-6 pt-6 border-t border-white/5 space-y-3 text-left">
                <div className="flex items-center gap-2.5 text-xs text-slate-300">
                  <Mail size={15} className="text-slate-500" />
                  <span className="truncate">{profile?.email}</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-slate-300">
                  <Building2 size={15} className="text-slate-500" />
                  <span className="truncate">{profile?.name}</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-slate-300">
                  <MapPin size={15} className="text-slate-500" />
                  <span className="truncate">{profile?.location || "Pakistan"}</span>
                </div>
              </div>

              <div className="mt-6 w-full p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-3">
                <ShieldCheck size={24} className="text-emerald-400 flex-shrink-0" />
                <div className="text-left">
                  <div className="text-xs font-bold text-white">AI Workforce Active</div>
                  <div className="text-[11px] text-slate-400">6 Specialized Agents Attached</div>
                </div>
              </div>
            </motion.div>

            {/* Right Card: Editable Form */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="md:col-span-2 bg-[#0e1522]/80 border border-white/10 rounded-3xl p-8 backdrop-blur-xl"
            >
              <h3 className="text-lg font-bold text-white mb-6">Business Settings &amp; Identity</h3>

              <form onSubmit={handleSave} className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                      Business Name
                    </label>
                    <input
                      type="text"
                      required
                      value={businessName}
                      onChange={(e) => setBusinessName(e.target.value)}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/20"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                      Owner Name
                    </label>
                    <input
                      type="text"
                      required
                      value={ownerName}
                      onChange={(e) => setOwnerName(e.target.value)}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/20"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    City / Location
                  </label>
                  <input
                    type="text"
                    required
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/20"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Tagline / Business Description
                  </label>
                  <input
                    type="text"
                    value={tagline}
                    onChange={(e) => setTagline(e.target.value)}
                    placeholder="e.g. Premium Pakistani Clothing"
                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/20"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Account Email (Permanent)
                  </label>
                  <input
                    type="email"
                    disabled
                    value={profile?.email || ""}
                    className="w-full bg-black/20 border border-white/5 rounded-xl px-4 py-3 text-sm text-slate-400 cursor-not-allowed"
                  />
                </div>

                <div className="pt-4 flex items-center justify-between">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    disabled={saving}
                    type="submit"
                    className="py-3 px-6 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-slate-950 font-bold rounded-xl shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all flex items-center gap-2 text-sm disabled:opacity-50"
                  >
                    {saved ? (
                      <>
                        <Check size={16} />
                        <span>Saved Successfully!</span>
                      </>
                    ) : (
                      <>
                        <Save size={16} />
                        <span>{saving ? "Saving Changes..." : "Update Business Profile"}</span>
                      </>
                    )}
                  </motion.button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </div>
    </Sidebar>
  );
}
