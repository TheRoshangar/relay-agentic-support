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
    <div>
      <h1>Login</h1>

      {error && <p>{error}</p>}

      <input
        type="text"
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />

      <br />

      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <br />

      <button
        onClick={handleLogin}
        disabled={loading}
      >
        {loading ? "Logging in..." : "Login"}
      </button>
    </div>
  )
}

export default Login