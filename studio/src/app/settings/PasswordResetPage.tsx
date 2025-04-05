// src/settings/PasswordResetPage.tsx
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { fetchWithAuth, ENGINE_BASE_URL } from '@/config';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/context/AuthContext';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
// Label is already imported
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Loader2 } from 'lucide-react';
import { ThemeProvider } from '@/components/themeProvider'; // Import ThemeProvider

// Zod schema remains the same
const passwordResetSchema = z.object({
    oldPassword: z.string().min(1, { message: "Current password is required." }),
    newPassword: z.string().min(8, { message: "New password must be at least 8 characters." }),
    confirmPassword: z.string().min(8, { message: "Please confirm your new password." }),
}).refine((data) => data.newPassword === data.confirmPassword, {
    message: "New passwords do not match.",
    path: ["confirmPassword"],
});

type PasswordResetFormData = z.infer<typeof passwordResetSchema>;

const PasswordResetPage: React.FC = () => {
    const { toast } = useToast();
    const { user } = useAuth();
    const [isSubmitting, setIsSubmitting] = useState(false);

    const form = useForm<PasswordResetFormData>({
        resolver: zodResolver(passwordResetSchema),
        defaultValues: {
            oldPassword: "",
            newPassword: "",
            confirmPassword: "",
        },
    });

    const onSubmit = async (values: PasswordResetFormData) => {
        setIsSubmitting(true);
        const payload = {
            password: values.newPassword,
        };

        try {
            const response = await fetchWithAuth(`${ENGINE_BASE_URL}/users/me`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                toast({
                    title: "Success",
                    description: "Your password has been updated successfully.",
                    variant: "default", // Keep variant default, it adapts to theme
                });
                form.reset();
            } else {
                 let errorDetail = "Failed to update password.";
                 try {
                    const errorData = await response.json();
                     if (errorData.detail && typeof errorData.detail === 'string' && errorData.detail.includes("UPDATE_USER_INVALID_PASSWORD")) {
                         errorDetail = `Password update failed: ${errorData.detail}. Ensure the new password meets requirements.`;
                         form.setError("newPassword", { type: "manual", message: "Password rejected by server." });
                     } else {
                         errorDetail = errorData.detail || JSON.stringify(errorData);
                     }
                 } catch (e) {
                    errorDetail = `HTTP Error ${response.status}: ${response.statusText || 'Failed to update password.'}`
                 }
                throw new Error(errorDetail);
            }
        } catch (error: any) {
            toast({
                title: "Error",
                description: error.message || "An unexpected error occurred.",
                variant: "destructive", // Keep variant destructive, it adapts
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <ThemeProvider defaultTheme="light" >
            {/* Add a background color div that respects the new theme */}
            <div className="p-4 md:p-6 h-full overflow-y-auto bg-white text-foreground text-neutral-900"> {/* Use theme-aware background/text */}
 <CardHeader>
                        <CardTitle className="text-xl">Change Your Password</CardTitle>
                        <CardDescription> {/* Text color will adapt */}
                            Update your account password below. Choose a strong, unique password.
                        </CardDescription>
                    </CardHeader>
                     <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)}>
                            <CardContent className="space-y-4">
                                 <FormField
                                    control={form.control}
                                    name="oldPassword"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Current Password</FormLabel>
                                            <FormControl>
                                                {/* Input will adapt its style */}
                                                <Input type="password" placeholder="Enter your current password" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                 <FormField
                                    control={form.control}
                                    name="newPassword"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>New Password</FormLabel>
                                            <FormControl>
                                                <Input type="password" placeholder="Enter your new password (min. 8 characters)" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                 <FormField
                                    control={form.control}
                                    name="confirmPassword"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Confirm New Password</FormLabel>
                                            <FormControl>
                                                <Input type="password" placeholder="Confirm your new password" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </CardContent>
                            <CardFooter className="flex justify-end">
                                {/* Button variant="default" will adapt */}
                                <Button type="submit" disabled={isSubmitting}>
                                    {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Update Password
                                </Button>
                            </CardFooter>
                        </form>
                    </Form>
             
            </div>
        </ThemeProvider>
    );
};

export default PasswordResetPage;