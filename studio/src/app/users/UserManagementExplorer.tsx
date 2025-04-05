// src/users/UserManagementExplorer.tsx
import React from 'react';
import { NavLink } from 'react-router-dom';
import { Sidebar, Users as UsersIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SidebarHeader } from '@/components/ui/sidebar';

interface UserManagementExplorerProps {
    onCollapse: () => void;
}

const UserManagementExplorer: React.FC<UserManagementExplorerProps> = ({ onCollapse }) => {

    const userManagementNavItems = [
        { name: 'Users', path: '/users', icon: <UsersIcon size={18} /> },
    ];

    return (
        // Explorer uses muted background, standard foreground text
        <div className="flex flex-col h-full text-foreground bg-neutral-50">
            {/* Header uses muted background (slightly transparent), border */}
            <SidebarHeader className="px-3 py-4 flex flex-row justify-between items-center backdrop-blur-sm bg-muted/90 border-b border-border flex-shrink-0">
                <div className="flex flex-row items-center space-x-2">
                    <h2 className="text-lg font-medium text-foreground">Users & Access</h2>
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onCollapse}
                     // Collapse button: Muted text, Accent background/text on hover
                    className="h-8 w-8 rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    aria-label="Collapse sidebar"
                >
                    <Sidebar size={16} />
                </Button>
            </SidebarHeader>

            {/* Navigation links */}
            <nav className="flex-1 overflow-y-auto p-3 space-y-1 bg-neutral-50">
                {userManagementNavItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        end
                        className={({ isActive }) =>
                            `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium hover:bg-neutral-200 transition-colors ${
                                isActive
                                    // Active: Accent background and text
                                    ? 'bg-accent text-accent-foreground'
                                    // Inactive: Muted text, Accent background/text on hover
                                    // NOTE: Background hover might not be visible if accent/muted colors are the same! Text change is key.
                                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
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

export default UserManagementExplorer;