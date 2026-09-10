import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="layout">
      <header>
        <span className="brand">Vision MCP</span>
        <nav>
          <NavLink to="/system-prompts">System Prompts</NavLink>
          <NavLink to="/vision-profiles">Vision Profiles</NavLink>
          <NavLink to="/mcp-access">MCP Access</NavLink>
        </nav>
        <span className="user">
          {user?.email} <button onClick={() => void logout()}>Sign out</button>
        </span>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
