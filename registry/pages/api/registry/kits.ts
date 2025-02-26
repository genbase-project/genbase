// pages/api/registry/kits.ts
import type { NextApiRequest, NextApiResponse } from 'next'
import { getFirestore, Query, DocumentData } from 'firebase-admin/firestore'

import { initAdmin } from '@/utils/initAdmin';

initAdmin()


interface KitSummary {
  fileName: string;
  downloadURL: string;
  checksum: string;
  kitConfig: {
    name: string;
    id: string;
    version: string;
    owner: string;
    description?: string;
    workflows?: Record<string, any>;
    dependencies?: string[];
  };
  uploadedAt: string;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const db = getFirestore()
    const packagesRef = db.collection('packages')
    
    // Handle optional query parameters for filtering
    const { owner, limit = '50', skip = '0' } = req.query
    
    let query: Query<DocumentData> = packagesRef
    
    // Apply owner filter if provided
    if (owner) {
      query = query.where('kitConfig.owner', '==', owner)
    }
    
    // Order by upload date (newest first)
    query = query.orderBy('uploadedAt', 'desc')
    
    // Apply pagination
    const limitNum = parseInt(limit as string, 10)
    const skipNum = parseInt(skip as string, 10)
    
    if (skipNum > 0) {
      // For pagination with skip, we need to use a different approach
      // This fetches documents to skip and uses the last one as a cursor
      const skipQuery = packagesRef.orderBy('uploadedAt', 'desc').limit(skipNum)
      const skipSnapshot = await skipQuery.get()
      
      if (!skipSnapshot.empty) {
        const lastDoc = skipSnapshot.docs[skipSnapshot.docs.length - 1]
        query = query.startAfter(lastDoc)
      }
    }
    
    // Apply the limit to our query
    query = query.limit(limitNum)
    
    // Execute the query
    const querySnapshot = await query.get()
    
    const kits: KitSummary[] = []
    
    querySnapshot.forEach((doc) => {
      const data = doc.data()
      kits.push({
        fileName: data.fileName,
        downloadURL: data.downloadURL,
        checksum: data.checksum,
        kitConfig: data.kitConfig,
        uploadedAt: data.uploadedAt
      })
    })
    
    // Count total kits (optional - remove if performance is a concern)
    const countSnapshot = await packagesRef.count().get();
    const totalCount = countSnapshot.data().count;
    
    const response = {
      total: totalCount,
      returned: kits.length,
      kits
    }
    
    return res.status(200).json(response)
  } catch (error) {
    console.error('Error fetching kits:', error)
    return res.status(500).json({ 
      error: error instanceof Error ? error.message : 'Internal server error' 
    })
  }
}