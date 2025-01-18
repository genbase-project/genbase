import React from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { User } from 'lucide-react';
import Logo from "../../assets/logo.svg?react";

const Header = () => {
  return (
    <header className="h-10 border-b flex items-center px-4 justify-between shrink-0">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <img src='/logo.png' className='h-6 w-6'/>
          <span className="text-sm font-semibold">CARTOGRAPH</span>
        </div>
        <Input 
          className="w-64 h-8" 
          placeholder="search public/private/etc blocks"
        />
      </div>
      <div className="flex items-center gap-4">
        <Button size="sm">
          Save
        </Button>
      </div>
    </header>
  );
};

export default Header;