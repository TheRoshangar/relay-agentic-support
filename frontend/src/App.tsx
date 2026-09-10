import { useState } from "react"
import Login from "./Login"
import MainApp from "./MainApp"

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  if (!isLoggedIn) {
    return (
      <Login
        onLoginSuccess={() => setIsLoggedIn(true)}
      />
    )
  }

  return <MainApp />
}

export default App