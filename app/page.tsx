'use client'
import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import Content from "./components/Content"
export default function Home() {
  const themes = [
    "light",
    "dark",
    "cupcake",
    "bumblebee",
    "emerald",
    "corporate",
    "synthwave",
    "retro",
    "cyberpunk",
    "valentine",
    "halloween",
    "garden",
    "forest",
    "aqua",
    "lofi",
    "pastel",
    "fantasy",
    "wireframe",
    "black",
    "luxury",
    "dracula",
    "cmyk",
    "autumn",
    "business",
    "acid",
    "lemonade",
    "night",
    "coffee",
    "winter",
  ]
  const [mounted, setMounted] = useState(false)
  const { theme, setTheme } = useTheme()
  // useEffect only runs on the client, so now we can safely show the UI
  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return null
  }
  return (
    <main className="min-h-screen flex flex-col items-center justify-center " onClick={(e) => {
      if ((e.target as HTMLElement).closest('#excludeDiv')) return;
      setTheme(themes[Math.floor(Math.random() * themes.length)])
    }}>
      <Content />
    </main>
  )
}
