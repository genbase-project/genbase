// src/users/UserManagementPage.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth, ENGINE_BASE_URL } from '@/config';
import { UserRead, UserCreate, UserUpdate } from '@/types/schemas';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { PlusCircle, Edit, Trash2, Loader2 } from 'lucide-react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogClose, // Import DialogClose
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
import { Switch } from "@/components/ui/switch"; // Using Switch for booleans can be nice too
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

// Schema for creating a user
const userCreateSchema = z.object({
    email: z.string().email({ message: "Invalid email address." }),
    password: z.string().min(8, { message: "Password must be at least 8 characters." }),
    is_active: z.boolean().default(true), // Default values for checkboxes/switches
    is_superuser: z.boolean().default(false),
});

// Schema for updating a user
// Make fields optional, password special handling
const userUpdateSchema = z.object({
    email: z.string().email({ message: "Invalid email address." }).optional(),
    // Password is optional for update. Only validate if provided.
    password: z.string().min(8, { message: "Password must be at least 8 characters." }).optional().or(z.literal('')),
    is_active: z.boolean().optional(),
    is_superuser: z.boolean().optional(),
});


// --- Component ---

const UserManagementPage: React.FC = () => {
    const [users, setUsers] = useState<UserRead[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [editingUser, setEditingUser] = useState<UserRead | null>(null);
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
        defaultValues: { // Default values will be set when edit dialog opens
            email: "",
            password: "", // Keep empty initially for edit
            is_active: false,
            is_superuser: false,
        },
    });

    // --- Data Fetching ---
    const fetchUsers = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/users`);
            if (response.ok) {
                const data: UserRead[] = await response.json();
                setUsers(data);
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

    // Reset create form when dialog closes
    useEffect(() => {
        if (!isCreateDialogOpen) {
            createForm.reset();
        }
    }, [isCreateDialogOpen, createForm]);

     // Reset edit form and set defaults when dialog opens/closes or user changes
    useEffect(() => {
        if (isEditDialogOpen && editingUser) {
            editForm.reset({
                email: editingUser.email,
                password: "", // Explicitly clear password on open
                is_active: editingUser.is_active,
                is_superuser: editingUser.is_superuser,
            });
        } else if (!isEditDialogOpen) {
             editForm.reset(); // Clear form on close
             setEditingUser(null); // Clear editing user state
        }
    }, [isEditDialogOpen, editingUser, editForm]);


    // --- Submit Handlers ---
    const handleCreateSubmit = async (values: z.infer<typeof userCreateSchema>) => {
        setIsSubmitting(true);
        try {
            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/auth/register`, { // Use the register endpoint
                method: 'POST',
                // FastAPI Users register expects JSON
                 headers: { 'Content-Type': 'application/json' },
                 body: JSON.stringify({
                    email: values.email,
                    password: values.password,
                    // Note: is_active and is_superuser might not be settable via standard register
                    // They usually need to be updated AFTER registration by a superuser PATCH /users/{id}
                    // Check your FastAPI Users setup if you customized registration.
                    // If not settable on register, you might need a two-step process (register then patch)
                    // or adjust the form to only take email/password initially.
                    // For now, sending them, but they might be ignored by default register.
                }),
            });

             if (response.status === 201) { // Check for 201 Created
                 const newUser: UserRead = await response.json(); // Get the created user data

                 // If is_active/is_superuser need setting after creation:
                 if (values.is_active !== newUser.is_active || values.is_superuser !== newUser.is_superuser) {
                     console.log("Register endpoint didn't set flags, attempting PATCH...");
                     await handleUpdateSubmit(
                         { // Prepare update payload
                             is_active: values.is_active,
                             is_superuser: values.is_superuser
                         },
                         newUser.id // Use the ID of the newly created user
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

    // Separate update logic to be reusable
    const handleUpdateSubmit = async (values: z.infer<typeof userUpdateSchema>, userId: UserRead['id']) => {
        setIsSubmitting(true);
        try {
             // Don't send empty password field unless it was intentionally changed
             const payload: Partial<UserUpdate> = { ...values }; // Use Partial for flexibility
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
                 setIsEditDialogOpen(false); // Close dialog if open
                 fetchUsers(); // Refresh list
                 return true; // Indicate success
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
             return false; // Indicate failure
        } finally {
            setIsSubmitting(false);
        }
    };

    // --- Action Handlers ---
    const openEditDialog = (user: UserRead) => {
        setEditingUser(user);
        setIsEditDialogOpen(true);
    };

    const handleDeleteUser = async (userId: UserRead['id']) => {
        console.log("Attempting to delete user:", userId);
        // Confirmation is handled by AlertDialog
        setIsSubmitting(true); // Use submitting state for delete as well
        try {
            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/users/${userId}`, {
                method: 'DELETE',
            });
            // Check specifically for 204 No Content on successful DELETE
            if (response.status === 204 || response.ok) { // Be lenient with ok() as well
                 toast({ title: "Success", description: "User deleted successfully." });
                 fetchUsers(); // Refresh the list
            } else {
                 const errorData = await response.json().catch(() => ({ detail: 'Failed to delete user' }));
                 // Handle potential 404 if user already deleted
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


    // --- JSX ---
    return (
        <div className="p-4 md:p-6 h-full overflow-y-auto bg-white text-foreground">
             <Card className="  text-neutral-900">
                <CardHeader className="flex flex-row items-center justify-between pb-4"> {/* Added pb-4 */}
                    <div>
                        <CardTitle className="text-xl">User Management</CardTitle>
                        <CardDescription className="text-gray-400">
                            Create, view, and manage user accounts. Only superusers can access this page.
                        </CardDescription>
                    </div>
                    {/* Create User Dialog Trigger */}
                    <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
                        <DialogTrigger asChild>
                             <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white">
                                 <PlusCircle className="mr-2 h-4 w-4" /> Create User
                             </Button>
                         </DialogTrigger>
                         <DialogContent className="sm:max-w-[425px]   text-neutral-900">
                            <DialogHeader>
                                <DialogTitle>Create New User</DialogTitle>
                                <DialogDescription className="text-gray-400">
                                    Enter the details for the new user. Default status is Active, default role is User.
                                </DialogDescription>
                            </DialogHeader>
                            {/* Create User Form */}
                             <Form {...createForm}>
                                <form onSubmit={createForm.handleSubmit(handleCreateSubmit)} className="space-y-4 py-4">
                                     <FormField
                                        control={createForm.control}
                                        name="email"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Email</FormLabel>
                                                <FormControl>
                                                    <Input placeholder="user@example.com" {...field} className="  focus:ring-indigo-500" />
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
                                                    <Input type="password" placeholder="********" {...field} className="  focus:ring-indigo-500" />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                     {/* Note: These might be ignored by default register endpoint */}
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
                                            <Button type="button" variant="outline" className="hover: ">Cancel</Button>
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
                            {[...Array(3)].map((_, i) => ( <Skeleton key={i} className="h-12 w-full rounded-md " /> ))}
                         </div>
                    ) : (
                        <div className="overflow-x-auto"> {/* Ensure table scrolls horizontally if needed */}
                            <Table>
                                <TableHeader>
                                    <TableRow className="hover: ">
                                        <TableHead className="text-gray-700">Email</TableHead>
                                        <TableHead className="text-gray-700">Status</TableHead>
                                        <TableHead className="text-gray-700">Role</TableHead>
                                        <TableHead className="text-right text-gray-700 min-w-[100px]">Tools</TableHead> {/* Added min-width */}
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {users.length === 0 && !isLoading ? (
                                         <TableRow className="hover: ">
                                            <TableCell colSpan={4} className="text-center text-gray-500 py-4">
                                                No users found.
                                            </TableCell>
                                         </TableRow>
                                    ) : (
                                        users.map((user) => (
                                            <TableRow key={user.id.toString()} className="hover: ">
                                                <TableCell className="font-medium py-3">{user.email}</TableCell> {/* Adjusted padding */}
                                                <TableCell className="py-3">
                                                     <Badge variant={user.is_active ? 'default' : 'destructive'} className={`text-xs ${user.is_active ? 'bg-green-600/80 text-green-100 border-green-500' : 'bg-red-700/80 text-red-100 border-red-600'}`}> {/* Adjusted colors/size */}
                                                         {user.is_active ? 'Active' : 'Inactive'}
                                                     </Badge>
                                                </TableCell>
                                                <TableCell className="py-3">
                                                     <Badge variant={user.is_superuser ? 'secondary' : 'outline'} className={`text-xs ${user.is_superuser ? 'bg-blue-600/80 text-blue-100 border-blue-500' : ' text-gray-700 /50'}`}> {/* Adjusted colors/size */}
                                                         {user.is_superuser ? 'Superuser' : 'User'}
                                                     </Badge>
                                                </TableCell>
                                                <TableCell className="text-right space-x-1 py-2"> {/* Adjusted spacing/padding */}
                                                    {/* Edit User Dialog Trigger */}
                                                     <Dialog open={isEditDialogOpen && editingUser?.id === user.id} onOpenChange={(open) => {if (!open) setIsEditDialogOpen(false); else openEditDialog(user)}}>
                                                        <DialogTrigger asChild>
                                                            <Button variant="ghost" size="icon" onClick={() => openEditDialog(user)} className="text-gray-400 hover:text-neutral-900 hover: h-8 w-8">
                                                                 <Edit className="h-4 w-4" />
                                                            </Button>
                                                         </DialogTrigger>
                                                         {/* Dialog Content for Edit - Placed outside Trigger but linked by open state */}
                                                         {editingUser && (
                                                             <DialogContent className="sm:max-w-[425px]   text-neutral-900">
                                                                <DialogHeader>
                                                                    <DialogTitle>Edit User: {editingUser.email}</DialogTitle>
                                                                    <DialogDescription className="text-gray-400">
                                                                        Modify user details. Leave password blank to keep unchanged.
                                                                    </DialogDescription>
                                                                </DialogHeader>
                                                                 <Form {...editForm}>
                                                                    <form onSubmit={editForm.handleSubmit((values) => handleUpdateSubmit(values, editingUser.id))} className="space-y-4 py-4">
                                                                        {/* Email (Potentially ReadOnly depending on your policy) */}
                                                                         <FormField
                                                                            control={editForm.control}
                                                                            name="email"
                                                                            render={({ field }) => (
                                                                                <FormItem>
                                                                                    <FormLabel>Email</FormLabel>
                                                                                    <FormControl>
                                                                                        <Input placeholder="user@example.com" {...field} className="  focus:ring-indigo-500" />
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
                                                                                        <Input type="password" placeholder="Leave blank to keep current" {...field} className="  focus:ring-indigo-500" />
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
                                                                                    <FormItem className="flex flex-row items-center justify-between rounded-lg border  p-3 w-1/2 /50">
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
                                                                                     <FormItem className="flex flex-row items-center justify-between rounded-lg border  p-3 w-1/2 /50">
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
                                                                        <DialogFooter>
                                                                             <DialogClose asChild>
                                                                                <Button type="button" variant="outline" className="hover: ">Cancel</Button>
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
                                                             <Button variant="ghost" size="icon" className="text-red-500 hover:text-red-400 hover: h-8 w-8" disabled={isSubmitting}> {/* Disable while any submission is happening */}
                                                                 <Trash2 className="h-4 w-4" />
                                                             </Button>
                                                         </AlertDialogTrigger>
                                                        <AlertDialogContent className="  text-neutral-900 bg-white">
                                                            <AlertDialogHeader>
                                                                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                                                                <AlertDialogDescription className="text-gray-400">
                                                                    This action cannot be undone. This will permanently delete the user
                                                                    <span className="font-semibold text-red-400"> {user.email}</span>.
                                                                </AlertDialogDescription>
                                                            </AlertDialogHeader>
                                                            <AlertDialogFooter>
                                                                <AlertDialogCancel className="hover: ">Cancel</AlertDialogCancel>
                                                                <AlertDialogAction
                                                                     onClick={() => handleDeleteUser(user.id)}
                                                                     className="bg-red-600 hover:bg-red-700 text-neutral-900"
                                                                     disabled={isSubmitting} // Disable during delete operation
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

             {/* Edit User Dialog (Structure only needed once, controlled by state) */}
             {/* We render the content conditionally inside the table row Dialog */}

        </div>
    );
};

export default UserManagementPage;