"use client"
import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { ArrowRight, Code, Database, GitBranch, Layers, Share2, SquareCode } from 'lucide-react';
import ModuleAnimation from '../components/ModuleAnimation';
// Animation variants
const fadeIn = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.6 }
  }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const slideIn = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.5 }
  }
};

export default function DocsLandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      {/* Hero Section */}
      <section className="relative py-20 md:py-28 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <div className="absolute top-0 right-0 w-1/3 h-1/3 bg-gradient-to-br from-blue-500/10 to-purple-500/10 blur-3xl"></div>
          <div className="absolute bottom-0 left-0 w-1/3 h-1/3 bg-gradient-to-tr from-teal-500/10 to-blue-500/10 blur-3xl"></div>
        </div>
       

        <div className="container mx-auto px-4 relative z-10">
          <motion.div 
            className="flex flex-col items-center text-center"
            initial="hidden"
            animate="visible"
            variants={staggerContainer}
          >
            <motion.div variants={fadeIn} className="mb-6">
              <Image 
                src="/logo.png" 
                alt="Genbase Logo" 
                width={80} 
                height={80} 
                className="mx-auto"
              />
            </motion.div>
            
            <motion.h1 
              variants={fadeIn}
              className="text-4xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6"
            >
              AI Agents Working Together<br />
              <span className="text-blue-600 dark:text-blue-400">Solving Real Problems</span>
            </motion.h1>
            
            <motion.p 
              variants={fadeIn}
              className="text-lg md:text-xl text-gray-600 dark:text-gray-300 max-w-3xl mb-8"
            >
              Genbase is a modular platform where specialized AI agents collaborate on your projects.
              Instead of one AI trying to do everything, Genbase lets you combine AI modules 
              with deep domain expertise that work together through shared repositories.
            </motion.p>
            
            <motion.div 
              variants={fadeIn}
              className="flex flex-col sm:flex-row gap-4"
            >
              <Link 
                href="/docs/overview/getting-started" 
                className="group px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                Get Started 
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link 
                href="/docs/overview/concepts" 
                className="px-6 py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-800 dark:text-white border border-gray-200 dark:border-gray-700 font-medium rounded-lg transition-colors"
              >
                Explore Core Concepts
              </Link>
            </motion.div>
          </motion.div>
        </div>

  
      </section>

