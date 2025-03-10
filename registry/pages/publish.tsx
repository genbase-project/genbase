'use client'

import { useState } from 'react'
import { useUser, withUser, AuthAction } from 'next-firebase-auth'
import { getStorage, ref, uploadBytesResumable, getDownloadURL } from 'firebase/storage'
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

function PublishPage() {
  const user = useUser()
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [showSuccessDialog, setShowSuccessDialog] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Initialize storage inside the component to ensure it has access to the latest auth context
  const storage = getStorage()

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
    if (!file || !user.id) {
      setError('You must be logged in and select a file')
      return
    }

    try {
      setUploading(true)
      setError(null)
      
      // Get fresh token
      const token = await user.getIdToken(true) // Force refresh
      if (!token) {
        throw new Error('Authentication token not available')
      }

      console.log('User authenticated:', !!user.id)
      console.log('User ID:', user.id)
      
      // Add progress tracking
      const storageRef = ref(storage, `registry/${user.id}/${file.name}`)
      
      // Use uploadBytesResumable to track progress
      const uploadTask = uploadBytesResumable(storageRef, file)
      
      uploadTask.on('state_changed', 
        (snapshot) => {
          const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100
          setUploadProgress(progress)
          console.log(`Upload progress: ${progress}%`)
        },
        (error) => {
          console.error('Upload error:', error)
          setError(`Upload failed: ${error.message}`)
          setUploading(false)
        },
        async () => {
          // Upload completed successfully
          const downloadURL = await getDownloadURL(uploadTask.snapshot.ref)
          console.log('File uploaded successfully')
          
          // Continue with API call
          try {
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

            console.log('API processing successful:', data)
            setShowSuccessDialog(true)
            setFile(null)
          } catch (apiError) {
            console.error('API Error:', apiError)
            setError(apiError instanceof Error ? apiError.message : 'Error processing file')
          } finally {
            setUploading(false)
            setUploadProgress(0)
          }
        }
      )
    } catch (error) {
      console.error('Error:', error)
      setError(error instanceof Error ? error.message : 'Error uploading file')
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
            <div className="space-y-2 w-full max-w-sm">
              <Progress value={uploadProgress} className="w-full" />
              <p className="text-sm text-gray-500 text-center">{uploadProgress.toFixed(1)}%</p>
            </div>
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