import './globals.css'
import { ThemeWrapper } from './providers';
import ThemeToggler from './components/ThemeToggler';


export const metadata = {
  title: 'abdulbasit',
  description: 'computer science student and web-application developer',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {

  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" sizes='any' />
      </head>
      <body >
        <ThemeWrapper >
          <div className='absolute right-4 top-2' >
            <ThemeToggler></ThemeToggler>
          </div>
          {children}

        </ThemeWrapper>
      </body>
    </html>
  )
}


