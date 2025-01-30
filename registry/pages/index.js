import React from 'react'
import { withUser } from 'next-firebase-auth'
import CommonHeader from '../components/Header'
import HomePage from '../components/Home'

const Index = () => {
  return (
    <div>
      <HomePage />
    </div>
  )
}

// No authentication required for home page
export default withUser()(Index)