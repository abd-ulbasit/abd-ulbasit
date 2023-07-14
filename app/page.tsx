'use client'
import { useEffect, useState } from "react"
import Socials from "./components/Socials"
import { useTheme } from "next-themes"
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
      <div className="max-w-sm flex flex-col gap-4  border-4" id="excludeDiv">

        <h1 className='text-4xl font-bold font-serif pl-2 sm:pl-0 hover:animate-pulse' >Abdul Basit</h1>
        <p className='italic indent-8  pl-1 sm:pl-0 ' >I study Computer Science. I am currently building applications in NEXTJS, and t3-stack . I also do Rust, system design, leetcode and advent of code.</p>
        <div className="mx-auto" >
          <Socials></Socials>
        </div>
      </div>
    </main>
  )
}
