import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "./index.css";
import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute, PublicOnlyRoute } from "./routes";
import Layout from "./pages/Layout";
import Login from "./pages/Login";
import SystemPrompts from "./pages/SystemPrompts";
import VisionProfiles from "./pages/VisionProfiles";
import McpAccess from "./pages/McpAccess";

const router = createBrowserRouter([
  {
    element: <PublicOnlyRoute />,
    children: [{ path: "/login", element: <Login /> }],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <Layout />,
        children: [
          { path: "/", element: <SystemPrompts /> },
          { path: "/system-prompts", element: <SystemPrompts /> },
          { path: "/vision-profiles", element: <VisionProfiles /> },
          { path: "/mcp-access", element: <McpAccess /> },
        ],
      },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <App />
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
);
