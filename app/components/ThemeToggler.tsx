"use client"
import { useTheme } from "next-themes"
import { FaRegMoon, FaSun } from "react-icons/fa"
const ThemeToggler = () => {
    const { theme, setTheme } = useTheme();
    return (
        <button className={` text-red-600 px-6 py-2`} onClick={() => { setTheme(theme == "light" ? "dark" : "light") }}  >{theme == "light" ? <FaRegMoon></FaRegMoon> :
            <FaSun></FaSun>}
        </button>
    );
}
export default ThemeToggler;