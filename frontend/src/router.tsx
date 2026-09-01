import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "./components/app-shell";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      // The split shell owns the workspace. These routes stay addressable for
      // bookmarks and command-palette jumps to inspector sections.
      { index: true, element: null },
      { path: "context", element: null },
      { path: "memories", element: null },
      { path: "life", element: null },
      { path: "growth", element: null },
      { path: "settings", element: null },
      { path: "training", element: null },
      { path: "debug", element: null }
    ]
  }
]);
