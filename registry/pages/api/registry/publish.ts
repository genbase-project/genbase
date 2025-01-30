// pages/api/registry/publish.ts
import { verifyIdToken } from 'next-firebase-auth'
import type { NextApiRequest, NextApiResponse } from 'next'
import { getFirestore } from 'firebase-admin/firestore'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    // Get the ID token from the Authorization header
    const token = req.headers.authorization

    if (!token) {
      return res.status(401).json({ error: 'No authentication token provided' })
    }

    // Verify the token
    const user = await verifyIdToken(token)
    
    if (!user) {
      return res.status(401).json({ error: 'Invalid authentication token' })
    }

    const { fileName, fileSize, downloadURL, uploadedAt } = req.body

    // Save to Firestore
    const db = getFirestore()
    await db.collection('packages').add({
      userId: user.id,
      userEmail: user.email,
      fileName,
      fileSize,
      downloadURL,
      uploadedAt,
      createdAt: new Date().toISOString(),
    })

    return res.status(200).json({ success: true })
  } catch (error) {
    console.error('Error in publish API:', error)
    return res.status(500).json({ 
      error: error instanceof Error ? error.message : 'Internal server error' 
    })
  }
}