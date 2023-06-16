"use client"
import './globals.css'
import { Inter } from 'next/font/google'
import { ThemeWrapper } from './providers';
import Navbar from './components/Navbar';
import { useTheme } from 'next-themes';
const inter = Inter({ subsets: ['latin'] })

const metadata = {
  title: 'Create Next App',
  description: 'Generated by create next app',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { setTheme, theme } = useTheme()
  return (
    <html lang="en">

      <body className={inter.className + ``}>
        <ThemeWrapper >

          <Navbar></Navbar>
          {children}
        </ThemeWrapper>
      </body>
    </html>
  )
}


