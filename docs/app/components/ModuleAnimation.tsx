// components/ModuleAnimation.js
"use client"

import React from 'react';
import { motion } from 'framer-motion';

const ModuleAnimation = () => {
  return (
    <section className="py-16 bg-gray-50 dark:bg-gray-900 overflow-hidden">
      <div className="container mx-auto px-4">
        <motion.div 
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: 1,
              transition: {
                staggerChildren: 0.1
              }
            }
          }}
          className="max-w-5xl mx-auto"
        >
          <motion.div 
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { 
                opacity: 1, 
                y: 0,
                transition: { duration: 0.6 }
              }
            }} 
            className="text-center mb-12"
          >
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              AI Agents Working Together
            </h2>
            <p className="text-lg text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
              See how Genbase modules communicate and share data through intelligent collaboration
            </p>
          </motion.div>
          
          <motion.div 
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { 
                opacity: 1, 
                y: 0,
                transition: { duration: 0.6 }
              }
            }}
            className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden"
          >
            {/* The SVG is directly embedded with dangerouslySetInnerHTML, but in a real implementation 
                you'd likely use Next.js public folder or a separate SVG file */}
            <div 
              dangerouslySetInnerHTML={{ 
                __html: `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500">
  <!-- Background gradient -->
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f0f9ff" />
      <stop offset="100%" stop-color="#e6f7ff" />
    </linearGradient>
    
    <!-- Module gradients -->
    <linearGradient id="moduleGradient1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3b82f6" />
      <stop offset="100%" stop-color="#60a5fa" />
    </linearGradient>
    
    <linearGradient id="moduleGradient2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10b981" />
      <stop offset="100%" stop-color="#34d399" />
    </linearGradient>
    
    <linearGradient id="moduleGradient3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8b5cf6" />
      <stop offset="100%" stop-color="#a78bfa" />
    </linearGradient>
    
    <!-- Data particle gradients -->
    <linearGradient id="dataGradient1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3b82f6" />
      <stop offset="100%" stop-color="#93c5fd" />
    </linearGradient>
    
    <linearGradient id="dataGradient2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10b981" />
      <stop offset="100%" stop-color="#6ee7b7" />
    </linearGradient>
    
    <linearGradient id="dataGradient3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8b5cf6" />
      <stop offset="100%" stop-color="#c4b5fd" />
    </linearGradient>
    
    <!-- Connection paths -->
    <path id="path1" d="M220,250 C300,180 380,180 450,240" fill="none" />
    <path id="path2" d="M450,260 C380,320 300,320 220,250" fill="none" />
    <path id="path3" d="M550,250 C620,190 690,190 700,240" fill="none" />
    <path id="path4" d="M700,260 C690,310 620,310 550,250" fill="none" />
    <path id="path5" d="M280,140 C350,100 450,100 520,140" fill="none" />
    <path id="path6" d="M520,360 C450,400 350,400 280,360" fill="none" />
    
    <!-- Filters -->
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="5" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
    
    <!-- Animation patterns -->
    <pattern id="gridPattern" patternUnits="userSpaceOnUse" width="30" height="30" patternTransform="rotate(0)">
      <line x1="0" y1="0" x2="0" y2="30" stroke="#3b82f620" stroke-width="1" />
      <line x1="0" y1="0" x2="30" y2="0" stroke="#3b82f620" stroke-width="1" />
    </pattern>
  </defs>

  <!-- Background -->
  <rect width="800" height="500" fill="url(#bgGradient)" />
  <rect width="800" height="500" fill="url(#gridPattern)" />
  
  <!-- Central Hub -->
  <circle cx="400" cy="250" r="60" fill="white" stroke="#e2e8f0" stroke-width="2" filter="url(#glow)" />
  <circle cx="400" cy="250" r="50" fill="white" stroke="#e2e8f0" stroke-width="2" />
  
  <!-- Central Hub Icon -->
  <g transform="translate(375, 225)">
    <rect x="0" y="0" width="50" height="50" rx="10" fill="white" stroke="#3b82f6" stroke-width="2" />
    <circle cx="25" cy="25" r="15" fill="#3b82f610" stroke="#3b82f6" stroke-width="2" />
    <circle cx="25" cy="25" r="5" fill="#3b82f6" />
    
    <!-- Animated pulse -->
    <circle cx="25" cy="25" r="23" fill="none" stroke="#3b82f640" stroke-width="2">
      <animate attributeName="r" values="15;25;15" dur="3s" repeatCount="indefinite" />
      <animate attributeName="stroke-opacity" values="0.6;0.2;0.6" dur="3s" repeatCount="indefinite" />
    </circle>
  </g>
  
  <!-- Modules -->
  <!-- Module 1 - Web Development -->
  <g transform="translate(120, 180)">
    <rect x="0" y="0" width="100" height="140" rx="15" fill="white" stroke="#e2e8f0" stroke-width="2" filter="url(#glow)" />
    <rect x="5" y="5" width="90" height="130" rx="10" fill="white" stroke="url(#moduleGradient1)" stroke-width="2" />
    
    <!-- Module 1 Icon -->
    <rect x="25" y="20" width="50" height="40" rx="5" fill="#3b82f610" stroke="#3b82f6" stroke-width="2" />
    <line x1="35" y1="35" x2="65" y2="35" stroke="#3b82f6" stroke-width="2" />
    <line x1="35" y1="45" x2="55" y2="45" stroke="#3b82f6" stroke-width="2" />
    
    <!-- Module 1 Text -->
    <text x="50" y="85" font-family="Arial" font-size="12" text-anchor="middle" fill="#1e3a8a">Web Dev</text>
    <text x="50" y="105" font-family="Arial" font-size="12" text-anchor="middle" fill="#1e3a8a">Module</text>
    
    <!-- Animated indicator light -->
    <circle cx="25" cy="120" r="5" fill="#3b82f6">
      <animate attributeName="opacity" values="0.5;1;0.5" dur="2s" repeatCount="indefinite" />
    </circle>
  </g>
  
  <!-- Module 2 - Database -->
  <g transform="translate(450, 180)">
    <rect x="0" y="0" width="100" height="140" rx="15" fill="white" stroke="#e2e8f0" stroke-width="2" filter="url(#glow)" />
    <rect x="5" y="5" width="90" height="130" rx="10" fill="white" stroke="url(#moduleGradient2)" stroke-width="2" />
    
    <!-- Module 2 Icon -->
    <circle cx="50" cy="40" r="20" fill="#10b98110" stroke="#10b981" stroke-width="2" />
    <path d="M40,40 L60,40 M40,32 L60,32 M40,48 L60,48" stroke="#10b981" stroke-width="2" stroke-linecap="round" />
    
    <!-- Module 2 Text -->
    <text x="50" y="85" font-family="Arial" font-size="12" text-anchor="middle" fill="#065f46">Database</text>
    <text x="50" y="105" font-family="Arial" font-size="12" text-anchor="middle" fill="#065f46">Module</text>
    
    <!-- Animated indicator light -->
    <circle cx="75" cy="120" r="5" fill="#10b981">
      <animate attributeName="opacity" values="0.5;1;0.5" dur="2.5s" repeatCount="indefinite" />
    </circle>
  </g>
  
  <!-- Module 3 - Deployment -->
  <g transform="translate(620, 180)">
    <rect x="0" y="0" width="100" height="140" rx="15" fill="white" stroke="#e2e8f0" stroke-width="2" filter="url(#glow)" />
    <rect x="5" y="5" width="90" height="130" rx="10" fill="white" stroke="url(#moduleGradient3)" stroke-width="2" />
    
    <!-- Module 3 Icon -->
    <rect x="30" y="20" width="40" height="40" rx="5" fill="#8b5cf610" stroke="#8b5cf6" stroke-width="2" />
    <path d="M30,35 L70,35 M50,20 L50,60" stroke="#8b5cf6" stroke-width="2" />
    
    <!-- Module 3 Text -->
    <text x="50" y="85" font-family="Arial" font-size="12" text-anchor="middle" fill="#5b21b6">Deployment</text>
    <text x="50" y="105" font-family="Arial" font-size="12" text-anchor="middle" fill="#5b21b6">Module</text>
    
    <!-- Animated indicator light -->
    <circle cx="25" cy="120" r="5" fill="#8b5cf6">
      <animate attributeName="opacity" values="0.5;1;0.5" dur="1.8s" repeatCount="indefinite" />
    </circle>
  </g>
  
  <!-- Connection Lines -->
  <path d="M220,220 C280,220 320,220 400,250" stroke="#3b82f640" stroke-width="2" stroke-dasharray="5,5" fill="none">
    <animate attributeName="stroke-dashoffset" from="10" to="0" dur="2s" repeatCount="indefinite" />
  </path>
  
  <path d="M400,250 C320,280 280,280 220,280" stroke="#3b82f640" stroke-width="2" stroke-dasharray="5,5" fill="none">
    <animate attributeName="stroke-dashoffset" from="0" to="10" dur="2s" repeatCount="indefinite" />
  </path>
  
  <path d="M400,250 C480,220 520,220 580,220" stroke="#10b98140" stroke-width="2" stroke-dasharray="5,5" fill="none">
    <animate attributeName="stroke-dashoffset" from="10" to="0" dur="2s" repeatCount="indefinite" />
  </path>
  
  <path d="M580,280 C520,280 480,280 400,250" stroke="#10b98140" stroke-width="2" stroke-dasharray="5,5" fill="none">
    <animate attributeName="stroke-dashoffset" from="0" to="10" dur="2s" repeatCount="indefinite" />
  </path>
  
  <path d="M580,220 C620,220 650,220 680,220" stroke="#8b5cf640" stroke-width="2" stroke-dasharray="5,5" fill="none">
    <animate attributeName="stroke-dashoffset" from="10" to="0" dur="2s" repeatCount="indefinite" />
  </path>
  
  <path d="M680,280 C650,280 620,280 580,280" stroke="#8b5cf640" stroke-width="2" stroke-dasharray="5,5" fill="none">
    <animate attributeName="stroke-dashoffset" from="0" to="10" dur="2s" repeatCount="indefinite" />
  </path>
  
  <!-- Data Flow Particles - Module 1 to Hub -->
  <g>
    <circle cx="0" cy="0" r="4" fill="url(#dataGradient1)">
      <animateMotion path="M220,220 C280,220 320,220 400,250" dur="2s" repeatCount="indefinite" />
    </circle>
    <circle cx="0" cy="0" r="6" fill="url(#dataGradient1)" opacity="0.3">
      <animateMotion path="M220,220 C280,220 320,220 400,250" dur="2s" begin="0.7s" repeatCount="indefinite" />
    </circle>
    <circle cx="0" cy="0" r="4" fill="url(#dataGradient1)">
      <animateMotion path="M220,220 C280,220 320,220 400,250" dur="2s" begin="1.4s" repeatCount="indefinite" />
    </circle>
  </g>
  
  <!-- Data Flow Particles - Hub to Module 1 -->
  <g>
    <circle cx="0" cy="0" r="4" fill="url(#dataGradient1)">
      <animateMotion path="M400,250 C320,280 280,280 220,280" dur="2s" repeatCount="indefinite" />
    </circle>
    <circle cx="0" cy="0" r="6" fill="url(#dataGradient1)" opacity="0.3">
      <animateMotion path="M400,250 C320,280 280,280 220,280" dur="2s" begin="0.7s" repeatCount="indefinite" />
    </circle>
  </g>
  
  <!-- Data Flow Particles - Hub to Module 2 -->
  <g>
    <circle cx="0" cy="0" r="4" fill="url(#dataGradient2)">
      <animateMotion path="M400,250 C480,220 520,220 580,220" dur="2s" repeatCount="indefinite" />
    </circle>
    <circle cx="0" cy="0" r="6" fill="url(#dataGradient2)" opacity="0.3">
      <animateMotion path="M400,250 C480,220 520,220 580,220" dur="2s" begin="0.5s" repeatCount="indefinite" />
    </circle>
  </g>
  
  <!-- Data Flow Particles - Module 2 to Hub -->
  <g>
    <circle cx="0" cy="0" r="4" fill="url(#dataGradient2)">
      <animateMotion path="M580,280 C520,280 480,280 400,250" dur="2s" repeatCount="indefinite" />
    </circle>
    <circle cx="0" cy="0" r="6" fill="url(#dataGradient2)" opacity="0.3">
      <animateMotion path="M580,280 C520,280 480,280 400,250" dur="2s" begin="1.2s" repeatCount="indefinite" />
    </circle>
  </g>
  
  <!-- Data Flow Particles - Module 2 to Module 3 -->
  <g>
    <circle cx="0" cy="0" r="4" fill="url(#dataGradient3)">
      <animateMotion path="M580,220 C620,220 650,220 680,220" dur="2s" repeatCount="indefinite" />
    </circle>
    <circle cx="0" cy="0" r="5" fill="url(#dataGradient3)" opacity="0.3">
      <animateMotion path="M580,220 C620,220 650,220 680,220" dur="2s" begin="0.8s" repeatCount="indefinite" />
    </circle>
  </g>
  
  <!-- Data Flow Particles - Module 3 to Module 2 -->
  <g>
    <circle cx="0" cy="0" r="4" fill="url(#dataGradient3)">
      <animateMotion path="M680,280 C650,280 620,280 580,280" dur="2s" repeatCount="indefinite" />
    </circle>
    <circle cx="0" cy="0" r="6" fill="url(#dataGradient3)" opacity="0.3">
      <animateMotion path="M680,280 C650,280 620,280 580,280" dur="2s" begin="0.5s" repeatCount="indefinite" />
    </circle>
  </g>
  
  <!-- Central hub pulse effect -->
  <circle cx="400" cy="250" r="60" fill="none" stroke="#3b82f620" stroke-width="4">
    <animate attributeName="r" values="60;70;60" dur="4s" repeatCount="indefinite" />
    <animate attributeName="stroke-opacity" values="0.2;0.1;0.2" dur="4s" repeatCount="indefinite" />
  </circle>
  
  <circle cx="400" cy="250" r="75" fill="none" stroke="#3b82f610" stroke-width="3">
    <animate attributeName="r" values="75;85;75" dur="4s" begin="1s" repeatCount="indefinite" />
    <animate attributeName="stroke-opacity" values="0.1;0.05;0.1" dur="4s" begin="1s" repeatCount="indefinite" />
  </circle>
  
  <!-- Text label for the illustration -->
  <text x="400" y="465" font-family="Arial" font-size="16" font-weight="bold" text-anchor="middle" fill="#1e3a8a">
    AI Agents Working Together in Genbase Modules
  </text>

</svg>
                `
              }}
              className="w-full h-full"
            />
          </motion.div>
          
          <motion.div 
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { 
                opacity: 1, 
                y: 0,
                transition: { duration: 0.6 }
              }
            }}
            className="mt-8 text-center"
          >
            
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
};

export default ModuleAnimation;