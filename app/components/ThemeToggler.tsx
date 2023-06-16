"use client"
import { useTheme } from "next-themes"
import { FaRegMoon, FaSun } from "react-icons/fa"
const ThemeToggler = () => {
    const { theme, setTheme } = useTheme();
    return (<div className="" >
        <button className={`dark:bg-white text-slate-600 px-6 py-2 dark:text-slate-200 `} onClick={() => { setTheme(theme == "light" ? "dark" : "light") }}  >{theme == "light" ? <FaRegMoon></FaRegMoon> : <FaSun></FaSun>}</button>
    </div>
    );
}
export default ThemeToggler;