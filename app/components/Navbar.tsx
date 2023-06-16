import ThemeToggler from "./ThemeToggler";

const Navbar = () => {
    return (
        <div className="flex flex-row items-center justify-between bg- p-2">
            <div>
                Navbar
            </div>
            <div className="" >
                <ThemeToggler></ThemeToggler>
            </div>
        </div>
    );
}

export default Navbar;