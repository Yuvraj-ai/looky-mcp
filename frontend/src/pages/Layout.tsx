import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import DeleteAccountModal from "./DeleteAccountModal";
import GitHubCard from "./GitHubCard";

export default function Layout() {
  const { user, logout } = useAuth();
  const [showDeleteModal, setShowDeleteModal] = useState(false);

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
          <span className="user-email" title={user?.email}>{user?.email}</span>
          <button type="button" className="btn-signout" onClick={() => void logout()}>Sign out</button>
          <button
            type="button"
            className="btn-delete-account-nav"
            onClick={() => setShowDeleteModal(true)}
            title="Delete my account and all data"
            aria-label="Delete my account"
          >
            Delete account
          </button>
        </span>
      </header>
      <main>
        <Outlet />
        <footer className="layout-footer">
          <GitHubCard />
          <button
            type="button"
            className="footer-delete-account-btn"
            onClick={() => setShowDeleteModal(true)}
          >
            Delete my account
          </button>
        </footer>
      </main>

      <DeleteAccountModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
      />
    </div>
  );
}
