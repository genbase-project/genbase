// pages/api/registry/publish.ts
import { verifyIdToken } from 'next-firebase-auth'
import type { NextApiRequest, NextApiResponse } from 'next'
import { getFirestore } from 'firebase-admin/firestore'
import fetch from 'node-fetch'
import JSZip from 'jszip'
import yaml from 'js-yaml'
import crypto from 'crypto'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const token = req.headers.authorization
    if (!token) {
      return res.status(401).json({ error: 'No authentication token provided' })
    }

    const user = await verifyIdToken(token)
    if (!user) {
      return res.status(401).json({ error: 'Invalid authentication token' })
    }

    const { fileName, fileSize, downloadURL } = req.body

    // Download the zip file
    const fileResponse = await fetch(downloadURL)
    if (!fileResponse.ok) {
      throw new Error('Failed to download zip file')
    }

    const fileBuffer = await fileResponse.arrayBuffer()

    // Calculate checksum
    const checksum = crypto
      .createHash('sha256')
      .update(new Uint8Array(fileBuffer))
      .digest('hex')

    // Read and validate kit.yaml
    const zip = new JSZip()
    await zip.loadAsync(fileBuffer)
    
    const kitYamlFile = zip.file('kit.yaml')
    if (!kitYamlFile) {
      return res.status(400).json({ error: 'kit.yaml not found in root of zip file' })
    }

    // Parse kit.yaml
    const yamlContent = await kitYamlFile.async('string')
    const kitConfig = yaml.load(yamlContent)

    // Basic validation that it's an object
    if (!kitConfig || typeof kitConfig !== 'object') {
      return res.status(400).json({ error: 'Invalid kit.yaml format' })
    }

    // Save to Firestore
    const db = getFirestore()
    await db.collection('packages').add({
      userId: user.id,
      userEmail: user.email,
      fileName,
      fileSize,
      downloadURL,
      checksum,
      kitConfig,
      uploadedAt: new Date().toISOString(),
    })

    return res.status(200).json({ success: true })
  } catch (error) {
    console.error('Error in publish API:', error)
    return res.status(500).json({ 
      error: error instanceof Error ? error.message : 'Internal server error' 
    })
  }
}