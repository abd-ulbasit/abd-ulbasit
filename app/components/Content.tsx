import Socials from "./Socials";

const Content = () => {
    const content = "I study Computer Science and build web apps with TypeScript (JS, sometimes). I'm gaining expertise in cloud-native development"

    return (
        <div className="max-w-sm flex flex-col gap-4" id="excludeDiv">

            <h1 className='text-4xl font-bold font-serif pl-2 sm:pl-0 hover:animate-pulse' >I&apos;m Abdul Basit</h1>
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
    );
}

export default Content;