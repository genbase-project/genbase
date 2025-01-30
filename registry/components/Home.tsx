import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Download, Star, GitFork } from 'lucide-react';

const HomePage = () => {
  const featuredModules = [
    {
      name: 'Text Summarizer',
      description: 'Advanced text summarization using transformer models',
      category: 'NLP',
      downloads: '125K',
      stars: 842,
      forks: 124
    },
    {
      name: 'Image Classifier',
      description: 'Pre-trained vision models for image classification',
      category: 'Computer Vision',
      downloads: '98K',
      stars: 756,
      forks: 89
    },
    {
      name: 'Data Cleaner',
      description: 'Intelligent data cleaning and preprocessing pipeline',
      category: 'Data Processing',
      downloads: '78K',
      stars: 654,
      forks: 76
    }
  ];

  const categories = [
    { name: 'Natural Language Processing', count: 1243 },
    { name: 'Computer Vision', count: 856 },
    { name: 'Speech Recognition', count: 432 },
    { name: 'Reinforcement Learning', count: 321 },
    { name: 'Data Processing', count: 765 },
    { name: 'Model Optimization', count: 543 }
  ];

  return (
    <div className="min-h-screen bg-background">
      <section className="py-12 px-4 text-center bg-muted/30">
        <div className="container mx-auto max-w-4xl">
          <h1 className="text-4xl font-bold mb-4">
            Discover AI Modules for Your Next Project
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            A registry of interconnectable AI modules to enhance your applications
          </p>
        </div>
      </section>

      <main className="container mx-auto py-12 px-4">
        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-6">Featured Modules</h2>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {featuredModules.map((module) => (
              <Card key={module.name}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="mb-2">{module.name}</CardTitle>
                      <Badge variant="secondary">{module.category}</Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="mb-4">{module.description}</CardDescription>
                  <div className="flex gap-4 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Download className="h-4 w-4" />
                      {module.downloads}
                    </div>
                    <div className="flex items-center gap-1">
                      <Star className="h-4 w-4" />
                      {module.stars}
                    </div>
                    <div className="flex items-center gap-1">
                      <GitFork className="h-4 w-4" />
                      {module.forks}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-6">Browse by Category</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {categories.map((category) => (
              <Card key={category.name} className="hover:bg-muted/50 transition-colors cursor-pointer">
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-lg">{category.name}</CardTitle>
                    <Badge variant="secondary">{category.count}</Badge>
                  </div>
                </CardHeader>
              </Card>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
};

export default HomePage;