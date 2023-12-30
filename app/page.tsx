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
  const content = "I study Computer Science and build applications in NEXTJS, and MERN Stack. I'm learning system programming in Rust"
  return (
    <main className="min-h-screen flex flex-col items-center justify-center " onClick={(e) => {
      if ((e.target as HTMLElement).closest('#excludeDiv')) return;
      setTheme(themes[Math.floor(Math.random() * themes.length)])
    }}>
      <div className="max-w-sm flex flex-col gap-4" id="excludeDiv">

        <h1 className='text-4xl font-bold font-serif pl-2 sm:pl-0 hover:animate-pulse' >Abdul Basit</h1>
        <p className='italic flex flex-wrap items-start gap-1' >
          <span className="w-6" ></span>
          {
            content.split(" ").map((word) => {
              return (
                <span key={word} className="hover:animate-pulse">
                  {word}
                </span>
              )
            })
          }
        </p>
        <div className="mx-auto" >
          <Socials></Socials>
        </div>
      </div>
    </main>
  )
}
