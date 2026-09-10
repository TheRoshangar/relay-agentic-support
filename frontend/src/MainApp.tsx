import { useState } from "react"
import Conversation from "./Conversation"
import Documents from "./Documents"

function MainApp() {
  const [page, setPage] = useState<"conversation" | "documents">(
    "conversation"
  )

  return (
    <div>
      <nav>
        <button onClick={() => setPage("conversation")}>
          Conversation
        </button>

        <button onClick={() => setPage("documents")}>
          Documents
        </button>
      </nav>

      <hr />

      {page === "conversation" && <Conversation />}

      {page === "documents" && <Documents />}
    </div>
  )
}

export default MainApp