import React from 'react';
import { ArrowRight, Box, Code2, Brain, Zap, GitFork, BookOpen, Circle } from 'lucide-react';
import Link from 'next/link';

const features = [
  {
    icon: <Brain className="h-6 w-6" />,
    title: "AI-First Design",
    description: "Built from the ground up for AI-controlled software systems with rich context management",
    gradient: "from-orange-100 to-amber-50"
  },
  {
    icon: <Box className="h-6 w-6" />,
    title: "Modular Architecture",
    description: "Create composable, reusable modules that work together seamlessly",
    gradient: "from-amber-50 to-orange-100"
  },
  {
    icon: <Code2 className="h-6 w-6" />,
    title: "Developer Friendly",
    description: "Intuitive APIs, comprehensive documentation, and powerful development tools",
    gradient: "from-orange-100 to-amber-50"
  },
  {
    icon: <Zap className="h-6 w-6" />,
    title: "Production Ready",
    description: "Enterprise-grade reliability with built-in monitoring and security",
    gradient: "from-amber-50 to-orange-100"
  }
];

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-50 to-white">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background Elements */}
        <div className="absolute inset-0">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-gradient-to-br from-orange-200 to-amber-100 opacity-20 blur-3xl" />
          <div className="absolute top-60 -left-40 w-80 h-80 rounded-full bg-gradient-to-br from-orange-200 to-amber-100 opacity-20 blur-3xl" />
        </div>
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24 sm:pb-32">
          <div className="text-center">
            <div className="inline-flex items-center px-4 py-2 rounded-full bg-gradient-to-r from-orange-100 to-amber-100 text-orange-800 text-sm mb-8">
              <Circle className="h-3 w-3 text-orange-500 mr-2 animate-pulse" />
              Now in Public Beta
            </div>
            
            <h1 className="text-4xl sm:text-6xl font-bold text-orange-900 mb-8 relative">
              <span className="relative">
                AI-First Software Architecture
                <div className="absolute -bottom-2 left-0 w-full h-1 bg-gradient-to-r from-orange-500 to-amber-500 transform skew-x-12" />
              </span>
            </h1>
            
            <p className="max-w-2xl mx-auto text-xl text-gray-600 mb-8">
              Build intelligent, self-managing software systems with context-aware AI agents and modular architecture
            </p>
            
            <div className="flex justify-center gap-4">
              <Link href="/docs" className="inline-flex items-center px-6 py-3 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 text-white hover:from-orange-600 hover:to-amber-600 transition-all duration-200 shadow-lg hover:shadow-xl hover:-translate-y-0.5">
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <a href="https://github.com/genbase-project/genbase" className="inline-flex items-center px-6 py-3 rounded-lg border border-orange-200 hover:border-orange-300 hover:bg-orange-50 transition-all duration-200">
                <GitFork className="mr-2 h-4 w-4 text-orange-600" />
                Star on GitHub
              </a>
            </div>
          </div>
          
          {/* Code Preview */}
          <div className="mt-16 max-w-3xl mx-auto transform hover:scale-[1.02] transition-transform duration-200">
            <div className="bg-gray-900 rounded-xl shadow-2xl overflow-hidden border border-orange-200/20">
              <div className="flex items-center space-x-2 px-4 py-3 border-b border-gray-800 bg-gray-800/50">
                <div className="w-3 h-3 bg-red-500 rounded-full" />
                <div className="w-3 h-3 bg-yellow-500 rounded-full" />
                <div className="w-3 h-3 bg-green-500 rounded-full" />
                <div className="ml-2 text-gray-400 text-sm">terminal</div>
              </div>
              <div className="p-4 space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2 text-gray-400 text-sm">
                    <span className="text-orange-400">$</span>
                    <span className="text-gray-100">hivon module create --kit web-service --name my-service</span>
                  </div>
                </div>
                <div className="space-y-2 border-l-2 border-orange-500/30 pl-4">
                  <div className="text-orange-400"> Check the service health and optimize configuration</div>
                  <div className="text-gray-300">Agent: I'll analyze the service and make improvements.</div>
                  <div className="text-gray-400 pl-2">1. Checking current metrics...</div>
                  <div className="text-gray-400 pl-2">2. Analyzing bottlenecks...</div>
                  <div className="text-gray-400 pl-2">3. Implementing optimizations...</div>
                </div>
                <div className="space-y-1 text-green-400/80">
                  <div>✓ Response time improved by 35%</div>
                  <div>✓ Resource usage optimized</div>
                  <div>✓ Monitoring configured</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <div 
              key={index} 
              className="group p-6 rounded-xl bg-gradient-to-br border border-orange-100 hover:border-orange-200 transition-all duration-200 hover:shadow-lg"
              style={{
                background: `linear-gradient(to bottom right, ${index % 2 === 0 ? '#fff5eb, #fff' : '#fff, #fff5eb'})`
              }}
            >
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center text-white mb-4 group-hover:scale-110 transition-transform duration-200">
                {feature.icon}
              </div>
              <h3 className="text-lg font-semibold text-orange-900 mb-2">{feature.title}</h3>
              <p className="text-gray-600">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Documentation Preview */}
      <div className="bg-gradient-to-b from-white to-orange-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-orange-900 mb-4">Comprehensive Documentation</h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Everything you need to build powerful AI-controlled systems
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: <BookOpen className="h-6 w-6" />,
                title: "Getting Started",
                description: "Quick start guide to create your first AI-controlled module",
                path: "/docs/getting-started"
              },
              {
                icon: <Brain className="h-6 w-6" />,
                title: "Core Concepts",
                description: "Understanding the fundamental building blocks of Hivon",
                path: "/docs/core-concepts"
              },
              {
                icon: <Box className="h-6 w-6" />,
                title: "Architecture",
                description: "Deep dive into Hivon's technical architecture and design",
                path: "/docs/architecture"
              }
            ].map((item, index) => (
              <Link 
                key={index}
                href={item.path} 
                className="group block p-6 rounded-xl bg-white border border-orange-100 hover:border-orange-200 transition-all duration-200 hover:shadow-lg hover:-translate-y-1"
              >
                <div className="flex items-center mb-4">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center text-white group-hover:scale-110 transition-transform duration-200">
                    {item.icon}
                  </div>
                  <h3 className="ml-3 font-semibold text-orange-900">{item.title}</h3>
                </div>
                <p className="text-gray-600">{item.description}</p>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Call to Action */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <div className="relative">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-32 h-32 rounded-full bg-gradient-to-br from-orange-200 to-amber-100 opacity-20 blur-2xl" />
          </div>
          <div className="relative">
            <h2 className="text-3xl font-bold text-orange-900 mb-4">Ready to Get Started?</h2>
            <p className="text-gray-600 max-w-2xl mx-auto mb-8">
              Join the community and start building intelligent, self-managing software systems today
            </p>
            <div className="flex justify-center gap-4">
              <Link href="/docs" className="inline-flex items-center px-6 py-3 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 text-white hover:from-orange-600 hover:to-amber-600 transition-all duration-200 shadow-lg hover:shadow-xl hover:-translate-y-0.5">
                Read the Docs
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <a href="https://discord.gg/hivon" className="inline-flex items-center px-6 py-3 rounded-lg border border-orange-200 hover:border-orange-300 hover:bg-orange-50 transition-all duration-200">
                Join Discord
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;