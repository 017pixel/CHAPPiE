import { useCallback, useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useUiStore } from "../store/ui";

const items = [
  { label: "Chat", to: "/", icon: "chat_bubble" },
  { label: "Kontext", to: "/context", icon: "database" },
  { label: "Memories", to: "/memories", icon: "history" },
  { label: "Life", to: "/life", icon: "favorite" },
  { label: "Growth", to: "/growth", icon: "trending_up" },
  { label: "Settings", to: "/settings", icon: "settings" },
  { label: "Training", to: "/training", icon: "model_training" },
  { label: "Debug", to: "/debug", icon: "bug_report" },
  { label: "3D", to: "/visualizer", icon: "view_in_ar" }
];

export function AppShell() {
  const { isSidebarOpen, toggleSidebar, closeSidebar } = useUiStore();
  const location = useLocation();

  const handleResize = useCallback(() => {
    if (window.innerWidth >= 1024 && !isSidebarOpen) {
      toggleSidebar();
    }
  }, [isSidebarOpen, toggleSidebar]);

  useEffect(() => {
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [handleResize]);

  useEffect(() => {
    if (window.innerWidth < 1024) {
      closeSidebar();
    }
  }, [location.pathname]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-ink text-mist">
      {/* Mobile Sidebar Backdrop */}
      <div
        className={`sidebar-backdrop lg:hidden ${isSidebarOpen ? "" : "hidden"}`}
        onClick={closeSidebar}
      />

      {/* Sidebar */}
      <aside
        className={`app-sidebar flex flex-col border-r border-white/5 bg-night ${
          isSidebarOpen ? "open w-72" : "closed"
        } lg:static lg:w-72 lg:translate-x-0`}
      >
        <div className="flex h-24 items-center justify-center px-6">
          <span className="text-xl font-black tracking-tighter text-mist uppercase">CHAPPiE</span>
        </div>

        <nav className="flex-1 space-y-2 px-3">
          {items.map(({ label, to, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `group flex items-center gap-4 rounded-none p-3 text-sm font-medium transition-all duration-300 ${
                  isActive
                    ? "bg-ember text-white shadow-glass"
                    : "text-slate hover:bg-white/5 hover:text-mist"
                }`
              }
            >
              <span className="material-symbols-outlined text-[22px] leading-none">{icon}</span>
              <span className="truncate whitespace-nowrap">{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 lg:hidden">
          <button
            onClick={closeSidebar}
            className="flex w-full items-center justify-center rounded-none bg-white/5 py-3 text-slate transition-all hover:bg-ember hover:text-white"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <a
          href={import.meta.env.VITE_API_BASE_URL ?? "http://100.105.94.71:8010"}
          target="_blank"
          rel="noopener noreferrer"
          className="m-4 block rounded-none bg-pine/20 p-4 text-[10px] text-slate border border-pine/10 hover:bg-pine/30 hover:border-pine/30 transition-all"
        >
          <p className="font-bold uppercase tracking-widest text-pine">API-Target</p>
          <p className="mt-1 break-all opacity-80">{import.meta.env.VITE_API_BASE_URL ?? "http://100.105.94.71:8010"}</p>
        </a>
      </aside>

      {/* Main Content Area */}
      <main className="relative flex flex-1 flex-col overflow-y-auto overflow-x-hidden">
        <header className="app-header flex h-20 items-center justify-between px-8 lg:h-24">
          {/* Hamburger (Mobile) */}
          <button
            className="mobile-hamburger"
            onClick={toggleSidebar}
            aria-label="Toggle Sidebar"
          >
            <span className="material-symbols-outlined text-mist">menu</span>
          </button>

          {/* Space */}
          <div className="flex-1" />

          {/* Online Indicator */}
          {location.pathname === "/" && (
            <div className="flex items-center gap-4">
              <div className="h-2 w-2 animate-pulse rounded-none bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
              <span className="text-[10px] uppercase tracking-widest text-slate">Online</span>
            </div>
          )}
        </header>

        <div className="app-content-wrapper mx-auto w-full max-w-[95%] px-6 pb-12 lg:px-12">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
