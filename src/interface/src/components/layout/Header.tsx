import React from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { User } from 'lucide-react';
import Logo from "../../assets/logo.svg?react";

const Header = () => {
  return (
    <header className="h-12 border-b border-gray-800 flex items-center px-4 justify-between  shrink-0">
      <div className="flex items-center gap-4    ">
        <div className="flex items-center gap-2">
          
            <img src='/logo.png' className='h-8 w-8'/>
        
          <span className="text-md text-white">Cartograph</span>
        </div>
        <Input 
          className="w-64 h-8 bg-background-secondary border-gray-800" 
          placeholder="search public/private/etc blocks"
        />
       
      </div>
      <div className="flex items-center gap-4">
        <Button variant="destructive" size="sm">
          Save
        </Button>
        <Button variant="outline" size="sm" className='text-black'>
          Release
        </Button>
      </div>
    </header>
  );
};

export default Header;