import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "./components/app-shell";
import { ChatPage } from "./pages/chat-page";
import { ContextPage } from "./pages/context-page";
import { DebugPage } from "./pages/debug-page";
import { GrowthPage } from "./pages/growth-page";
import { LifePage } from "./pages/life-page";
import { MemoriesPage } from "./pages/memories-page";
import { SettingsPage } from "./pages/settings-page";
import { TrainingPage } from "./pages/training-page";
import { VisualizerPage } from "./pages/visualizer-page";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <ChatPage /> },
      { path: "context", element: <ContextPage /> },
      { path: "memories", element: <MemoriesPage /> },
      { path: "life", element: <LifePage /> },
      { path: "growth", element: <GrowthPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "training", element: <TrainingPage /> },
      { path: "debug", element: <DebugPage /> },
      { path: "visualizer", element: <VisualizerPage /> }
    ]
  }
]);
