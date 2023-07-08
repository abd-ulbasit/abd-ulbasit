import Socials from "./components/Socials"
export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center">
      <div className="max-w-sm flex flex-col gap-4">

        <h1 className='text-4xl font-bold font-serif pl-2 sm:pl-0 hover:animate-pulse' >Abdul Basit</h1>
        <p className='italic indent-8  pl-1 sm:pl-0 sm:tracking-normal tracking-tighter' >I study Computer Science. I am currently building applications in NEXTJS, t3-stack and  SvelteKit. I also do leetcode, system design and Rust.</p>
        <div className="mx-auto" >
          <Socials></Socials>
        </div>
      </div>
    </main>
  )
}
