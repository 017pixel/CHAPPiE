import { NavLink, Outlet } from "react-router-dom";
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
  const { isSidebarOpen, toggleSidebar } = useUiStore();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-ink text-mist">
      {/* Sidebar */}
      <aside
        className={`relative flex flex-col border-r border-white/5 bg-night transition-all duration-500 ease-in-out ${
          isSidebarOpen ? "w-72" : "w-20"
        } lg:static`}
      >
        <div className="flex h-24 items-center justify-center px-6">
          <span className={`text-xl font-black tracking-tighter text-mist uppercase transition-opacity duration-300 ${isSidebarOpen ? "opacity-100" : "opacity-0 invisible"}`}>CHAPPiE</span>
        </div>

        <nav className="flex-1 space-y-2 px-3">
          {items.map(({ label, to, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `group flex items-center rounded-none p-3 text-sm font-medium transition-all duration-300 ${
                  isActive
                    ? "bg-ember text-white shadow-glass"
                    : "text-slate hover:bg-white/5 hover:text-mist"
                } ${!isSidebarOpen ? "justify-center" : "gap-4"}`
              }
              title={!isSidebarOpen ? label : ""}
            >
              <span className="material-symbols-outlined text-[22px] leading-none">{icon}</span>
              {isSidebarOpen && <span className="truncate whitespace-nowrap">{label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="p-4">
          <button
            onClick={toggleSidebar}
            className="flex w-full items-center justify-center rounded-none bg-white/5 py-3 text-slate transition-all hover:bg-ember hover:text-white"
          >
            <span className={`material-symbols-outlined transition-transform duration-500`}>
              {isSidebarOpen ? "chevron_left" : "chevron_right"}
            </span>
          </button>
        </div>

        {isSidebarOpen && (
          <div className="m-4 rounded-none bg-pine/20 p-4 text-[10px] text-slate border border-pine/10">
            <p className="font-bold uppercase tracking-widest text-pine">API-Target</p>
            <p className="mt-1 break-all opacity-80">{import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8010"}</p>
          </div>
        )}
      </aside>

      {/* Main Content Area */}
      <main className="relative flex flex-1 flex-col overflow-y-auto overflow-x-hidden">
        {/* Subtle top bar for tablet/mobile or just status */}
        <header className="flex h-20 items-center justify-between px-8 lg:h-24">
          <h2 className="text-sm font-medium uppercase tracking-[0.2em] text-slate">System Overview</h2>
          <div className="flex items-center gap-4">
            <div className="h-2 w-2 animate-pulse rounded-none bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
            <span className="text-[10px] uppercase tracking-widest text-slate">Online</span>
          </div>
        </header>

        <div className="mx-auto w-full max-w-[95%] px-6 pb-12 lg:px-12">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
