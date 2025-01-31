// pages/publish.tsx
'use client'

import { useState } from 'react'
import { useUser, withUser, AuthAction } from 'next-firebase-auth'
import { getStorage, ref, uploadBytes, getDownloadURL } from 'firebase/storage'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Progress } from '@/components/ui/progress'

const storage = getStorage()

function PublishPage() {
  const user = useUser()
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [showSuccessDialog, setShowSuccessDialog] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null)
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      if (selectedFile.type === 'application/zip' || selectedFile.name.endsWith('.zip')) {
        setFile(selectedFile)
      } else {
        setError('Please upload a zip file')
      }
    }
  }

  const handleUpload = async () => {
    if (!file || !user.id) return

    try {
      setUploading(true)
      setError(null)

      const token = await user.getIdToken()
      if (!token) {
        throw new Error('Authentication token not available')
      }

      // Upload to Firebase Storage
      const storageRef = ref(storage, `registry/${user.id}/${file.name}`)
      await uploadBytes(storageRef, file)
      const downloadURL = await getDownloadURL(storageRef)

      // Send to API for processing
      const response = await fetch('/api/registry/publish', {
        method: 'POST',
        headers: {
          'Authorization': token,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fileName: file.name,
          fileSize: file.size,
          downloadURL,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to process package')
      }

      setShowSuccessDialog(true)
      setFile(null)
    } catch (error) {
      console.error('Error:', error)
      setError(error instanceof Error ? error.message : 'Error uploading file')
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }

  return (
    <div className="container mx-auto py-10">
      <Card className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Publish Registry Package</h1>
          <Button
            variant="outline"
            onClick={() => user.signOut()}
          >
            Sign Out
          </Button>
        </div>

        <div className="space-y-4">
          <div className="grid w-full max-w-sm items-center gap-1.5">
            <Label htmlFor="file">Package File (ZIP)</Label>
            <Input
              id="file"
              type="file"
              accept=".zip,application/zip,application/x-zip-compressed"
              onChange={handleFileChange}
              disabled={uploading}
            />
          </div>

          {error && (
            <div className="text-sm text-red-500">
              {error}
            </div>
          )}

          {file && (
            <div className="text-sm text-gray-500">
              Selected file: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
            </div>
          )}

          {uploading && (
            <Progress value={uploadProgress} className="w-full max-w-sm" />
          )}

          <Button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full max-w-sm"
          >
            {uploading ? 'Uploading...' : 'Upload Package'}
          </Button>
        </div>
      </Card>

      <AlertDialog open={showSuccessDialog} onOpenChange={setShowSuccessDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Upload Successful</AlertDialogTitle>
            <AlertDialogDescription>
              Your package has been successfully uploaded to the registry.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Button onClick={() => setShowSuccessDialog(false)}>Close</Button>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default withUser({
  whenUnauthedAfterInit: AuthAction.REDIRECT_TO_LOGIN,
  whenUnauthedBeforeInit: AuthAction.SHOW_LOADER,
})(PublishPage)