import Image from 'next/image'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24 bg-white">
      <h1 className='text-5xl font-mono ' >
        Hello World! I am
        <span className=' decoration-4 ml-4 font-semibold underline text-orange-600 italic bg-purple-200 px-2 rounded-sm font-sans decoration-lime-600 decoration-dotted' >
          Abdul Basit
        </span>
      </h1>
      <p className='italic'>And You are blinded by the light theme</p>
    </main>
  )
}
