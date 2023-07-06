import Socials from "./components/Socials"
export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center">
      <div>
        <h1 className='' >
          <span className="" >
            I am
            <span className='' >
              Abdul Basit
            </span>
          </span>
        </h1>
        <p className='' >Studing Computer Science  </p>
        <div className="" >

          <Socials></Socials>
        </div>
      </div>
    </main>
  )
}
