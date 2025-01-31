// pages/index.tsx
import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Package, FileCode, GitFork } from 'lucide-react';
import { getFirestore, collection, getDocs } from 'firebase/firestore';
import Link from 'next/link';

interface Package {
  fileName: string;
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

const HomePage = () => {
  const [packages, setPackages] = useState<Package[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPackages = async () => {
      try {
        const db = getFirestore();
        const packagesCollection = collection(db, 'packages');
        const packagesSnapshot = await getDocs(packagesCollection);
        
        const packagesData = packagesSnapshot.docs.map(doc => ({
          ...doc.data()
        })) as Package[];

        setPackages(packagesData);
      } catch (error) {
        console.error('Error fetching packages:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPackages();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* orange background */}
      <section className="py-8 px-4 text-center bg-orange-400">
        <div className="container mx-auto max-w-4xl">
          <p className="text-xl text-muted-foreground  text-white">
            A registry of Agent-controlled interconnectable Modules Kits
          </p>
        </div>
      </section>

      <main className="container mx-auto py-12 px-4">
        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-6">Available Packages</h2>
          {loading ? (
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900" />
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {packages.map((pkg) => (
                <Link href={`/kit/${pkg.kitConfig.id}`}>
  <Card className="hover:shadow-lg transition-shadow"
          key={pkg.fileName}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="mb-2">{pkg.kitConfig.name}</CardTitle>
                        <div className="flex gap-2 mb-2">
                          <Badge variant="secondary">{pkg.kitConfig.owner}</Badge>
                          <Badge variant="outline">{pkg.kitConfig.version}</Badge>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="mb-4">
                      {pkg.kitConfig.description || 
                       `Package ID: ${pkg.kitConfig.id}`}
                    </CardDescription>
                    <div className="flex gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Package className="h-4 w-4" />
                        {Object.keys(pkg.kitConfig.workflows || {}).length} workflows
                      </div>
                      <div className="flex items-center gap-1">
                        <FileCode className="h-4 w-4" />
                        {pkg.kitConfig.dependencies?.length || 0} dependencies
                      </div>
                      <div className="flex items-center gap-1 ml-auto">
                        <time className="text-xs text-muted-foreground" dateTime={pkg.uploadedAt}>
                          {new Date(pkg.uploadedAt).toLocaleDateString()}
                        </time>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default HomePage;