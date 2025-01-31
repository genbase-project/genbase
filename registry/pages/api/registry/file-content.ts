// pages/api/registry/file-content.ts
import { verifyIdToken } from 'next-firebase-auth'
import type { NextApiRequest, NextApiResponse } from 'next'
import fetch from 'node-fetch'
import JSZip from 'jszip'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    // const token = req.headers.authorization
    // if (!token) {
    //   return res.status(401).json({ error: 'No authentication token provided' })
    // }

    // const user = await verifyIdToken(token)
    // if (!user) {
    //   return res.status(401).json({ error: 'Invalid authentication token' })
    // }

    const { downloadURL, filePath } = req.body

    // Download the zip file
    const fileResponse = await fetch(downloadURL)
    if (!fileResponse.ok) {
      throw new Error('Failed to download zip file')
    }

    const fileBuffer = await fileResponse.arrayBuffer()

    // Read the zip and get the requested file
    const zip = new JSZip()
    const contents = await zip.loadAsync(fileBuffer)
    
    const file = contents.file(filePath)
    if (!file) {
      return res.status(404).json({ error: 'File not found in package' })
    }

    const content = await file.async('string')
    return res.status(200).json({ content })
  } catch (error) {
    console.error('Error retrieving file:', error)
    return res.status(500).json({ 
      error: error instanceof Error ? error.message : 'Internal server error' 
    })
  }
}