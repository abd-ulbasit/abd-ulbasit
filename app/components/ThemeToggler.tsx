"use client"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"
const ThemeToggler = () => {
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
        <button className={`btn capitalize  glass`} onClick={() => { setTheme(themes[Math.floor(Math.random() * themes.length)]) }}  >{theme}
        </button>
    );
}
export default ThemeToggler;