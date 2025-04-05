// src/settings/SettingsSidebar.tsx
import React from 'react';
import { NavLink } from 'react-router-dom';
import { Sidebar, DatabaseZap, KeyRound } from 'lucide-react'; // Import KeyRound icon
import { Button } from '@/components/ui/button';
import { SidebarHeader } from '@/components/ui/sidebar';

interface SettingsSidebarProps {
    onCollapse: () => void;
}

const SettingsSidebar: React.FC<SettingsSidebarProps> = ({ onCollapse }) => {

    const settingsNavItems = [
        { name: 'Model', path: '/settings/model', icon: <DatabaseZap size={18} /> },
        { name: 'Password & Security', path: '/settings/security', icon: <KeyRound size={18} /> },
    ];

    return (
        // Use theme variables: bg-muted for slightly off-white, foreground text
        <div className="flex flex-col h-full text-foreground bg-neutral-50">
            {/* Use theme variables for header: muted background (slightly transparent), border, foreground text */}
            <SidebarHeader className="px-3 py-4 flex flex-row justify-between items-center backdrop-blur-sm  border-b border-border flex-shrink-0">
                <div className="flex flex-row items-center space-x-2">
                    <h2 className="text-lg font-medium text-foreground">Settings</h2>
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onCollapse}
                    // Use theme variables for collapse button: muted text, accent background/text on hover
                    className="h-8 w-8 rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    aria-label="Collapse sidebar"
                >
                    <Sidebar size={16} />
                </Button>
            </SidebarHeader>

            {/* Navigation links */}
            <nav className="flex-1 overflow-y-auto p-3 space-y-1">
                {settingsNavItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) =>
                            `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors  ${
                                isActive
                                    // Active: Accent background and text
                                    ? 'bg-accent bg-neutral-200'
                                    : 'text-muted-foreground hover:bg-accent hover:bg-neutral-200'
                            }`
                        }
                    >
                        {item.icon}
                        <span>{item.name}</span>
                    </NavLink>
                ))}
            </nav>
        </div>
    );
};

export default SettingsSidebar;