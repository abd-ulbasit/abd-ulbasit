import Socials from "./components/Socials"
export default function Home() {
  return (
    <main className="min-h-screen  ">
      <div className='flex flex-col items-center   min-h-screen px-1 sm:px-12 py-4 md:px-24 ' >
        <div className="flex flex-col gap-4 justify-between content-between flex-grow">

          <h1 className='text-5xl  px-auto py-8' >
            <span className="block font-bold" >
              Hello World!
            </span>
            <span className="py-10 my-10" >
              I am
              <span className='inline-block md:inline decoration-4  font-bold underline text-orange-600 italic  px-2  font-sans text-6xl' >
                Abdul Basit
              </span>
            </span>
          </h1>
          <p className='text-2xl text-center' >Studing Computer Science  <span className='text-yellow-400 block ' >&</span> building Quality Web Applications</p>
          <p className="italic pt-4 text-gray-400" >Together, we&apos;ll bring your ideas to life.</p>
        </div>
        <div className="mt-10" >

          <Socials></Socials>
        </div>
      </div>
    </main>
  )
}