<section>  <ModuleAnimation/> </section>
      {/* What is Genbase - With Code Example */}
      <section className="py-20 bg-gray-50 dark:bg-gray-900">
        <div className="container mx-auto px-4">
          <motion.div 
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={staggerContainer}
            className="max-w-6xl mx-auto"
          >
            <motion.div variants={fadeIn} className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
                What Makes Genbase Different
              </h2>
              <p className="text-lg text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
                {"Genbase doesn't just generate code—it creates modular, collaborative AI workflows that truly understand your domain."}
              </p>
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <motion.div variants={slideIn} className="space-y-6">
                <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3 flex items-center">
                    <span className="flex items-center justify-center w-8 h-8 bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded-full mr-3">1</span>
                    Specialized Knowledge, Not Generic AI
                  </h3>
                  <p className="text-gray-600 dark:text-gray-300 mb-4">
                    Instead of one AI struggling to know everything, Genbase modules 
                    have deep expertise in specific domains. A Next.js agent actually
                    understands framework-specific patterns, while a PostgreSQL agent 
                    knows database optimization.
                  </p>
                </div>

                <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3 flex items-center">
                    <span className="flex items-center justify-center w-8 h-8 bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded-full mr-3">2</span>
                    Modules Working Together
                  </h3>
                  <p className="text-gray-600 dark:text-gray-300 mb-4">
                    Genbase modules communicate through structured relationships.
                    A web development module can request database operations from a 
                    PostgreSQL module without needing to understand database internals.
                    This mimics how real teams collaborate.
                  </p>
                </div>

                <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3 flex items-center">
                    <span className="flex items-center justify-center w-8 h-8 bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded-full mr-3">3</span>
                    Actual Environment Control
                  </h3>
                  <p className="text-gray-600 dark:text-gray-300">
                    Unlike chat-based AIs limited to text, Genbase agents operate on 
                    Git repositories with full access to run commands, modify files, 
                    test code, and work like real developers in a real environment.
                  </p>
                </div>
              </motion.div>

              <motion.div 
                variants={fadeIn}
                className="relative rounded-xl shadow-xl overflow-hidden"
              >
                       <div className='px-8 py-8 bg-cyan-600 rounded-xl shadow-xl border border-gray-100 dark:border-gray-700'>
                <Image 
                  src="/module.png" 
                  alt="Genbase Dashboard Interface" 
                  width={600} 
                  height={400} 
                  className="w-full  rounded-xl border "/>
         </div>
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-6">
                  <p className="text-white text-lg font-bold">Genbase module dashboard showing active workflows and module relationships</p>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* How It Works - Visual Flow */}
      <section className="py-20 bg-white dark:bg-gray-950">
        <div className="container mx-auto px-4">
          <motion.div 
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={staggerContainer}
          >
            <motion.div variants={fadeIn} className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
                How Genbase Works
              </h2>
              <p className="text-lg text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
                From selecting specialized modules to building complete solutions with AI collaboration
              </p>
            </motion.div>

            <div className="max-w-5xl mx-auto">
              {/* Step 1 */}
              <motion.div 
                variants={fadeIn}
                className="grid grid-cols-1 md:grid-cols-12 gap-8 mb-12 items-center"
              >
                <div className="md:col-span-4 flex md:justify-end">
                  <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 text-2xl font-bold">1</div>
                </div>
                <div className="md:col-span-8">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Select Specialized Modules</h3>
                  <p className="text-gray-600 dark:text-gray-300">
                    Choose from a library of domain-specific modules in the Genbase Registry.
                    Each module contains agents with deep expertise in areas like Next.js development,
                    PostgreSQL management, or Docker deployment.
                  </p>
                </div>
              </motion.div>

              {/* Connector */}
              <motion.div 
                variants={fadeIn}
                className="flex justify-center  md:pr-8 my-4"
              >
                <div className="h-12 w-0.5 bg-gray-200 dark:bg-gray-700"></div>
              </motion.div>

              {/* Step 2 */}
              <motion.div 
                variants={fadeIn}
                className="grid grid-cols-1 md:grid-cols-12 gap-8 mb-12 items-center"
              >
                <div className="md:col-span-4 flex md:justify-end">
                  <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 text-2xl font-bold">2</div>
                </div>
                <div className="md:col-span-8">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Define Module Relationships</h3>
                  <p className="text-gray-600 dark:text-gray-300">
                    Connect modules through well-defined relationships that determine how they work together.
                    A web module can invoke database operations from a PostgreSQL module, or a Docker module
                    can access code from development modules to build containers.
                  </p>
                </div>
              </motion.div>

              {/* Connector */}
              <motion.div 
                variants={fadeIn}
                className="flex justify-center  md:pr-8 my-4"
              >
                <div className="h-12 w-0.5 bg-gray-200 dark:bg-gray-700"></div>
              </motion.div>

              {/* Step 3 */}
              <motion.div 
                variants={fadeIn}
                className="grid grid-cols-1 md:grid-cols-12 gap-8 mb-12 items-center"
              >
                <div className="md:col-span-4 flex md:justify-end">
                  <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 text-2xl font-bold">3</div>
                </div>
                <div className="md:col-span-8">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Interact Through Purpose-Built Workflows</h3>
                  <p className="text-gray-600 dark:text-gray-300">
                    Instead of generic chat interfaces, Genbase provides specialized workflows 
                    for specific tasks. A development workflow connects you with an agent that 
                    understands the exact development task, with all the context and tools needed.
                  </p>
                </div>
              </motion.div>

              {/* Connector */}
              <motion.div 
                variants={fadeIn}
                className="flex justify-center  md:pr-8 my-4"
              >
                <div className="h-12 w-0.5 bg-gray-200 dark:bg-gray-700"></div>
              </motion.div>

              {/* Step 4 */}
              <motion.div 
                variants={fadeIn}
                className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center"
              >
                <div className="md:col-span-4 flex md:justify-end">
                  <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 text-2xl font-bold">4</div>
                </div>
                <div className="md:col-span-8">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">AI Agents Collaborate on Real Workspaces</h3>
                  <p className="text-gray-600 dark:text-gray-300">
                    Genbase agents work in Git repositories with full environment access.
                    They generate code, run tests, execute commands, and collaborate to
                    solve complex problems—just like a real development team.
                  </p>
                </div>
              </motion.div>
            </div>

            <motion.div variants={fadeIn} className="flex justify-center mt-12">
              <Link 
                href="/docs/overview/architecture" 
                className="group px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors inline-flex items-center gap-2"
              >
                Explore Technical Architecture 
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </Link>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Module Registry */}
      <section className="py-20 bg-gray-50 dark:bg-gray-900 overflow-hidden">
        <div className="container mx-auto px-4">
          <motion.div 
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={staggerContainer}
          >
            <motion.div variants={fadeIn} className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
                Discover Specialized Modules
              </h2>
              <p className="text-lg text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
                Browse the Genbase Registry for ready-to-use AI modules
              </p>
            </motion.div>
            
            <motion.div 
              variants={fadeIn}
              className="mb-16 max-w-5xl mx-auto"
            >
              <div className='px-8 py-8 bg-purple-800 rounded-xl shadow-xl border border-gray-100 dark:border-gray-700'>
              <Image 
                src="/registry.png" 
                alt="Genbase Module Registry" 
                width={1000}
                height={600}
                className="w-full rounded-xl shadow-lg border border-gray-200 dark:border-gray-700"
              />
              </div>
            </motion.div>
            
            <motion.div variants={fadeIn} className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
                Real-World Applications
              </h2>
              <p className="text-lg text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
                See how specialized modules work together to solve complex problems
              </p>
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 max-w-6xl mx-auto">
              {/* Example 1 */}
              <motion.div 
                variants={slideIn}
                className="bg-white dark:bg-gray-800 rounded-2xl overflow-hidden shadow-md"
              >
                <div className="p-1 bg-gradient-to-r from-blue-500 to-teal-500"></div>
                <div className="p-8">
                  <div className="flex items-center mb-4">
                    <SquareCode className="w-8 h-8 text-blue-500 mr-3" />
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Full-Stack Web Application</h3>
                  </div>
                  
                  <p className="text-gray-600 dark:text-gray-300 mb-6">
                    Building a complex e-commerce platform with multiple specialized agents working in concert:
                  </p>
                  
                  <div className="space-y-4 mb-6">
                    <div className="flex items-start">
                      <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex-shrink-0 flex items-center justify-center text-blue-600 dark:text-blue-400 mr-4">
                        <Code size={20} />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white mb-1">Next.js Developer Module</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-300">
                          Generates frontend components with React Server Components, handles routing and state management
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-start">
                      <div className="w-10 h-10 rounded-full bg-teal-100 dark:bg-teal-900/30 flex-shrink-0 flex items-center justify-center text-teal-600 dark:text-teal-400 mr-4">
                        <Database size={20} />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white mb-1">PostgreSQL Administrator Module</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-300">
                          Designs normalized schema, creates optimized queries, exposes functions for data operations
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-start">
                      <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex-shrink-0 flex items-center justify-center text-purple-600 dark:text-purple-400 mr-4">
                        <GitBranch size={20} />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white mb-1">Docker Deployment Module</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-300">
                          Creates containerization setup, configures multi-stage builds, optimizes for production
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-gray-50 dark:bg-gray-900/50 p-4 rounded-lg border border-gray-100 dark:border-gray-700">
                    <h4 className="font-medium text-gray-900 dark:text-white mb-2">How They Work Together:</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      The Next.js module creates frontend components that call backend APIs. When database 
                      operations are needed, it invokes actions from the PostgreSQL module to create 
                      optimized queries. The Docker module builds containers for both services, coordinating
                      the deployment pipeline.
                    </p>
                  </div>
                </div>
              </motion.div>

              {/* Example 2 */}
              <motion.div 
                variants={slideIn}
                className="bg-white dark:bg-gray-800 rounded-2xl overflow-hidden shadow-md"
              >
                <div className="p-1 bg-gradient-to-r from-purple-500 to-pink-500"></div>
                <div className="p-8">
                  <div className="flex items-center mb-4">
                    <Layers className="w-8 h-8 text-purple-500 mr-3" />
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">API Integration Platform</h3>
                  </div>
                  
                  <p className="text-gray-600 dark:text-gray-300 mb-6">
                    Creating a system that integrates multiple third-party services with custom business logic:
                  </p>
                  
                  <div className="space-y-4 mb-6">
                    <div className="flex items-start">
                      <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex-shrink-0 flex items-center justify-center text-blue-600 dark:text-blue-400 mr-4">
                        <Share2 size={20} />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white mb-1">API Designer Module</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-300">
                          Creates REST endpoints, handles authentication, generates API documentation
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-start">
                      <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/30 flex-shrink-0 flex items-center justify-center text-amber-600 dark:text-amber-400 mr-4">
                        <Layers size={20} />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white mb-1">Integration Service Module</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-300">
                          Handles data transformation, service connections, error handling across systems
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-start">
                      <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 flex-shrink-0 flex items-center justify-center text-green-600 dark:text-green-400 mr-4">
                        <Database size={20} />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white mb-1">Data Processing Module</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-300">
                          Transforms and enriches data, implements business logic, handles complex operations
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-gray-50 dark:bg-gray-900/50 p-4 rounded-lg border border-gray-100 dark:border-gray-700">
                    <h4 className="font-medium text-gray-900 dark:text-white mb-2">How They Work Together:</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      The API Designer creates endpoints that trigger functions in the Integration Service module. 
                      This module connects to external APIs and passes normalized data to the Data Processing module 
                      through action relationships. Each module has deep expertise in its domain, but shares capabilities
                      through the Genbase platform.
                    </p>
                  </div>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="py-20 bg-gradient-to-b from-blue-50 to-white dark:from-blue-950/30 dark:to-gray-950 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-gray-200 dark:via-gray-700 to-transparent"></div>
        
        <div className="container mx-auto px-4 relative z-10">
          <motion.div 
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={staggerContainer}
            className="max-w-4xl mx-auto"
          >
            <motion.div variants={fadeIn} className="bg-white dark:bg-gray-800 rounded-2xl p-8 md:p-12 shadow-xl border border-gray-100 dark:border-gray-700">
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                  Start Building with Genbase
                </h2>
                <p className="text-lg text-gray-600 dark:text-gray-300 mb-0 max-w-2xl mx-auto">
                  Combine specialized AI agents to create powerful, collaborative workflows for your next project
                </p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Link 
                  href="/docs/overview/getting-started" 
                  className="group bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 p-6 rounded-xl transition-colors flex flex-col"
                >
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2 flex items-center">
                    Getting Started
                    <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" />
                  </h3>
                  <p className="text-gray-600 dark:text-gray-300">
                    Quick setup guide to start your first Genbase project with sample modules
                  </p>
                </Link>
                
                <Link 
                  href="/docs/overview/concepts" 
                  className="group bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 p-6 rounded-xl transition-colors flex flex-col"
                >
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2 flex items-center">
                    Core Concepts
                    <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" />
                  </h3>
                  <p className="text-gray-600 dark:text-gray-300">
                    Understand modules, workflows, relations, and other key Genbase components
                  </p>
                </Link>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-white dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="md:col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <Image src="/logo.png" alt="Genbase Logo" width={32} height={32} />
                <span className="text-lg font-semibold text-gray-900 dark:text-white">Genbase</span>
              </div>
              <p className="text-gray-600 dark:text-gray-300 mb-4 max-w-md">
                An open platform where specialized AI agents collaborate on shared workspaces to solve complex development challenges.
              </p>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">Documentation</h3>
              <ul className="space-y-2">
                <li><Link href="/introduction" className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Introduction</Link></li>
                <li><Link href="/docs/overview/getting-started" className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Getting Started</Link></li>
                <li><Link href="/docs/overview/concepts" className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Core Concepts</Link></li>
                <li><Link href="/docs/overview/architecture" className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Architecture</Link></li>
              </ul>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">Resources</h3>
              <ul className="space-y-2">
                <li><a href="https://github.com/genbase-project/genbase" className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">GitHub</a></li>
                <li><a href="https://registry.genbase.io" className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Module Registry</a></li>
                <li><a href="https://github.com/genbase-project/genbase/discussions" className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Community</a></li>
              </ul>
            </div>
          </div>
          
          <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-800 text-center text-gray-500 dark:text-gray-400 text-sm">
            &copy; {new Date().getFullYear()} Genbase. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}