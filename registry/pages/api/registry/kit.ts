// pages/api/registry/kit.ts
import type { NextApiRequest, NextApiResponse } from 'next'
import { getFirestore } from 'firebase-admin/firestore'

import { initAdmin } from '@/utils/initAdmin';

initAdmin()

interface KitResponse {
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
    const { owner, id, version } = req.query

    if (!owner || !id) {
      return res.status(400).json({ 
        error: 'Missing required parameters: owner and id are required' 
      })
    }

    const db = getFirestore()
    const packagesRef = db.collection('packages')
    
    let query = packagesRef
      .where('kitConfig.owner', '==', owner)
      .where('kitConfig.id', '==', id)
    
    // If version is specified, get that version; otherwise get the latest
    if (version) {
      query = query.where('kitConfig.version', '==', version)
    } else {
      query = query.orderBy('uploadedAt', 'desc')
    }
    
    const querySnapshot = await query.limit(1).get()

    if (querySnapshot.empty) {
      return res.status(404).json({ 
        error: 'Kit not found' 
      })
    }

    const kitData = querySnapshot.docs[0].data()
    
    const response: KitResponse = {
      downloadURL: kitData.downloadURL,
      checksum: kitData.checksum,
      kitConfig: kitData.kitConfig,
      uploadedAt: kitData.uploadedAt,
    }

    return res.status(200).json(response)
  } catch (error) {
    console.error('Error in kit API:', error)
    return res.status(500).json({ 
      error: error instanceof Error ? error.message : 'Internal server error' 
    })
  }
}
