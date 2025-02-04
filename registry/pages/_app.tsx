import React from 'react'
import '../styles/globals.css'
import initAuth from '../utils/initAuth'
import CommonHeader from '../components/CommonHeader'
import type { AppProps } from 'next/app'

initAuth()

const MyApp = ({ Component, pageProps }: AppProps) => (
  <div className="min-h-screen flex flex-col">
    <CommonHeader />
    <main className="flex-1">
      <Component {...pageProps} />
    </main>
  </div>
)

export default MyApp