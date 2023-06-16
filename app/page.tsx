import Socials from "./components/Socials"
export default function Home() {
  return (
    <main className="min-h-screen  ">

      <div className='flex flex-col items-center justify-between  min-h-screen px-0 sm:px-12 py-4 md:px-24 ' >
        <div className="flex flex-col gap-4">

          <h1 className='text-5xl  px-auto py-8' >
            <span className="block font-bold" >
              Hello World!
            </span>
            I am
            <span className='inline-block md:inline decoration-4  font-semibold underline text-orange-600 italic  px-2 rounded-sm font-sans   text-6xl' >
              Abdul Basit
            </span>
          </h1>
          <p className='text-2xl text-center' >Studing Computer Science  <span className='text-yellow-400 block ' >&</span> building Quality Web Applications</p>
          <p className="italic pt-4" >Together, we&apos;ll bring your ideas to life</p>
        </div>
        <Socials></Socials>
      </div>
    </main>
  )
}
