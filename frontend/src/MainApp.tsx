import { useState } from "react"
import Conversation from "./Conversation"
import Documents from "./Documents"

function MainApp() {
  const [page, setPage] = useState<"conversation" | "documents">(
    "conversation"
  )

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-glyph">CB</div>
          <div className="brand-text">
            CoolBreeze AC
            <span>Support console</span>
          </div>
        </div>

        <nav className="tab-nav">
          <button
            className={
              "tab-button" + (page === "conversation" ? " active" : "")
            }
            onClick={() => setPage("conversation")}
          >
            Conversation
          </button>

          <button
            className={
              "tab-button" + (page === "documents" ? " active" : "")
            }
            onClick={() => setPage("documents")}
          >
            Documents
          </button>
        </nav>
      </header>

      {page === "conversation" && <Conversation />}
      {page === "documents" && <Documents />}
    </div>
  )
}

export default MainApp
