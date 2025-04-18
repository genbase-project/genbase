// src/users/UserManagementPage.tsx - Updated with Role Management
import React, { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth, ENGINE_BASE_URL } from '@/config';
import { UserRead, UserCreate, UserUpdate } from '@/types/schemas';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { PlusCircle, Edit, Trash2, Loader2, ShieldCheck, Shield } from 'lucide-react';
import UserRoleManagement from './UserRoleManagement'; // Import the new component
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
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";

// --- Zod Schemas for Validation ---
// [KEEP YOUR EXISTING SCHEMAS HERE]
const userCreateSchema = z.object({
    email: z.string().email({ message: "Invalid email address." }),
    password: z.string().min(8, { message: "Password must be at least 8 characters." }),
    is_active: z.boolean().default(true),
    is_superuser: z.boolean().default(false),
});

const userUpdateSchema = z.object({
    email: z.string().email({ message: "Invalid email address." }).optional(),
    password: z.string().min(8, { message: "Password must be at least 8 characters." }).optional().or(z.literal('')),
    is_active: z.boolean().optional(),
    is_superuser: z.boolean().optional(),
});

// Extend UserRead type to include roles
interface ExtendedUserRead extends UserRead {
    roles?: string[];
}

// --- Component ---
const UserManagementPage: React.FC = () => {
    const [users, setUsers] = useState<ExtendedUserRead[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [editingUser, setEditingUser] = useState<ExtendedUserRead | null>(null);
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
    const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
    const { toast } = useToast();

    // --- Form Hooks ---
    const createForm = useForm<z.infer<typeof userCreateSchema>>({
        resolver: zodResolver(userCreateSchema),
        defaultValues: {
            email: "",
            password: "",
            is_active: true,
            is_superuser: false,
        },
    });

    const editForm = useForm<z.infer<typeof userUpdateSchema>>({
        resolver: zodResolver(userUpdateSchema),
        defaultValues: {
            email: "",
            password: "",
            is_active: false,
            is_superuser: false,
        },
    });

    const fetchUsers = useCallback(async () => {
        setIsLoading(true);
        try {
            // First fetch the list of users
            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/users`);
            if (response.ok) {
                const userData: UserRead[] = await response.json();
                
                // Then fetch roles for each user
                const usersWithRoles = await Promise.all(
                    userData.map(async (user) => {
                        try {
                            const rolesResponse = await fetchWithAuth(
                                `${ENGINE_BASE_URL}/authz/users/${user.id}/roles`
                            );
                            if (rolesResponse.ok) {
                                const rolesData = await rolesResponse.json();
                                return { ...user, roles: rolesData.roles };
                            }
                            return { ...user, roles: [] };
                        } catch (error) {
                            console.error(`Error fetching roles for user ${user.id}:`, error);
                            return { ...user, roles: [] };
                        }
                    })
                );
                
                setUsers(usersWithRoles);
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch users' }));
                throw new Error(errorData.detail || 'Failed to fetch users');
            }
        } catch (error: any) {
            console.error('Error fetching users:', error);
            toast({
                title: 'Error',
                description: error.message || 'Could not load user data.',
                variant: 'destructive',
            });
            setUsers([]);
        } finally {
            setIsLoading(false);
        }
    }, [toast]);


    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    // --- Dialog and Form Handling ---
    useEffect(() => {
        if (!isCreateDialogOpen) {
            createForm.reset();
        }
    }, [isCreateDialogOpen, createForm]);

    useEffect(() => {
        if (isEditDialogOpen && editingUser) {
            editForm.reset({
                email: editingUser.email,
                password: "",
                is_active: editingUser.is_active,
                is_superuser: editingUser.is_superuser,
            });
        } else if (!isEditDialogOpen) {
            editForm.reset();
            setEditingUser(null);
        }
    }, [isEditDialogOpen, editingUser, editForm]);

    // --- Submit Handlers ---
    // [KEEP YOUR EXISTING HANDLERS HERE]
    const handleCreateSubmit = async (values: z.infer<typeof userCreateSchema>) => {
        setIsSubmitting(true);
        try {
            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: values.email,
                    password: values.password,
                }),
            });

            if (response.status === 201) {
                const newUser: UserRead = await response.json();

                if (values.is_active !== newUser.is_active || values.is_superuser !== newUser.is_superuser) {
                    console.log("Register endpoint didn't set flags, attempting PATCH...");
                    await handleUpdateSubmit(
                        {
                            is_active: values.is_active,
                            is_superuser: values.is_superuser
                        },
                        newUser.id
                    );
                } else {
                    toast({ title: "Success", description: "User created successfully." });
                }

                setIsCreateDialogOpen(false);
                fetchUsers();
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to create user' }));
                throw new Error(errorData.detail || 'Failed to create user');
            }
        } catch (error: any) {
            console.error("Error creating user:", error);
            toast({
                title: "Error",
                description: error.message || "Could not create user.",
                variant: "destructive",
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleUpdateSubmit = async (values: z.infer<typeof userUpdateSchema>, userId: UserRead['id']) => {
        setIsSubmitting(true);
        try {
            const payload: Partial<UserUpdate> = { ...values };
            if (!payload.password) {
                delete payload.password;
            }

            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/users/${userId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                toast({ title: "Success", description: "User updated successfully." });
                setIsEditDialogOpen(false);
                fetchUsers();
                return true;
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to update user' }));
                throw new Error(errorData.detail || 'Failed to update user');
            }
        } catch (error: any) {
            console.error("Error updating user:", error);
            toast({
                title: "Error",
                description: error.message || "Could not update user.",
                variant: "destructive",
            });
            return false;
        } finally {
            setIsSubmitting(false);
        }
    };

    // --- Action Handlers ---
    const openEditDialog = (user: ExtendedUserRead) => {
        setEditingUser(user);
        setIsEditDialogOpen(true);
    };

    const handleDeleteUser = async (userId: UserRead['id']) => {
        console.log("Attempting to delete user:", userId);
        setIsSubmitting(true);
        try {
            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/users/${userId}`, {
                method: 'DELETE',
            });
            if (response.status === 204 || response.ok) {
                toast({ title: "Success", description: "User deleted successfully." });
                fetchUsers();
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to delete user' }));
                if (response.status === 404) {
                    throw new Error("User not found. Maybe already deleted?");
                }
                throw new Error(errorData.detail || 'Failed to delete user');
            }
        } catch (error: any) {
            console.error('Error deleting user:', error);
            toast({
                title: 'Error',
                description: error.message || 'Could not delete user.',
                variant: 'destructive',
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    // New handler for role updates
    const handleRolesUpdated = (userId: string, roles: string[]) => {
        setUsers(prevUsers => 
            prevUsers.map(user => 
                user.id.toString() === userId
                    ? { ...user, roles: roles }
                    : user
            )
        );
    };

// Helper function to display all roles as multiple badges
const getRoleIndicators = (user: ExtendedUserRead) => {
    const { roles = [] } = user;
    
    // If no roles assigned, show "No Role" badge
    if (roles.length === 0) {
        return (
            <Badge variant="outline" className="text-xs text-gray-700">
                No Role
            </Badge>
        );
    }
    
    // Map each role to an appropriate badge
    return (
        <div className="flex flex-wrap gap-1">
            {user.is_superuser && (
                <Badge className="bg-blue-600/80 text-blue-100 border-blue-500 text-xs">
                    Superuser
                </Badge>
            )}
            
            {roles.map(role => {
                if (role === 'admin') {
                    return (
                        <Badge key={role} className="bg-indigo-600/80 text-indigo-100 border-indigo-500 text-xs">
                            Admin
                        </Badge>
                    );
                } else if (role === 'viewer') {
                    return (
                        <Badge key={role} className="bg-green-600/80 text-green-100 border-green-500 text-xs">
                            Viewer
                        </Badge>
                    );
                } else {
                    // For any custom roles in the future
                    return (
                        <Badge key={role} className="bg-purple-600/80 text-purple-100 border-purple-500 text-xs">
                            {role}
                        </Badge>
                    );
                }
            })}
        </div>
    );
};

    // --- JSX ---
    return (
        <div className="p-4 md:p-6 h-full overflow-y-auto bg-white text-foreground">
            <Card className="text-neutral-900">
                <CardHeader className="flex flex-row items-center justify-between pb-4">
                    <div>
                        <CardTitle className="text-xl">User Management</CardTitle>
                        <CardDescription className="text-gray-400">
                            Create, view, and manage user accounts and roles. Only superusers can access this page.
                        </CardDescription>
                    </div>
                    {/* Create User Dialog Trigger */}
                    <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
                        <DialogTrigger asChild>
                            <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white">
                                <PlusCircle className="mr-2 h-4 w-4" /> Create User
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[425px] text-neutral-900">
                            <DialogHeader>
                                <DialogTitle>Create New User</DialogTitle>
                                <DialogDescription className="text-gray-400">
                                    Enter the details for the new user. Default status is Active, default role is User.
                                </DialogDescription>
                            </DialogHeader>
                            {/* Create User Form */}
                            <Form {...createForm}>
                                <form onSubmit={createForm.handleSubmit(handleCreateSubmit)} className="space-y-4 py-4">
                                    {/* [KEEP YOUR EXISTING FORM FIELDS] */}
                                    <FormField
                                        control={createForm.control}
                                        name="email"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Email</FormLabel>
                                                <FormControl>
                                                    <Input placeholder="user@example.com" {...field} className="focus:ring-indigo-500" />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={createForm.control}
                                        name="password"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Password</FormLabel>
                                                <FormControl>
                                                    <Input type="password" placeholder="********" {...field} className="focus:ring-indigo-500" />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <div className="flex items-center space-x-4">
                                        <FormField
                                            control={createForm.control}
                                            name="is_active"
                                            render={({ field }) => (
                                                <FormItem className="flex flex-row items-center space-x-2 space-y-0">
                                                    <FormControl>
                                                        <Checkbox checked={field.value} onCheckedChange={field.onChange} id="create_is_active"/>
                                                    </FormControl>
                                                    <FormLabel htmlFor="create_is_active" className="font-normal cursor-pointer">Active</FormLabel>
                                                </FormItem>
                                            )}
                                        />
                                        <FormField
                                            control={createForm.control}
                                            name="is_superuser"
                                            render={({ field }) => (
                                                <FormItem className="flex flex-row items-center space-x-2 space-y-0">
                                                    <FormControl>
                                                        <Checkbox checked={field.value} onCheckedChange={field.onChange} id="create_is_superuser"/>
                                                    </FormControl>
                                                    <FormLabel htmlFor="create_is_superuser" className="font-normal cursor-pointer">Superuser</FormLabel>
                                                </FormItem>
                                            )}
                                        />
                                    </div>
                                    <DialogFooter>
                                        <DialogClose asChild>
                                            <Button type="button" variant="outline">Cancel</Button>
                                        </DialogClose>
                                        <Button type="submit" disabled={isSubmitting} className="bg-indigo-600 hover:bg-indigo-700">
                                            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                            Create User
                                        </Button>
                                    </DialogFooter>
                                </form>
                            </Form>
                        </DialogContent>
                    </Dialog>
                </CardHeader>
                <CardContent>
                    {/* User Table */}
                    {isLoading ? (
                        <div className="space-y-2">
                            {[...Array(3)].map((_, i) => ( <Skeleton key={i} className="h-12 w-full rounded-md" /> ))}
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="text-gray-700">Email</TableHead>
                                        <TableHead className="text-gray-700">Status</TableHead>
                                        <TableHead className="text-gray-700">Role</TableHead>
                                        <TableHead className="text-right text-gray-700 min-w-[160px]">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {users.length === 0 && !isLoading ? (
                                        <TableRow>
                                            <TableCell colSpan={5} className="text-center text-gray-500 py-4">
                                                No users found.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        users.map((user) => (
                                            <TableRow key={user.id.toString()}>
                                                <TableCell className="font-medium py-3">{user.email}</TableCell>
                                                <TableCell className="py-3">
                                                    <Badge variant={user.is_active ? 'default' : 'destructive'} className={`text-xs ${user.is_active ? 'bg-green-600/80 text-green-100 border-green-500' : 'bg-red-700/80 text-red-100 border-red-600'}`}>
                                                        {user.is_active ? 'Active' : 'Inactive'}
                                                    </Badge>
                                                </TableCell>
                                               
                                                <TableCell className="py-3">
                                                    {getRoleIndicators(user)}
                                                </TableCell>
                                                <TableCell className="text-right space-x-1 py-2">
                                                    {/* Role Management Button */}
                                                    <UserRoleManagement 
                                                        userId={user.id.toString()} 
                                                        userEmail={user.email}
                                                        onRolesUpdated={(roles) => handleRolesUpdated(user.id.toString(), roles)}
                                                    />
                                                    
                                                    {/* Edit User Dialog Trigger */}
                                                    <Dialog open={isEditDialogOpen && editingUser?.id === user.id} onOpenChange={(open) => {if (!open) setIsEditDialogOpen(false); else openEditDialog(user)}}>
                                                        <DialogTrigger asChild>
                                                            <Button variant="ghost" size="icon" onClick={() => openEditDialog(user)} className="text-gray-400 hover:text-neutral-900 h-8 w-8 ml-1">
                                                                <Edit className="h-4 w-4" />
                                                            </Button>
                                                        </DialogTrigger>
                                                        {/* Dialog Content for Edit */}
                                                        {editingUser && (
                                                            <DialogContent className="sm:max-w-[425px] text-neutral-900">
                                                                {/* [KEEP YOUR EXISTING EDIT DIALOG CONTENT] */}
                                                                <DialogHeader>
                                                                    <DialogTitle>Edit User: {editingUser.email}</DialogTitle>
                                                                    <DialogDescription className="text-gray-400">
                                                                        Modify user details. Leave password blank to keep unchanged.
                                                                    </DialogDescription>
                                                                </DialogHeader>
                                                                <Form {...editForm}>
                                                                <form onSubmit={editForm.handleSubmit((values) => handleUpdateSubmit(values, editingUser.id))} className="space-y-4 py-4">
    {/* Email Field */}
    <FormField
        control={editForm.control}
        name="email"
        render={({ field }) => (
            <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                    <Input placeholder="user@example.com" {...field} className="focus:ring-indigo-500" />
                </FormControl>
                <FormMessage />
            </FormItem>
        )}
    />
    
    {/* Optional New Password */}
    <FormField
        control={editForm.control}
        name="password"
        render={({ field }) => (
            <FormItem>
                <FormLabel>New Password (Optional)</FormLabel>
                <FormControl>
                    <Input type="password" placeholder="Leave blank to keep current" {...field} className="focus:ring-indigo-500" />
                </FormControl>
                <FormMessage />
            </FormItem>
        )}
    />
    
    {/* Status and Role Switches */}
    <div className="flex items-center space-x-4 pt-2">
        <FormField
            control={editForm.control}
            name="is_active"
            render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 w-1/2">
                    <FormLabel className="text-sm font-normal cursor-pointer">Active Status</FormLabel>
                    <FormControl>
                        <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                            aria-readonly
                        />
                    </FormControl>
                </FormItem>
            )}
        />
        <FormField
            control={editForm.control}
            name="is_superuser"
            render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 w-1/2">
                    <FormLabel className="text-sm font-normal cursor-pointer">Superuser Role</FormLabel>
                    <FormControl>
                        <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                            aria-readonly
                        />
                    </FormControl>
                </FormItem>
            )}
        />
    </div>
    
    {/* Note about Casbin roles */}
    <div className="text-sm text-gray-500 bg-gray-50 p-3 rounded-md border border-gray-200">
        <div className="flex items-center mb-1">
            <ShieldCheck className="h-4 w-4 mr-1 text-indigo-600" />
            <span className="font-medium text-gray-700">RBAC Roles</span>
        </div>
        <p>Use the "Manage Roles" button to assign or revoke RBAC roles like Admin or Viewer.</p>
    </div>
    
    <DialogFooter>
        <DialogClose asChild>
            <Button type="button" variant="outline">Cancel</Button>
        </DialogClose>
        <Button type="submit" disabled={isSubmitting} className="bg-indigo-600 hover:bg-indigo-700">
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
        </Button>
    </DialogFooter>
</form>
</Form>
                                                            </DialogContent>
                                                        )}
                                                    </Dialog>

                                                    {/* Delete User Alert Dialog Trigger */}
                                                    <AlertDialog>
                                                        <AlertDialogTrigger asChild>
                                                            <Button 
                                                                variant="ghost" 
                                                                size="icon" 
                                                                className="text-red-500 hover:text-red-400 h-8 w-8" 
                                                                disabled={isSubmitting}
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </AlertDialogTrigger>
                                                        <AlertDialogContent className="text-neutral-900 bg-white">
                                                            <AlertDialogHeader>
                                                                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                                                                <AlertDialogDescription className="text-gray-400">
                                                                    This action cannot be undone. This will permanently delete the user
                                                                    <span className="font-semibold text-red-400"> {user.email}</span>.
                                                                </AlertDialogDescription>
                                                            </AlertDialogHeader>
                                                            <AlertDialogFooter>
                                                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                                                <AlertDialogAction
                                                                    onClick={() => handleDeleteUser(user.id)}
                                                                    className="bg-red-600 hover:bg-red-700 text-white"
                                                                    disabled={isSubmitting}
                                                                >
                                                                    {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Delete User"}
                                                                </AlertDialogAction>
                                                            </AlertDialogFooter>
                                                        </AlertDialogContent>
                                                    </AlertDialog>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </div>
                    )}
                </CardContent>
            </Card>
            
            {/* Explanation of Roles */}
            <Card className="text-neutral-900 mt-4">
                <CardHeader>
                    <div className="flex items-center">
                        <Shield className="h-5 w-5 mr-2 text-indigo-600" />
                        <CardTitle className="text-lg">Understanding User Roles</CardTitle>
                    </div>
                </CardHeader>
                <CardContent className="text-sm space-y-3">
                    <div>
                        <ul className="mt-2 space-y-2">
                            <li className="flex items-start">
                                <Badge variant="secondary" className="mr-2 bg-blue-600/80 text-blue-100 mt-1">Superuser</Badge>
                                <span>Full access to all parts of the application including user management.</span>
                            </li>
                            <li className="flex items-start">
                                <Badge variant="secondary" className="mr-2 bg-indigo-600/80 text-indigo-100 mt-1">Admin</Badge>
                                <span>Role granting full access to resources with permission to perform all actions.</span>
                            </li>
                            <li className="flex items-start">
                                <Badge variant="secondary" className="mr-2 bg-green-600/80 text-green-100 mt-1">Viewer</Badge>
                                <span>Role with read-only access to resources.</span>
                            </li>
                        </ul>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default UserManagementPage;