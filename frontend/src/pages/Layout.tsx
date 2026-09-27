import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import GitHubCard from "./GitHubCard";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="layout">
      <header>
        <span className="brand"><span className="looky-brand-name">Looky</span> MCP</span>
        <nav>
          <NavLink to="/system-prompts">System Prompts</NavLink>
          <span className="nav-divider" aria-hidden="true">|</span>
          <NavLink to="/vision-profiles">Vision Profiles</NavLink>
          <span className="nav-divider" aria-hidden="true">|</span>
          <NavLink to="/mcp-access">MCP Access</NavLink>
        </nav>
        <span className="user">
          {user?.email} <button onClick={() => void logout()}>Sign out</button>
        </span>
      </header>
      <main>
        <Outlet />
        <footer className="layout-footer">
          <GitHubCard />
        </footer>
      </main>
    </div>
  );
}
