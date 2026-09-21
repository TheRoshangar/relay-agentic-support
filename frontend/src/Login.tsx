import { useState } from "react"

type LoginProps = {
  onLoginSuccess: () => void
}

function Login({ onLoginSuccess }: LoginProps) {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleLogin = async () => {
    setLoading(true)
    setError("")

    try {
      const response = await fetch(
        "http://localhost:8000/api/login/",
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username,
            password,
          }),
        }
      )

      const text = await response.text()

      console.log("STATUS:", response.status)
      console.log("RESPONSE:", text)

      const data = JSON.parse(text)

      if (!response.ok) {
        throw new Error(data.error || "Login failed")
      }

      console.log("LOGIN SUCCESS", data)

      onLoginSuccess()

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Something went wrong"
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-mark">
          <div className="login-mark-glyph">CB</div>
          <div className="login-mark-text">
            CoolBreeze AC
            <span>Support console</span>
          </div>
        </div>

        <h1>Sign in</h1>
        <p className="login-sub">
          Use your account to view orders and talk to Maya.
        </p>

        {error && <div className="error-banner">{error}</div>}

        <div className="field">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            placeholder="your.username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleLogin()
            }}
          />
        </div>

        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleLogin()
            }}
          />
        </div>

        <button
          className="primary-button"
          onClick={handleLogin}
          disabled={loading}
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </div>
    </div>
  )
}

export default Login
