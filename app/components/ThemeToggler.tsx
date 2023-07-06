"use client"
import { useTheme } from "next-themes"
import { FaRegMoon, FaSun } from "react-icons/fa"
const ThemeToggler = () => {
    const { theme, setTheme } = useTheme();
    return (
        <button className={` text-primary-focus px-6 py-2`} onClick={() => { setTheme(theme == "night" ? "retro" : "night") }}  >{theme == "retro" ? <FaRegMoon></FaRegMoon> :
            <FaSun></FaSun>}
        </button>
    );
}
export default ThemeToggler;