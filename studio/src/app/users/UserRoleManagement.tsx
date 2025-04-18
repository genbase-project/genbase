// src/users/UserRoleManagement.tsx
import React, { useState, useEffect } from 'react';
import { fetchWithAuth, ENGINE_BASE_URL } from '@/config';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogClose,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Badge } from '@/components/ui/badge';

// Types for role management
interface UserRolesResponse {
    user_id: string;
    roles: string[];
}

interface RoleAssignmentResponse {
    status: string;
    message: string;
    roles: string[];
}

interface UserRoleManagementProps {
    userId: string;
    userEmail: string; // Display purposes
    onRolesUpdated?: (roles: string[]) => void;
}

const UserRoleManagement: React.FC<UserRoleManagementProps> = ({ userId, userEmail, onRolesUpdated }) => {
    // State
    const [userRoles, setUserRoles] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [selectedRole, setSelectedRole] = useState<string>("");
    const [availableRoles] = useState<string[]>(["admin", "viewer"]); // Hardcoded for now, could be fetched
    const { toast } = useToast();

    // Fetch user roles when dialog opens
    const fetchUserRoles = async () => {
        setIsLoading(true);
        try {
            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/authz/users/${userId}/roles`);
            if (response.ok) {
                const data: UserRolesResponse = await response.json();
                setUserRoles(data.roles);
                if (onRolesUpdated) {
                    onRolesUpdated(data.roles);
                }
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch user roles' }));
                throw new Error(errorData.detail || 'Failed to fetch user roles');
            }
        } catch (error: any) {
            console.error('Error fetching user roles:', error);
            toast({
                title: 'Error',
                description: error.message || 'Could not load user roles.',
                variant: 'destructive',
            });
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (isDialogOpen) {
            fetchUserRoles();
        }
    }, [isDialogOpen]);

    // Assign role
    const handleAssignRole = async () => {
        if (!selectedRole) {
            toast({
                title: 'Error',
                description: 'Please select a role to assign.',
                variant: 'destructive',
            });
            return;
        }

        setIsLoading(true);
        try {
            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/authz/users/${userId}/roles`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role: selectedRole }),
            });

            if (response.ok) {
                const data: RoleAssignmentResponse = await response.json();
                setUserRoles(data.roles);
                if (onRolesUpdated) {
                    onRolesUpdated(data.roles);
                }
                toast({
                    title: 'Success',
                    description: `Role '${selectedRole}' assigned successfully.`,
                });
                setSelectedRole("");
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to assign role' }));
                throw new Error(errorData.detail || 'Failed to assign role');
            }
        } catch (error: any) {
            console.error('Error assigning role:', error);
            toast({
                title: 'Error',
                description: error.message || 'Could not assign role.',
                variant: 'destructive',
            });
        } finally {
            setIsLoading(false);
        }
    };

    // Revoke role
    const handleRevokeRole = async (role: string) => {
        setIsLoading(true);
        try {
            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/authz/users/${userId}/roles/${role}`, {
                method: 'DELETE',
            });

            if (response.ok) {
                // If the backend returns updated roles as part of response
                try {
                    const data: RoleAssignmentResponse = await response.json();
                    setUserRoles(data.roles);
                    if (onRolesUpdated) {
                        onRolesUpdated(data.roles);
                    }
                } catch (e) {
                    // If no JSON response, just refetch roles
                    await fetchUserRoles();
                }
                
                toast({
                    title: 'Success',
                    description: `Role '${role}' revoked successfully.`,
                });
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to revoke role' }));
                throw new Error(errorData.detail || 'Failed to revoke role');
            }
        } catch (error: any) {
            console.error('Error revoking role:', error);
            toast({
                title: 'Error',
                description: error.message || 'Could not revoke role.',
                variant: 'destructive',
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
                <Button 
                    variant="outline" 
                    size="sm" 
                    className="text-indigo-600 border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
                >
                    Manage Roles
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px] text-neutral-900">
                <DialogHeader>
                    <DialogTitle>Manage User Roles</DialogTitle>
                    <DialogDescription className="text-gray-400">
                        Assign or revoke roles for user: <span className="font-medium text-indigo-600">{userEmail}</span>
                    </DialogDescription>
                </DialogHeader>

                {isLoading && userRoles.length === 0 ? (
                    <div className="py-6 flex justify-center">
                        <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                    </div>
                ) : (
                    <>
                        {/* Current Roles */}
                        <div className="space-y-4 py-2">
                            <div className="font-medium">Current Roles:</div>
                            <div className="flex flex-wrap gap-2">
                                {userRoles.length === 0 ? (
                                    <p className="text-sm text-gray-500 italic">No roles assigned</p>
                                ) : (
                                    userRoles.map(role => (
                                        <div key={role} className="flex items-center space-x-1">
                                            <Badge 
                                                variant="secondary" 
                                                className="px-2 py-1 bg-indigo-100 text-indigo-800 border border-indigo-200"
                                            >
                                                {role}
                                            </Badge>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-6 w-6 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                                                onClick={() => handleRevokeRole(role)}
                                                disabled={isLoading}
                                            >
                                                <XCircle className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Assign New Role */}
                        <div className="space-y-4 py-2 border-t border-gray-100 mt-2 pt-4">
                            <div className="font-medium">Assign New Role:</div>
                            <div className="flex space-x-2">
                                <Select
                                    value={selectedRole}
                                    onValueChange={setSelectedRole}
                                    disabled={isLoading}
                                >
                                    <SelectTrigger className="w-[180px] focus:ring-indigo-500">
                                        <SelectValue placeholder="Select role" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {availableRoles
                                            .filter(role => !userRoles.includes(role))
                                            .map(role => (
                                                <SelectItem key={role} value={role}>
                                                    {role}
                                                </SelectItem>
                                            ))}
                                        {availableRoles.every(role => userRoles.includes(role)) && (
                                            <SelectItem value="no-roles" disabled>
                                                All roles assigned
                                            </SelectItem>
                                        )}
                                    </SelectContent>
                                </Select>
                                <Button
                                    onClick={handleAssignRole}
                                    disabled={isLoading || !selectedRole}
                                    className="bg-indigo-600 hover:bg-indigo-700 text-white"
                                >
                                    {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4 mr-1" />}
                                    Assign
                                </Button>
                            </div>
                        </div>
                    </>
                )}

                <DialogFooter className="mt-4 pt-2 border-t border-gray-100">
                    <DialogClose asChild>
                        <Button variant="outline">Close</Button>
                    </DialogClose>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default UserRoleManagement;